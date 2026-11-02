import copy
import unittest
from district_links import link


def feature(state, geoid, basename, **fields):
    return {'type':'Feature','properties':dict(STATE=state,GEOID=geoid,BASENAME=basename,**fields),'geometry':None}


def row(i, state='CA', district='1', body='California State Assembly', level='state'):
    return dict(id=i,state=state,district=district,body=body,level=level,sources=[{'id':'roster-'+state}])


def collection(features, source='geometry'):
    return {'type':'FeatureCollection','features':features,'source':{'id':source}}


class DistrictLinksTest(unittest.TestCase):
    def setUp(self):
        self.geo={'states':collection([
            feature('06','06','California',STUSAB='CA'),feature('02','02','Alaska',STUSAB='AK'),
            feature('33','33','New Hampshire',STUSAB='NH'),feature('24','24','Maryland',STUSAB='MD'),
            feature('25','25','Massachusetts',STUSAB='MA'),feature('50','50','Vermont',STUSAB='VT')], 'states')}

    def test_state_chamber_scope_many_members_and_immutable_inputs(self):
        self.geo['sldl']=collection([feature('06','06001','1',SLDL='001'),feature('02','02001','1',SLDL='001')])
        self.geo['sldu']=collection([feature('06','06001','1',SLDU='001')])
        rows=[row('one'),row('two'),row('other-state','AK',body='Alaska House'),row('upper',body='California Senate')]
        before=copy.deepcopy((rows,self.geo))
        out=link(rows,self.geo)
        self.assertEqual(out['summary']['matched'],4)
        self.assertEqual([r['districtKey'] for r in out['matches']],['sldl:06001','sldl:06001','sldl:02001','sldu:06001'])
        self.assertEqual(out['matches'][0]['sourceIds'],['roster-CA'])
        self.assertEqual(out['matches'][0]['geometrySourceIds'],['geometry'])
        self.assertEqual((rows,self.geo),before)

    def test_literal_letters_and_subdistricts(self):
        self.geo['sldu']=collection([feature('02','0200A','A',SLDU='00A')])
        self.geo['sldl']=collection([feature('24','2437B','37B',SLDL='37B')])
        out=link([row('a','AK','A','Alaska Senate'),row('b','MD','37B','Maryland House')],self.geo)
        self.assertEqual(out['summary']['matched'],2)
        self.assertEqual(out['matches'][0]['GEOID'],'0200A')

    def test_named_district_formatting(self):
        self.geo['sldl']=collection([feature('33','33804','Strafford 04',SLDL='804'),feature('25','25ABC','Barnstable-Dukes-Nantucket',SLDL='ABC')])
        self.geo['sldu']=collection([feature('50','50CHS','Chittenden South East',SLDU='CHS')])
        rows=[row('nh','NH','Strafford 4','New Hampshire House'),row('ma','MA','Barnstable, Dukes and Nantucket','Massachusetts House'),row('vt','VT','Chittenden-Southeast District','Vermont Senate')]
        self.assertEqual(link(rows,self.geo)['summary']['matched'],3)

    def test_floterial_and_unrecognized_number_do_not_guess(self):
        self.geo['sldl']=collection([feature('33','33804','Strafford 04',SLDL='804')])
        self.geo['sldu']=collection([feature('06','06001','1',SLDU='001')])
        out=link([row('nh','NH','Strafford 18','New Hampshire House'),row('wrong','CA','101','California Senate')],self.geo)
        self.assertEqual(out['summary']['matched'],0)
        self.assertEqual({r['reason'] for r in out['unmatched']},{'no-exact-official-district-label'})

    def test_nh_floterial_fallback_keeps_derived_identity_and_sources(self):
        self.geo['sldl']=collection([feature('33','33804','Strafford 04',SLDL='804')])
        derived={'type':'Feature','properties':{
            'STATE':'33','boundaryId':'33-floterial-ST18','NH_FLT':'ST18',
            'BASENAME':'Strafford 18','districtKind':'floterial',
            'sourceId':'nh-floterial-components',
            'componentKeys':['sldl:33803','sldl:33804'],
            'componentSourceIds':['census-nh-components-raw']},'geometry':None}
        self.geo['sldl_floterial']={'type':'FeatureCollection','features':[derived],
            'sources':[{'id':'nh-floterial-components'},{'id':'census-nh-components-raw'},
                       {'id':'unrelated-geometry-response'}]}
        rows=[row('nh-one','NH','Strafford 18','New Hampshire House'),
              row('nh-two','NH','Strafford 18','New Hampshire House')]
        before=copy.deepcopy((rows,self.geo))
        out=link(rows,self.geo)
        self.assertEqual(out['summary']['matched'],2)
        self.assertEqual(out['unmatched'],[])
        for match in out['matches']:
            self.assertEqual(match['layer'],'sldl_floterial')
            self.assertEqual(match['districtKey'],'sldl_floterial:33-floterial-ST18')
            self.assertEqual(match['boundaryId'],'33-floterial-ST18')
            self.assertIsNone(match['GEOID'])
            self.assertEqual(match['geometrySourceIds'],
                             ['census-nh-components-raw','nh-floterial-components'])
            self.assertEqual(match['sourceIds'],['roster-NH'])
            self.assertEqual(match['stateCrosswalkSourceIds'],['states'])
        self.assertEqual((rows,self.geo),before)

    def test_senate_state_and_at_large_congress(self):
        self.geo['cd']=collection([feature('02','0200','Congressional District (at Large)',CD119='00')])
        out=link([row('sen','AK',None,'U.S. Senate','federal'),row('rep','AK','0','U.S. House','federal')],self.geo)
        self.assertEqual(out['summary']['matched'],2)
        self.assertEqual(out['matches'][0]['districtKey'],'state:02')
        self.assertEqual(out['matches'][1]['districtKey'],'cd:0200')

    def test_ambiguous_names_and_duplicate_geoid(self):
        self.geo['sldl']=collection([feature('06','06001','1',SLDL='001'),feature('06','06ABC','1',SLDL='ABC')])
        self.assertEqual(link([row('x')],self.geo)['unmatched'][0]['reason'],'ambiguous-official-district-label')
        self.geo['sldl']['features'].append(self.geo['sldl']['features'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate geometry ID'):
            link([row('x')],self.geo)

    def test_future_congress_geometry_rejected(self):
        self.geo['cd']=collection([feature('02','0200','At Large',CD120='00')])
        with self.assertRaisesRegex(ValueError,'120th Congress'):
            link([row('rep','AK','0','U.S. House','federal')],self.geo)


if __name__=='__main__':
    unittest.main()
