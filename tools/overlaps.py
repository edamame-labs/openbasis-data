"""Reproducible polygon-area intersections; no population or address inference."""
from collections import defaultdict
import hashlib
from itertools import combinations
import json
import math

import pyproj
from pyproj import CRS, Transformer
import shapely
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely import STRtree, make_valid

BASE_LAYERS = ['state','county','cd','sldu','sldl','cd120']
LAYER_ORDER = BASE_LAYERS + ['sldl_floterial']
PROJECTIONS = {
    'conus': '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 +datum=WGS84 +units=m +type=crs',
    'AK': '+proj=aea +lat_1=55 +lat_2=65 +lat_0=50 +lon_0=-154 +datum=WGS84 +units=m +type=crs',
    'HI': '+proj=laea +lat_0=20 +lon_0=-157 +datum=WGS84 +units=m +type=crs',
}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def polygonal(geometry):
    if geometry.geom_type in {'Polygon','MultiPolygon'}: return geometry
    pieces=[]
    for part in getattr(geometry,'geoms',[]):
        candidate=polygonal(part)
        if not candidate.is_empty: pieces.append(candidate)
    return unary_union(pieces)


def prepare_feature(feature, layer, transformer):
    props=feature['properties']
    raw=feature['geometry']
    assert raw and raw['type'] in {'Polygon','MultiPolygon'}, 'Missing polygon geometry'
    original=shape(raw)
    projected=shapely.transform(original,transformer.transform,interleaved=False)
    assert not projected.is_empty and all(math.isfinite(v) for v in projected.bounds), 'Invalid projected extent'
    boundary_id=props.get('GEOID') or props['boundaryId']
    key=layer+':'+str(boundary_id)
    repair=None
    if not projected.is_valid:
        reason=shapely.is_valid_reason(projected)
        repaired=polygonal(make_valid(projected))
        assert repaired.is_valid and not repaired.is_empty,'Unrepairable polygon'
        repair=dict(key=key,reason=reason,method='GEOS make_valid linework; polygonal components retained',
                    originalGeometrySha256=sha(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()),
                    projectedBeforeSha256=sha(projected.wkb),projectedAfterSha256=sha(repaired.wkb),
                    beforeAreaM2=projected.area,afterAreaM2=repaired.area)
        projected=repaired
    assert projected.area>0 and math.isfinite(projected.area), 'Non-positive polygon area'
    item=dict(key=key,layer=layer,geoid=props.get('GEOID'),boundaryId=boundary_id,stateFips=str(props['STATE']),
              name=props.get('NAME',props.get('BASENAME','')),districtKind=props.get('districtKind','district'),
              sourceId=props.get('sourceId'),areaM2=projected.area,geometryRepaired=repair is not None)
    return item,projected,repair


def intersect_layers(items_a, geometries_a, items_b, geometries_b):
    """One unordered row per positive-area cross-layer pair, with both shares."""
    if not geometries_a or not geometries_b: return [],[]
    tree=STRtree(geometries_b)
    rows=[]
    covered_a=defaultdict(float)
    covered_b=defaultdict(float)
    for i,a in enumerate(geometries_a):
        for index in tree.query(a,predicate='intersects'):
            j=int(index)
            area=a.intersection(geometries_b[j]).area
            assert math.isfinite(area) and area>=0,'Non-finite intersection'
            if area==0: continue  # A shared boundary line is not a positive area.
            ra=area/a.area
            rb=area/geometries_b[j].area
            assert ra<=1+1e-8 and rb<=1+1e-8,'Intersection exceeds an input area'
            rows.append(dict(a=items_a[i]['key'],b=items_b[j]['key'],intersectionAreaM2=area,
                             shareOfA=ra,shareOfB=rb,
                             geometryRepaired=items_a[i]['geometryRepaired'] or items_b[j]['geometryRepaired']))
            covered_a[i]+=area
            covered_b[j]+=area
    diagnostics=[]
    for items,covered,other in [(items_a,covered_a,items_b[0]['layer']),(items_b,covered_b,items_a[0]['layer'])]:
        for i,item in enumerate(items):
            area=item['areaM2']
            total=covered[i]
            fraction=total/area
            # Do not renormalize missing coverage, slivers, or overlapping inputs.
            if abs(fraction-1)>1e-6:
                diagnostics.append(dict(key=item['key'],againstLayer=other,areaM2=area,
                                        sumIntersectionAreaM2=total,coveredRatio=fraction,
                                        residualAreaM2=area-total,
                                        status='over-covered' if fraction>1 else 'under-covered'))
    rows.sort(key=lambda r:(r['a'],r['b']))
    return rows,diagnostics


def calculate(state, collections):
    definition=PROJECTIONS.get(state,PROJECTIONS['conus'])
    crs=CRS.from_user_input(definition)
    transformer=Transformer.from_crs('EPSG:4326',crs,always_xy=True)
    state_features=collections.get('state',{}).get('features',[])
    assert len(state_features)==1, 'Analytical state polygon is required'
    state_props=state_features[0]['properties']
    assert state_props.get('STUSAB')==state,'Requested state differs from the official state crosswalk'
    expected_fips=str(state_props['STATE'])
    items_by_layer={}
    geometries_by_layer={}
    repairs=[]
    for layer in LAYER_ORDER:
        if layer not in collections: continue
        fc=collections[layer]
        assert fc.get('layer',{}).get('generalization')=='none requested', 'Explicit un-generalized analytical provenance required'
        for evidence in [fc,fc.get('source',{}),*fc.get('sources',[])]:
            assert evidence.get('generalization') in {None,'none requested'}, 'Generalized geometry cannot be used analytically'
        items=[]
        geoms=[]
        for feature in fc['features']:
            assert str(feature['properties']['STATE'])==expected_fips,'Mixed-state geometry inputs'
            item,geom,repair=prepare_feature(feature,layer,transformer)
            items.append(item)
            geoms.append(geom)
            if repair: repairs.append(repair)
        assert len({i['key'] for i in items})==len(items),'Duplicate feature key'
        items_by_layer[layer]=items
        geometries_by_layer[layer]=geoms
    internal=[]
    for layer,geoms in geometries_by_layer.items():
        tree=STRtree(geoms)
        for i,geom in enumerate(geoms):
            for j_value in tree.query(geom,predicate='intersects'):
                j=int(j_value)
                if j<=i: continue
                area=geom.intersection(geoms[j]).area
                if area/min(geom.area,geoms[j].area)>1e-6:
                    internal.append(dict(layer=layer,a=items_by_layer[layer][i]['key'],b=items_by_layer[layer][j]['key'],intersectionAreaM2=area,note='Non-disjoint same-layer polygons; do not assume partition totals equal one'))
    pairs=[]
    diagnostics=[]
    for a,b in combinations(items_by_layer,2):
        if not items_by_layer[a] or not items_by_layer[b]: continue
        intersections,coverage=intersect_layers(items_by_layer[a],geometries_by_layer[a],items_by_layer[b],geometries_by_layer[b])
        pairs.extend(intersections)
        diagnostics.extend(coverage)
    return dict(schemaVersion=1,state=state,
                method=dict(measure='polygon-area-including-water',units='square-metres',
                            projection=definition,projectionWkt=crs.to_wkt(),alwaysXY=True,
                            intersection='GEOS planar intersection in equal-area projection',
                            geometryPrecision='Original Census coordinates; no generalization, snapping or coordinate rounding',
                            numericalCoverageTolerance=1e-6,population=None,
                            software=dict(shapely=shapely.__version__,geos=shapely.geos_version_string,
                                          pyproj=pyproj.__version__,proj=pyproj.proj_version_str)),
                layerCounts={layer:len(items) for layer,items in items_by_layer.items()},
                districts=[item for items in items_by_layer.values() for item in items],
                overlaps=pairs,geometryRepairs=repairs,coverageResiduals=diagnostics,sameLayerIntersections=internal)
