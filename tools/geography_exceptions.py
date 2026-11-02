"""Primary-source district subdivisions and NH overlapping House districts."""
import copy
import csv
import io
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

SOURCES = {
    'nd-district-directory': ('North Dakota Legislative Assembly', 'https://ndlegis.gov/assembly/69-2025/special-2/members/members-by-district'),
    'nh-floterial-components': ('U.S. Census Bureau', 'https://www2.census.gov/programs-surveys/decennial/rdo/mapping-files/2023/2022-state-legislative-bef/NH_Floterial_2022.csv'),
}
CSV_FIELDS = ['Floterial District', 'Component Census SLDL Code', 'Component Census SLDL Name']


class MemberCard(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.values = {'member-name': [], 'member-chamber': [], 'district': []}
        self.capture = None
        self.div_depth = 0
        self.website = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href', '').startswith('/biography/'):
            self.website = urljoin(SOURCES['nd-district-directory'][1], attrs['href'])
        if tag == 'div':
            self.div_depth += 1
            for name in self.values:
                if name in attrs.get('class', '').split():
                    assert self.capture is None, 'Nested member fields'
                    self.capture = (name, self.div_depth)

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.capture and self.capture[1] == self.div_depth:
                self.capture = None
            self.div_depth -= 1

    def handle_data(self, value):
        if self.capture:
            self.values[self.capture[0]].append(value)


def parse_nd(raw):
    text = raw.decode('utf-8-sig') if isinstance(raw, bytes) else raw
    # Cards are non-nested list items in the government's directory template.
    cards = re.findall(r'<li\b[^>]*class=["\'][^"\']*\bmember-item\b[^"\']*["\'][^>]*>(.*?)</li>', text, re.S)
    result = []
    for html in cards:
        card = MemberCard(html)
        fields = {k: ' '.join(' '.join(v).split()) for k, v in card.values.items()}
        m = re.match(r'^District (\d+[AB]?)\s*\|', fields['district'])
        assert m and fields['member-name'] and card.website, 'Incomplete official ND district card'
        assert fields['member-chamber'] in {'Representative', 'Senator'}, 'Unknown ND chamber'
        result.append(dict(name=fields['member-name'], district=m[1], website=card.website,
                           chamber=fields['member-chamber'], sourceId='nd-district-directory'))
    assert result, 'Empty official ND district directory'
    identities = [r['website'] for r in result]
    assert len(set(identities)) == len(identities), 'Duplicate ND profile identity'
    return result


def parse_components(raw):
    text = raw.decode('utf-8-sig') if isinstance(raw, bytes) else raw
    reader = csv.DictReader(io.StringIO(text))
    assert reader.fieldnames == CSV_FIELDS, 'NH component CSV header changed'
    rows = list(reader)
    seen = set()
    for row in rows:
        code, district, name = (row[f] for f in CSV_FIELDS)
        assert re.fullmatch(r'[A-Z]{2}\d+', code), 'Invalid official NH floterial code'
        assert re.fullmatch(r'\d{1,3}', district), 'Invalid official Census component code'
        assert re.fullmatch(r'State House District .+ \d{2}', name), 'Invalid official component name'
        key = (code, district.zfill(3))
        assert key not in seen, 'Duplicate NH component relation'
        seen.add(key)
    assert rows, 'Empty NH component CSV'
    return rows


def collect(fetch, offline=False):
    sources, data = [], {}
    for key, (publisher, url) in SOURCES.items():
        raw, source = fetch(key, publisher, url, offline)
        if key == 'nd-district-directory':
            source['effectivePeriod'] = '69th Legislative Assembly, September 2026 special-session membership'
            data['ndDistricts'] = parse_nd(raw)
            assert len(data['ndDistricts']) == 141, 'ND district directory is incomplete or chamber membership changed'
        else:
            source['effectivePeriod'] = 'New Hampshire 2022 legislative district plan'
            data['nhComponents'] = parse_components(raw)
            assert len(data['nhComponents']) == 109, 'NH component relationship count changed; review plan applicability'
        sources.append(source)
    data['sources'] = copy.deepcopy(sources)
    return data, sources


def apply_roster(officials, data):
    """Copy records and enrich only ND House district 4 from exact official identity."""
    rows = copy.deepcopy(officials)
    sources = {s['id']: s for s in data['sources']}
    proof = sources['nd-district-directory']
    directory = data['ndDistricts']
    for row in rows:
        if not (row.get('state') == 'ND' and row.get('level') == 'state' and
                'House' in row.get('body', '') and row.get('district') == '4'):
            continue
        candidates = [r for r in directory if r['name'] == row['name'] and r['chamber'] == 'Representative'
                      and r['website'] == row.get('website')]
        assert len(candidates) == 1, 'No unambiguous ND member name/profile identity: ' + row['id']
        district = candidates[0]['district']
        assert district in {'4A', '4B'}, 'ND district 4 no longer resolves to a published subdistrict'
        row['district'] = district
        if not any(s['id'] == proof['id'] for s in row['sources']):
            row['sources'].append(copy.deepcopy(proof))
        row.setdefault('fieldEvidence', {})['district'] = dict(
            sourceIds=[proof['id']], value=district,
            method='Exact official name and biography URL in current-session district directory; preserves published subdistrict label')
    return rows


def floterials(base_fc, data):
    """Union explicitly enumerated Census components; never repair input polygons."""
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    from shapely.validation import explain_validity

    source = next(s for s in data['sources'] if s['id'] == 'nh-floterial-components')
    components = {}
    for feature in base_fc['features']:
        props = feature['properties']
        if props.get('STATE') != '33' or props.get('SLDL') == 'ZZZ':
            continue
        code = props['SLDL']
        assert code not in components, 'Duplicate Census NH component code'
        assert props.get('GEOID') == '33' + code, 'Census NH component GEOID mismatch'
        components[code] = feature
    groups = {}
    for row in data['nhComponents']:
        code = row['Component Census SLDL Code'].zfill(3)
        assert code in components, 'Missing Census NH component: ' + code
        feature = components[code]
        assert feature['properties']['NAME'] == row['Component Census SLDL Name'], 'Census component label conflicts with official crosswalk: ' + code
        groups.setdefault(row['Floterial District'], []).append(feature)
    features, refs = [], {source['id']}
    for float_code, parts in sorted(groups.items()):
        assert len(parts) >= 2, 'Floterial must have two or more official component districts'
        assert len({p['properties']['GEOID'] for p in parts}) == len(parts), 'Duplicate floterial component'
        county_names = {re.fullmatch(r'State House District (.+) \d{2}', f['properties']['NAME']).group(1) for f in parts}
        assert len(county_names) == 1, 'Official floterial components span conflicting county labels'
        label = next(iter(county_names)) + ' ' + str(int(re.search(r'\d+$', float_code).group()))
        geometries = []
        for feature in parts:
            geom = shape(feature['geometry'])
            assert geom.geom_type in {'Polygon', 'MultiPolygon'} and not geom.is_empty, 'Invalid component geometry type'
            assert geom.is_valid, 'Invalid component polygon ' + feature['properties']['GEOID'] + ': ' + explain_validity(geom)
            geometries.append(geom)
        union = unary_union(geometries)
        assert union.is_valid and not union.is_empty and union.geom_type in {'Polygon', 'MultiPolygon'}, 'Invalid derived NH floterial polygon: ' + float_code
        component_refs = sorted({f['properties']['sourceId'] for f in parts})
        refs.update(component_refs)
        properties = dict(STATE='33', boundaryId='33-floterial-' + float_code,
                          BASENAME=label, NAME='State House Floterial District ' + label,
                          NH_FLT=float_code, districtKind='floterial', sourceId=source['id'],
                          componentKeys=sorted('sldl:' + f['properties']['GEOID'] for f in parts),
                          componentSourceIds=component_refs,
                          derivation='Shapely unary_union of current Census component polygons explicitly listed by the Census 2022 NH floterial crosswalk; no simplification or geometry repair')
        features.append(dict(type='Feature', properties=properties, geometry=mapping(union)))
    return dict(type='FeatureCollection', features=features, sourceIds=sorted(refs),
                layer=dict(key='sldl_floterial', name='New Hampshire House floterial districts',
                           vintage='2022 plan; component geometry vintage as cited by input layer',
                           plan='2022 New Hampshire House plan', derived=True,
                           generalization='none requested', componentLayer=copy.deepcopy(base_fc.get('layer', {})),
                           methodology='Union of official component polygons using official Census floterial crosswalk; overlapping representation units, not a disjoint partition'))
