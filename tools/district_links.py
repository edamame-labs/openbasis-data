"""Deterministic official roster-to-Census boundary joins; no spatial inference."""
from collections import Counter, defaultdict
import re
import unicodedata

# Exact label correspondences observed in the two official input publications.
LABEL_ALIASES = {
    ('MA', 'sldl', 'barnstable, dukes and nantucket'): 'barnstable-dukes-nantucket',
    ('MA', 'sldu', 'berkshire, hampden, franklin and hampshire'): 'berkshire-hampden-franklin-hampshire',
    ('MA', 'sldu', 'hampden, hampshire and worcester'): 'hampden-hampshire-worcester',
    ('MA', 'sldu', 'hampshire, franklin and worcester'): 'hampshire-franklin-worcester',
    ('MA', 'sldu', 'norfolk, plymouth and bristol'): 'norfolk-plymouth-bristol',
    ('MA', 'sldu', 'norfolk, worcester and middlesex'): 'norfolk-worcester-middlesex',
    ('VT', 'sldu', 'chittenden-central'): 'chittenden central',
    ('VT', 'sldu', 'chittenden-north'): 'chittenden north',
    ('VT', 'sldu', 'chittenden-southeast'): 'chittenden south east',
}

LAYER_FIELDS = {'cd': 'CD119', 'sldu': 'SLDU', 'sldl': 'SLDL','sldl_floterial':'NH_FLT'}


def canonical_label(value, state, layer):
    """Formatting normalization only; never translate district identifiers."""
    text = unicodedata.normalize('NFKC', str(value)).strip().casefold()
    text = re.sub(r'\s+', ' ', text)
    # Vermont's official roster appends this generic word; Census BASENAME omits it.
    if state == 'VT' and layer == 'sldu':
        text = re.sub(r' district$', '', text)
    # Leading zeroes have no numeric meaning (NH: Strafford 04 -> Strafford 4).
    text = re.sub(r'(?<![\w])0+(\d+)', lambda m: str(int(m.group())), text)
    if re.fullmatch(r'\d+[a-z]?', text):
        text = re.sub(r'^0+(?=\d)', '', text)
    return LABEL_ALIASES.get((state, layer, text), text)


def source_ids(value):
    if isinstance(value, dict):
        return [value['id']] if value.get('id') else []
    if isinstance(value, list):
        return sorted({i for v in value for i in source_ids(v)})
    return []


def target_layer(row):
    if row.get('level') == 'federal':
        return {'U.S. House': 'cd', 'U.S. Senate': 'states'}.get(row.get('body'))
    if row.get('level') != 'state':
        return None
    if row.get('office') == 'Governor':
        return 'states'
    if row['state'] == 'NE':
        return 'sldu'
    body = row.get('body', '').casefold()
    if 'senate' in body:
        return 'sldu'
    if 'house' in body or 'assembly' in body:
        return 'sldl'
    return None


def link(officials, collections):
    """Return a many-person-to-one-boundary join and explicit unmatched reasons.

    collections keys: states, cd (119th), sldu (2024), sldl (2024).
    Each is a GeoJSON FeatureCollection with source or sources metadata. State
    features supply the official FIPS/USPS crosswalk. Inputs are never mutated.
    """
    rows = officials.get('officials', []) if isinstance(officials, dict) else officials
    state_codes = {}
    state_refs = {}
    for feature in collections.get('states', {}).get('features', []):
        p = feature['properties']
        if p.get('STUSAB') and p.get('STATE'):
            if p['STUSAB'] in state_codes:
                raise ValueError('Duplicate state code: ' + p['STUSAB'])
            state_codes[p['STUSAB']] = str(p['STATE'])
            controls=[s['id'] for s in collections['states'].get('sources',[]) if s['id'].endswith('-metadata')]
            state_refs[p['STUSAB']]=sorted(set(([p['sourceId']]+controls) if p.get('sourceId') else source_ids(collections['states'].get('source'))+source_ids(collections['states'].get('sources'))))
    indexes = {}
    metadata = {}
    for layer, fc in collections.items():
        if layer not in {'states', *LAYER_FIELDS}:
            continue
        index = defaultdict(list)
        seen = set()
        metadata[layer] = source_ids(fc.get('source')) + source_ids(fc.get('sources'))
        for f in fc.get('features', []):
            p = f['properties']
            geoid = str(p.get('GEOID') or p['boundaryId'])
            if geoid in seen:
                raise ValueError('Duplicate geometry ID in ' + layer + ': ' + geoid)
            seen.add(geoid)
            if layer == 'cd' and 'CD120' in p:
                raise ValueError('120th Congress geometry cannot join the 119th Congress roster')
            state = str(p['STATE'])
            if not geoid.startswith(state):
                raise ValueError('Geometry GEOID/state mismatch: ' + geoid)
            if layer == 'states':
                labels = [state]
            elif layer == 'cd':
                if not re.fullmatch(r'\d{2}', str(p.get('CD119', ''))):
                    continue
                labels = [str(int(p['CD119']))]
            else:
                # BASENAME is the government-published district label. Do not
                # turn alphabetical districts into ordinal positions or use
                # internal feature IDs as district numbers.
                labels = [str(p.get('BASENAME', ''))]
                if not labels[0] or str(p.get(LAYER_FIELDS[layer], '')) in {'ZZZ', 'ZZ'}:
                    continue
            stusab = next((st for st, code in state_codes.items() if code == state), '')
            for label in labels:
                key = (state, canonical_label(label, stusab, layer))
                controls=[s['id'] for s in fc.get('sources',[]) if s['id'].endswith('-metadata')]
                refs=([p['sourceId']]+p.get('componentSourceIds',[])+controls) if p.get('sourceId') else metadata[layer] + source_ids(p.get('source')) + source_ids(p.get('sources'))
                index[key].append((f, sorted(set(refs))))
        indexes[layer] = index
    matches, unmatched = [], []
    for row in rows:
        layer = target_layer(row)
        st = row['state']
        fips = state_codes.get(st)
        district = row.get('district')
        entry = dict(officialId=row['id'], state=st, layer='state' if layer=='states' else layer,
                     district=district, sourceIds=source_ids(row.get('sources', [])))
        reason = None
        if not layer:
            reason = 'unsupported-office'
        elif not fips:
            reason = 'state-crosswalk-unavailable'
        elif layer not in indexes:
            reason = 'geometry-layer-unavailable'
        elif layer != 'states' and (district is None or str(district).strip() == ''):
            reason = 'district-label-unavailable'
        else:
            label = canonical_label(fips if layer == 'states' else district, st, layer)
            candidates = indexes[layer].get((fips, label), [])
            if not candidates and st=='NH' and layer=='sldl':
                candidates=indexes.get('sldl_floterial',{}).get((fips,canonical_label(district,st,'sldl_floterial')),[])
                if candidates:
                    layer='sldl_floterial'
                    entry['layer']=layer
            if not candidates:
                reason = 'no-exact-official-district-label'
            elif len(candidates) != 1:
                reason = 'ambiguous-official-district-label'
            else:
                feature, refs = candidates[0]
                p = feature['properties']
                entry.update(districtKey=('state' if layer=='states' else layer) + ':' + str(p.get('GEOID') or p['boundaryId']), GEOID=p.get('GEOID'),boundaryId=p.get('GEOID') or p['boundaryId'],
                             geometrySourceIds=refs, stateCrosswalkSourceIds=state_refs[st],
                             matchingRule=(('statewide-governor-state-fips' if row.get('office') == 'Governor' else 'statewide-senate-state-fips') if layer == 'states' else
                                           '119th-congress-numeric-code' if layer == 'cd' else
                                           'state-chamber-canonical-basename'),
                             geometryDistrictLabel=p.get('BASENAME', p.get('NAME')))
                matches.append(entry)
        if reason:
            entry['reason'] = reason
            unmatched.append(entry)
    return dict(schemaVersion=1, matches=matches, unmatched=unmatched,
                summary=dict(officials=len(rows), matched=len(matches), unmatched=len(unmatched),
                             matchedByLayer=dict(Counter(x['layer'] for x in matches)),
                             unmatchedByReason=dict(Counter(x['reason'] for x in unmatched))))
