"""Analytical overlap tests: dimensionality, denominators, gaps and dateline."""
import unittest
try:
    from shapely.geometry import box, Polygon, mapping
    from pyproj import Transformer
    from overlaps import calculate,intersect_layers,prepare_feature,PROJECTIONS
    AVAILABLE=True
except ImportError:
    AVAILABLE=False

@unittest.skipUnless(AVAILABLE,'Optional geometry dependencies are not installed; use requirements-geo.txt for full analytical tests')
class OverlapTests(unittest.TestCase):
    def item(self,key,layer,geometry):
        return dict(key=key,layer=layer,areaM2=geometry.area,geometryRepaired=False)

    def test_shares_use_both_different_denominators(self):
        a,b=box(0,0,4,2),box(2,0,8,2)
        rows,_=intersect_layers([self.item('cd:a','cd',a)],[a],[self.item('sldu:b','sldu',b)],[b])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['intersectionAreaM2'],4)
        self.assertEqual(rows[0]['shareOfA'],.5)
        self.assertAlmostEqual(rows[0]['shareOfB'],1/3)

    def test_shared_line_has_no_area_overlap(self):
        a,b=box(0,0,1,1),box(1,0,2,1)
        rows,_=intersect_layers([self.item('a','cd',a)],[a],[self.item('b','sldu',b)],[b])
        self.assertEqual(rows,[])

    def test_uncovered_area_is_reported_without_renormalization(self):
        a,b=box(0,0,4,2),box(0,0,1,2)
        rows,diagnostics=intersect_layers([self.item('a','cd',a)],[a],[self.item('b','sldu',b)],[b])
        self.assertEqual(rows[0]['shareOfA'],.25)
        self.assertEqual(next(d for d in diagnostics if d['key']=='a')['coveredRatio'],.25)

    def test_overlapping_partition_is_reported(self):
        a,b,c=box(0,0,2,2),box(0,0,2,2),box(0,0,1,2)
        _,diagnostics=intersect_layers([self.item('a','cd',a)],[a],[self.item('b','sldu',b),self.item('c','sldu',c)],[b,c])
        self.assertEqual(next(d for d in diagnostics if d['key']=='a')['status'],'over-covered')

    def test_invalid_polygon_repair_is_explicit(self):
        feature=dict(properties={'GEOID':'1','STATE':'06'},geometry=mapping(Polygon([(0,0),(2,2),(0,2),(2,0),(0,0)])))
        item,geom,repair=prepare_feature(feature,'cd',Transformer.from_crs(4326,4326,always_xy=True))
        self.assertTrue(item['geometryRepaired'])
        self.assertIsNotNone(repair)
        self.assertTrue(geom.is_valid)
        self.assertEqual(geom.area,2)

    def test_alaska_antimeridian_does_not_become_world_spanning_area(self):
        ring=[(179,52),(-179,52),(-179,53),(179,53),(179,52)]
        feature=dict(properties={'GEOID':'1','STATE':'02'},geometry=mapping(Polygon(ring)))
        item,_,_=prepare_feature(feature,'cd',Transformer.from_crs(4326,PROJECTIONS['AK'],always_xy=True))
        self.assertLess(item['areaM2'],30_000_000_000)
        self.assertGreater(item['areaM2'],1_000_000_000)

    def test_no_population_is_inferred_from_area(self):
        feature=dict(properties={'GEOID':'1','STATE':'06','STUSAB':'CA'},geometry=mapping(box(-122,37,-121,38)))
        fc=dict(type='FeatureCollection',features=[feature],layer={'generalization':'none requested'})
        result=calculate('CA',{'state':fc,'cd':fc})
        self.assertIsNone(result['method']['population'])
        self.assertNotIn('population',result['districts'][0])

    def test_hole_area_and_complete_partition_conserve_area(self):
        a=Polygon([(0,0),(4,0),(4,4),(0,4),(0,0)],holes=[[(1,1),(3,1),(3,3),(1,3),(1,1)]])
        bs=[box(0,0,2,4),box(2,0,4,4)]
        rows,diagnostics=intersect_layers([self.item('a','cd',a)],[a],[self.item(str(i),'sldu',b) for i,b in enumerate(bs)],bs)
        self.assertEqual(sum(r['intersectionAreaM2'] for r in rows),12)
        self.assertEqual(sum(r['shareOfA'] for r in rows),1)
        self.assertFalse([d for d in diagnostics if d['key']=='a'])

    def test_reversing_inputs_swaps_shares(self):
        a,b=box(0,0,4,2),box(2,0,8,2)
        forward,_=intersect_layers([self.item('a','cd',a)],[a],[self.item('b','sldu',b)],[b])
        reverse,_=intersect_layers([self.item('b','sldu',b)],[b],[self.item('a','cd',a)],[a])
        self.assertEqual(forward[0]['intersectionAreaM2'],reverse[0]['intersectionAreaM2'])
        self.assertEqual(forward[0]['shareOfA'],reverse[0]['shareOfB'])

    def test_wrong_or_mixed_state_is_rejected(self):
        state=dict(properties={'GEOID':'06','STATE':'06','STUSAB':'CA'},geometry=mapping(box(-122,37,-121,38)))
        fc=dict(features=[state],layer={'generalization':'none requested'})
        with self.assertRaises(AssertionError): calculate('AK',{'state':fc})
        other=dict(properties={'GEOID':'01','STATE':'01'},geometry=state['geometry'])
        with self.assertRaises(AssertionError): calculate('CA',{'state':fc,'cd':dict(features=[other],layer=fc['layer'])})

    def test_nested_display_generalization_is_rejected(self):
        state=dict(properties={'GEOID':'06','STATE':'06','STUSAB':'CA'},geometry=mapping(box(-122,37,-121,38)))
        for field in ['layer','source']:
            fc=dict(features=[state],layer={'generalization':'none requested'})
            fc[field]={'generalization':'0.001 degrees'}
            with self.assertRaises(AssertionError): calculate('CA',{'state':fc})

    def test_generalized_geometry_rejected(self):
        with self.assertRaises(AssertionError):
            calculate('CA',{'cd':dict(features=[],generalization='0.001 degrees')})

if __name__=='__main__':unittest.main()
