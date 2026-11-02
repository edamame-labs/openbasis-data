#!/usr/bin/env python3
"""Export one intersection polygon from the published original Census inputs."""
import argparse
import json
from geo_io import read_json
from pathlib import Path
import shapely
from shapely.geometry import mapping
from pyproj import Transformer
from overlaps import PROJECTIONS,prepare_feature


def export(folder,state,key_a,key_b):
    state=state.upper()
    assert state in {row['state'] for row in json.loads((folder/'geography/index.json').read_text())['states']}
    definition=PROJECTIONS.get(state,PROJECTIONS['conus'])
    forward=Transformer.from_crs(4326,definition,always_xy=True)
    reverse=Transformer.from_crs(definition,4326,always_xy=True)
    inputs=[]
    evidence=set()
    for key in [key_a,key_b]:
        layer,geoid=key.split(':',1)
        assert layer in {'state','county','cd','sldu','sldl','sldl_floterial'} and all(c.isalnum() or c=='-' for c in geoid)
        fc=read_json(folder/'geography/regions'/state.lower()/(layer+'.geojson.gz'))
        feature=next(f for f in fc['features'] if str(f['properties'].get('GEOID') or f['properties']['boundaryId'])==geoid)
        item,geom,repair=prepare_feature(feature,layer,forward)
        inputs.append((item,geom,repair))
        evidence.add(feature['properties']['sourceId'])
        evidence.update(feature['properties'].get('componentSourceIds',[]))
    result=inputs[0][1].intersection(inputs[1][1])
    assert not result.is_empty and result.area>0,'No positive-area intersection'
    geographic=shapely.transform(result,reverse.transform,interleaved=False)
    return dict(type='Feature',properties=dict(state=state,a=key_a,b=key_b,
                intersectionAreaM2=result.area,measure='polygon-area-including-water',
                geometryRepaired=any(i[2] for i in inputs),sourceIds=sorted(evidence),projection=definition),
                geometry=mapping(geographic))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',required=True)
    parser.add_argument('--a',required=True)
    parser.add_argument('--b',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    folder=Path(__file__).resolve().parents[1]/'data'
    args.output.write_text(json.dumps(export(folder,args.state,args.a,args.b),ensure_ascii=False,allow_nan=False)+'\n')
