"""Acquire Census state, county, and legislative polygons without generalization.

The Census layer cycle and the officeholder's session are different facts. This
collector preserves the former and does not infer the latter from retrieval time.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

BASE = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/'
PUBLISHER = 'U.S. Census Bureau'
# Census state FIPS identifiers for the 50 states; DC and territories excluded.
STATE_FIPS = set('01 02 04 05 06 08 09 10 12 13 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 54 55 56'.split())
LAYERS = {
    'cd': (4, '119th Congressional Districts', 'CD119', '119th Congress'),
    'sldu': (5, '2024 State Legislative Districts - Upper', 'SLDU', '2024 state legislative districts'),
    'sldl': (6, '2024 State Legislative Districts - Lower', 'SLDL', '2024 state legislative districts'),
}
AREA_BASE = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/'
AREA_LAYERS = {
    'state': (0, 'States', None, '2026 state boundaries'),
    'county': (1, 'Counties', 'COUNTY', '2026 county boundaries'),
}
PAGE_SIZE = 100


def decode_source(raw, source):
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError('Census response is not JSON: '+source.get('url', source['id'])) from exc


def check_metadata(metadata, name, district_field):
    assert 'error' not in metadata, 'Census metadata request failed'
    assert metadata['name'] == name, 'Census layer name changed; review applicability'
    assert 'January 1, 2026 vintage' in metadata['description'], 'Census vintage changed; review applicability'
    names = {f['name'] for f in metadata['fields']}
    assert ({'GEOID', 'STATE', 'OBJECTID'} | ({district_field} if district_field else set())) <= names, 'Census identifiers changed'
    assert metadata.get('advancedQueryCapabilities', {}).get('supportsPagination'), 'Census pagination unavailable'


def check_page(page, district_field, offset, count, page_size=PAGE_SIZE):
    assert 'error' not in page and page.get('type') == 'FeatureCollection', 'Invalid Census geometry response'
    features = page.get('features', [])
    expected = min(page_size, count-offset)
    assert len(features) == expected, 'Census page incomplete or pagination ignored'
    # A transfer limit is acceptable only on a full, nonfinal page; every page is
    # fetched using an independent count, rather than trusting this optional flag.
    assert not page.get('exceededTransferLimit') or len(features) == page_size and offset+len(features)<count, 'Unexpected transfer limit'
    for feature in features:
        p = feature['properties']
        assert p['STATE'] in STATE_FIPS and p['GEOID'].startswith(p['STATE'])
        assert p['GEOID'] == p['STATE']+(p[district_field] if district_field else '')
        assert (feature.get('geometry') or {}).get('type') in {'Polygon', 'MultiPolygon'}, 'Missing polygon'
        assert feature['geometry']['coordinates'], 'Empty polygon'
    return features


def district_kind(properties, district_field):
    """Preserve Census pseudo-districts, but prevent treating them as seats."""
    code = str(properties[district_field]).upper()
    if code in {'ZZ', 'ZZZ'}:
        return 'unassigned-area'
    return 'district'


def iter_collect(fetch, offline=False):
    """Yield one (key, collection, sources) tuple at a time to bound memory."""
    for key, (layer_id, name, district_field, cycle) in {**AREA_LAYERS, **LAYERS}.items():
        prefix = 'census-'+key
        base = (AREA_BASE if key in AREA_LAYERS else BASE)+str(layer_id)
        raw, metadata_source = fetch(prefix+'-metadata', PUBLISHER, base+'?f=pjson', offline)
        metadata = decode_source(raw, metadata_source)
        check_metadata(metadata, name, district_field)
        metadata_source.update(vintage='2026-01-01', description=metadata['description'])
        fields = ','.join(f['name'] for f in metadata['fields'] if f.get('type') != 'esriFieldTypeGeometry' and f['name']!='STGEOMETRY')
        def acquire_state(state):
            state_prefix = prefix+'-'+state
            state_where = "STATE='"+state+"'"
            count_url = base+'/query?'+urlencode(dict(where=state_where, returnCountOnly='true', f='json'))
            raw, count_source = fetch(state_prefix+'-count', PUBLISHER, count_url, offline)
            count_payload = decode_source(raw, count_source)
            assert 'error' not in count_payload and isinstance(count_payload.get('count'), int), 'Invalid Census feature count'
            count = count_payload['count']
            assert count > 0 or key=='sldl' and state=='31', 'Unexpected empty state layer'
            state_sources, state_features = [count_source], []
            for offset in range(0, count, PAGE_SIZE):
                query = dict(where=state_where, outFields=fields, outSR='4326', orderByFields='OBJECTID', resultOffset=offset, resultRecordCount=PAGE_SIZE, f='geojson')
                # No maxAllowableOffset, geometryPrecision or quantization.
                raw, source = fetch(state_prefix+'-page-'+str(offset//PAGE_SIZE), PUBLISHER, base+'/query?'+urlencode(query), offline)
                source.update(vintage='2026-01-01', mapCycle=cycle, generalization='none requested', coordinateReferenceSystem='EPSG:4326')
                page = decode_source(raw, source)
                for feature in check_page(page, district_field, offset, count):
                    p = feature['properties']
                    assert p['STATE']==state, 'State filter was ignored'
                    p['sourceId'] = source['id']
                    if key in LAYERS: p['districtKind'] = district_kind(p, district_field)
                    state_features.append(feature)
                state_sources.append(source)
            assert len(state_features)==count
            return state_features, state_sources
        layer_sources = [metadata_source]
        features, seen_geoids, seen_objects = [], set(), set()
        # Small state queries avoid the Census gateway rejecting large IN clauses;
        # bounded parallelism also bounds response memory and publisher load.
        with ThreadPoolExecutor(max_workers=4) as executor:
            state_results = executor.map(acquire_state, sorted(STATE_FIPS))
            for state_features, state_sources in state_results:
                for feature in state_features:
                    p = feature['properties']
                    assert p['GEOID'] not in seen_geoids, 'Duplicate district GEOID across pages'
                    assert p['OBJECTID'] not in seen_objects, 'Duplicate Census object across pages'
                    seen_geoids.add(p['GEOID']); seen_objects.add(p['OBJECTID'])
                    features.append(feature)
                layer_sources.extend(state_sources)
        states = {f['properties']['STATE'] for f in features}
        expected_states = STATE_FIPS-({'31'} if key == 'sldl' else set())
        assert states == expected_states, 'Unexpected state coverage (Nebraska has no lower chamber)'
        collection = dict(type='FeatureCollection', features=features, sources=layer_sources,
            layer=dict(id=layer_id, name=name, districtField=district_field, vintage='2026-01-01', mapCycle=cycle,
                applicability=('119th Congress; do not join to 120th Congress' if key=='cd' else 'Census 2024 state legislative district layer; current officeholder applicability requires matching the chamber plan') if key in LAYERS else 'Census January 1, 2026 state/county boundaries',
                generalization='none requested', coordinateReferenceSystem='EPSG:4326',
                excludedJurisdictions='District of Columbia and territories',
                missingChamber='Nebraska has no lower chamber' if key=='sldl' else None))
        yield key, collection, layer_sources
        # Do not retain the previous national layer while acquiring the next.
        del collection, features, layer_sources


def collect(fetch, offline=False):
    """Compatibility API; iter_collect is preferred for national-size files."""
    collections, sources = {}, []
    for key, collection, layer_sources in iter_collect(fetch, offline):
        collections[key] = collection
        sources.extend(layer_sources)
    return collections, sources
