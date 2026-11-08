"""Publish original government polygons, deterministic links and area overlays."""
from collections import Counter
import csv
import json
from pathlib import Path

from district_links import link
from overlaps import calculate,LAYER_ORDER,BASE_LAYERS
from geography_exceptions import floterials


from geo_io import write_json,read_json


def source_ids(fc,features,fips):
    used={f['properties']['sourceId'] for f in features}
    for source in fc['sources']:
        if source['id'].endswith('-metadata') or '-'+fips+'-count' in source['id'] or source.get('withholdsState')==fips:
            used.add(source['id'])
    return sorted(used)


def write(stage,officials,layer_packets,exception_data):
    """Consume one national layer at a time, then analyze bounded per-state data."""
    geography_index=dict(schemaVersion=1,coordinateReferenceSystem='EPSG:4326',
                         geometry='Original Census coordinates without requested generalization',
                         sourceIds=[],layers={},states=[])
    evidence=[]
    slim={}
    state_properties={}
    counts={}
    for layer,fc,layer_sources in layer_packets:
        assert layer in BASE_LAYERS and layer not in slim
        evidence.extend(layer_sources)
        geography_index['layers'][layer]=fc['layer']
        counts[layer]=len(fc['features'])
        if layer=='state':
            assert len(fc['features'])==50
            state_properties={f['properties']['STATE']:f['properties'] for f in fc['features']}
        assert len(state_properties)==50,'Acquire the authoritative state crosswalk first'
        by_fips={}
        for feature in fc['features']:
            by_fips.setdefault(feature['properties']['STATE'],[]).append(feature)
        slim[layer]=dict(type='FeatureCollection',features=[dict(type='Feature',properties=f['properties'],geometry=None) for f in fc['features']],sources=layer_sources,layer=fc['layer'])
        withheld={w['state']:w for w in fc['layer'].get('withheldStates',[])}
        for fips,p in state_properties.items():
            st=p['STUSAB']
            features=by_fips.get(fips,[])
            if not features: assert layer=='sldl' and st=='NE' or fips in withheld,'Missing analytical layer: '+st+' '+layer
            local=dict(type='FeatureCollection',layer=fc['layer'],features=features,sourceIds=source_ids(fc,features,fips))
            if fips in withheld: local['withheld']=withheld[fips]
            path=Path('geography/regions')/st.lower()/(layer+'.geojson.gz')
            write_json(stage/path,local,compact=True)
            assert (stage/path).stat().st_size<95_000_000,'Geometry artifact exceeds reviewable file size; split before publishing'
        print('Saved original analytical layer',layer,counts[layer],'features',flush=True)
        del fc,by_fips,features,local
    assert set(slim)==set(BASE_LAYERS),'All six analytical layers are required'
    geography_index['sourceIds']=[s['id'] for s in evidence]
    reports=[]
    total_intersections=0
    for fips,p in sorted(state_properties.items(),key=lambda item:item[1]['STUSAB']):
        st=p['STUSAB']
        paths={layer:str(Path('geography/regions')/st.lower()/(layer+'.geojson.gz')) for layer in BASE_LAYERS}
        local={layer:read_json(stage/path) for layer,path in paths.items()}
        if st=='NH':
            fc=floterials(local['sldl'],exception_data)
            counts['sldl_floterial']=len(fc['features'])
            geography_index['layers']['sldl_floterial']=fc['layer']
            local['sldl_floterial']=fc
            slim['sldl_floterial']=dict(type='FeatureCollection',features=[dict(type='Feature',properties=f['properties'],geometry=None) for f in fc['features']],sourceIds=fc['sourceIds'],layer=fc['layer'])
            path='geography/regions/nh/sldl_floterial.geojson.gz'
            paths['sldl_floterial']=path
            write_json(stage/path,fc,compact=True)
        result=calculate(st,local)
        result['inputFiles']=paths
        result['sourceIds']=sorted({i for fc in local.values() for i in fc['sourceIds']})
        write_json(stage/'overlaps'/(st.lower()+'.json'),result)
        with (stage/'overlaps'/(st.lower()+'.csv')).open('w',newline='') as f:
            columns=['a','b','intersectionAreaM2','shareOfA','shareOfB','geometryRepaired']
            writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n')
            writer.writeheader()
            writer.writerows(result['overlaps'])
        row=dict(state=st,layerCounts=result['layerCounts'],files=paths,
                 overlapFile='overlaps/'+st.lower()+'.json',intersectionPairs=len(result['overlaps']),
                 repairedGeometries=len(result['geometryRepairs']),coverageResiduals=len(result['coverageResiduals']),
                 sameLayerIntersections=len(result['sameLayerIntersections']))
        geography_index['states'].append(row)
        reports.append({**row,'geometryRepairs':result['geometryRepairs'],'coverageResiduals':result['coverageResiduals'],'sameLayerIntersections':result['sameLayerIntersections']})
        total_intersections+=len(result['overlaps'])
        print('Geography',st,result['layerCounts'],'intersections',len(result['overlaps']),flush=True)
        del result,local
    linkage=link(officials,{**slim,'states':slim['state']})
    geography_index['linkageSummary']=linkage['summary']
    write_json(stage/'district-links.json',linkage)
    write_json(stage/'geography/index.json',geography_index)
    summary=dict(schemaVersion=1,measure='polygon-area-including-water',populationOverlap='not-calculated',
                 geometryVintage='2026-01-01',congress='119th',futureCongress=dict(layer='cd120',congress='120th',joinedToOfficials=False),stateLegislativePlan='Census 2024 SLD',
                 states=50,analyticalCounts=counts,intersectionPairs=total_intersections,
                 geometryRepairs=sum(s['repairedGeometries'] for s in reports),
                 coverageResiduals=sum(len(s['coverageResiduals']) for s in reports),
                 sameLayerIntersections=sum(len(s['sameLayerIntersections']) for s in reports),
                 linkage=linkage['summary'],stateReports=reports,
                 limitations=['Derived planar polygon areas include water and do not measure people, voters or land-only area.',
                              'Some layer pairs are not disjoint partitions. Residuals are preserved without renormalization.',
                              'Geometry repairs are explicit derived transformations; original published coordinates remain unchanged.',
                              'An exact district label join is not an independent legal determination of a plan applicability.',
                              '120th Congress plans are published as the separate cd120 layer and never substituted for cd or joined to current officeholders; 2026 legislative election plans are not collected.',
                              'cd120 omits states whose Census 120th Congress geometry the Census Bureau reports as not reflecting the plan in effect; see withheldStates.'])
    write_json(stage/'geography-report.json',summary)
    return summary,evidence
