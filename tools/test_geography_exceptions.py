import copy
import json
import unittest
from geography_exceptions import SOURCES, apply_roster, collect, floterials, parse_components, parse_nd

CSV='Floterial District,Component Census SLDL Code,Component Census SLDL Name\nBE8,3,State House District Belknap 03\nBE8,4,State House District Belknap 04\n'
SOURCE=dict(id='nh-floterial-components',url=SOURCES['nh-floterial-components'][1],sha256='a'*64)
ND_SOURCE=dict(id='nd-district-directory',url=SOURCES['nd-district-directory'][1],sha256='b'*64)


def square(x):
    return {'type':'Polygon','coordinates':[[[x,0],[x+1,0],[x+1,1],[x,1],[x,0]]]}


def base():
    return dict(type='FeatureCollection',layer=dict(vintage='2026-01-01',plan='2024'),features=[
        dict(type='Feature',properties=dict(STATE='33',GEOID='33003',SLDL='003',NAME='State House District Belknap 03',sourceId='census-raw-1'),geometry=square(0)),
        dict(type='Feature',properties=dict(STATE='33',GEOID='33004',SLDL='004',NAME='State House District Belknap 04',sourceId='census-raw-2'),geometry=square(1))])


def data():
    return dict(nhComponents=parse_components(CSV),sources=[SOURCE,ND_SOURCE],ndDistricts=[
        dict(name='Clayton Fegley',district='4B',chamber='Representative',website='https://ndlegis.gov/biography/clayton-fegley'),
        dict(name='Lisa Finley-DeVille',district='4A',chamber='Representative',website='https://ndlegis.gov/biography/lisa-finley-deville')])


class ExceptionTests(unittest.TestCase):
    def test_nd_primary_card_labels(self):
        raw='''<li class="member-item first odd"><div><a href="/biography/clayton-fegley"><div class="member-chamber">Representative</div><div class="strong member-name">Clayton Fegley</div></a><div class="district">District 4B | <span class="sr-only">Republican</span>R</div></div></li>'''
        out=parse_nd(raw)
        self.assertEqual(out[0]['district'],'4B')
        self.assertEqual(out[0]['website'],'https://ndlegis.gov/biography/clayton-fegley')

    def test_exact_member_identity_and_provenance(self):
        rows=[dict(id='f',name='Clayton Fegley',state='ND',level='state',body='North Dakota House of Representatives',district='4',website='https://ndlegis.gov/biography/clayton-fegley',sources=[{'id':'roster'}])]
        before=copy.deepcopy(rows)
        out=apply_roster(rows,data())
        self.assertEqual(rows,before)
        self.assertEqual(out[0]['district'],'4B')
        self.assertEqual(out[0]['sources'][-1],ND_SOURCE)
        self.assertEqual(out[0]['fieldEvidence']['district']['sourceIds'],['nd-district-directory'])
        wrong=copy.deepcopy(rows);wrong[0]['website']='https://ndlegis.gov/biography/somebody-else'
        with self.assertRaisesRegex(AssertionError,'name/profile identity'):
            apply_roster(wrong,data())

    def test_union_preserves_official_identifiers_and_sources(self):
        original=base();before=copy.deepcopy(original)
        out=floterials(original,data())
        self.assertEqual(original,before)
        self.assertEqual(len(out['features']),1)
        props=out['features'][0]['properties']
        self.assertNotIn('GEOID',props)
        self.assertEqual(props['boundaryId'],'33-floterial-BE8')
        self.assertEqual(props['BASENAME'],'Belknap 8')
        self.assertEqual(props['componentKeys'],['sldl:33003','sldl:33004'])
        self.assertEqual(props['componentSourceIds'],['census-raw-1','census-raw-2'])
        self.assertEqual(out['sourceIds'],['census-raw-1','census-raw-2','nh-floterial-components'])
        from shapely.geometry import shape
        self.assertAlmostEqual(shape(out['features'][0]['geometry']).area,2)
        self.assertTrue(out['layer']['derived'])
        json.dumps(out)

    def test_unknown_component_and_label_conflict_fail(self):
        d=data();d['nhComponents'][0]['Component Census SLDL Code']='999'
        with self.assertRaisesRegex(AssertionError,'Missing Census'):
            floterials(base(),d)
        d=data();d['nhComponents'][0]['Component Census SLDL Name']='State House District Belknap 99'
        with self.assertRaisesRegex(AssertionError,'label conflicts'):
            floterials(base(),d)

    def test_invalid_geometry_is_rejected_without_repair(self):
        fc=base();fc['features'][0]['geometry']['coordinates']=[[[0,0],[1,1],[1,0],[0,1],[0,0]]]
        with self.assertRaisesRegex(AssertionError,'Invalid component polygon'):
            floterials(fc,data())

    def test_disjoint_components_remain_multipart(self):
        fc=base();fc['features'][1]['geometry']=square(4)
        out=floterials(fc,data())
        self.assertEqual(out['features'][0]['geometry']['type'],'MultiPolygon')

    def test_duplicate_crosswalk_relationship_rejected(self):
        with self.assertRaisesRegex(AssertionError,'Duplicate NH'):
            parse_components(CSV+'BE8,3,State House District Belknap 03\n')


if __name__=='__main__':
    unittest.main()
