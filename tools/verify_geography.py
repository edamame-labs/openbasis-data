"""Offline integrity checks for analytical geometry, joins and area exports."""
import csv
import json
import math
from geo_io import read_json
from pathlib import Path

LAYERS={'state','county','cd','sldu','sldl'}


def read(path):return read_json(path)


def close(a,b):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8)


def verify(folder,officials,sources):
    index=read(folder/'geography/index.json')
    report=read(folder/'geography-report.json')
    source_index={s['id']:s for s in sources}
    states=read(folder/'geography/states.geojson')['features']
    fips_by_state={f['properties']['STUSAB']:f['properties']['STATE'] for f in states}
    assert {s['state'] for s in index['states']}==set(fips_by_state) and len(index['states'])==50
    counts={layer:0 for layer in LAYERS}
    keys={}
    total_pairs=0
    for state in index['states']:
        st=state['state']
        local_keys={}
        expected_layers=LAYERS|({'sldl_floterial'} if st=='NH' else set())
        assert set(state['files'])==expected_layers
        derived_components=[]
        for layer in expected_layers:
            counts.setdefault(layer,0)
            path='geography/regions/'+st.lower()+'/'+layer+'.geojson.gz'
            assert state['files'][layer]==path
            fc=read(folder/path)
            assert fc['type']=='FeatureCollection' and fc['layer']['generalization']=='none requested'
            assert len(fc['features'])==state['layerCounts'][layer]
            assert set(fc['sourceIds'])<=source_index.keys()
            for feature in fc['features']:
                p=feature['properties']
                boundary_id=p.get('GEOID') or p['boundaryId']
                assert p['STATE']==fips_by_state[st] and boundary_id.startswith(p['STATE'])
                assert feature['geometry']['type'] in {'Polygon','MultiPolygon'} and feature['geometry']['coordinates']
                assert p['sourceId'] in fc['sourceIds']
                source=source_index[p['sourceId']]
                if layer=='sldl_floterial':
                    assert fc['layer']['derived'] and not p.get('GEOID') and p['districtKind']=='floterial'
                    assert source['url'].endswith('/2022-state-legislative-bef/NH_Floterial_2022.csv')
                    assert set(p['componentSourceIds'])<=source_index.keys()
                    derived_components.extend(p['componentKeys'])
                else:
                    assert 'tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/' in source['url']
                assert not any(token in source['url'] for token in ['maxAllowableOffset','geometryPrecision','quantizationParameters'])
                key=layer+':'+boundary_id
                assert key not in keys and key not in local_keys
                local_keys[key]=dict(state=st,sourceId=p['sourceId'])
            counts[layer]+=len(fc['features'])
        assert set(derived_components)<=local_keys.keys()
        keys.update(local_keys)
        result=read(folder/state['overlapFile'])
        assert result['state']==st and result['method']['measure']=='polygon-area-including-water'
        assert result['method']['population'] is None
        areas={d['key']:d['areaM2'] for d in result['districts']}
        assert len(areas)==len(local_keys) and set(areas)==set(local_keys)
        assert all(math.isfinite(a) and a>0 for a in areas.values())
        seen=set()
        for pair in result['overlaps']:
            a,b=pair['a'],pair['b']
            assert a in local_keys and b in local_keys and a.split(':')[0]!=b.split(':')[0]
            assert (a,b) not in seen and (b,a) not in seen
            seen.add((a,b))
            area=pair['intersectionAreaM2']
            assert math.isfinite(area) and area>0 and area<=min(areas[a],areas[b])*(1+1e-8)
            assert close(pair['shareOfA'],area/areas[a]) and close(pair['shareOfB'],area/areas[b])
        assert len(seen)==state['intersectionPairs']
        total_pairs+=len(seen)
        with (folder/'overlaps'/(st.lower()+'.csv')).open(newline='') as f:
            exported=list(csv.DictReader(f))
        assert len(exported)==len(result['overlaps'])
        for flat,pair in zip(exported,result['overlaps']):
            assert flat=={key:str(value) for key,value in pair.items()}
        for residual in result['coverageResiduals']:
            assert residual['key'] in areas
            assert close(residual['areaM2'],areas[residual['key']])
            assert close(residual['coveredRatio'],residual['sumIntersectionAreaM2']/residual['areaM2'])
            assert close(residual['residualAreaM2'],residual['areaM2']-residual['sumIntersectionAreaM2'])
    assert counts==report['analyticalCounts'] and total_pairs==report['intersectionPairs']
    links=read(folder/'district-links.json')
    people={r['id']:r for r in officials}
    seen=set()
    for row in links['matches']+links['unmatched']:
        assert row['officialId'] in people and row['officialId'] not in seen
        seen.add(row['officialId'])
        assert row['sourceIds']==sorted(s['id'] for s in people[row['officialId']]['sources'])
        if 'districtKey' in row:
            assert row['districtKey'] in keys and keys[row['districtKey']]['state']==row['state']
            assert keys[row['districtKey']]['sourceId'] in row['geometrySourceIds']
            assert set(row['geometrySourceIds']+row['stateCrosswalkSourceIds'])<=source_index.keys()
        else:assert row['reason']
    assert seen==people.keys()
    assert report['linkage']==index['linkageSummary']==links['summary']
    assert len(links['matches'])==links['summary']['matched'] and len(links['unmatched'])==links['summary']['unmatched']
    print('Validated analytical geography:',counts,'positive-area pairs',total_pairs,'linked officials',len(links['matches']))
