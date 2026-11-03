"""Regression tests for roster eligibility, identities, and source structures."""
import csv
import io
import json
import unittest
from unittest.mock import patch
from regions import region_b as roster


class RegionBTests(unittest.TestCase):
    def proof(self,key):
        return {'id':key, 'url':roster.SOURCES[key][1], 'retrievedAt':'2026-11-01T00:00:00+00:00'}

    def test_minnesota_uses_current_alphabetical_tab_not_stale_elect_tab(self):
        html=b'''<h1>House Member Information 2025 - 2026</h1>
          <div id="Alpha"><a href="/members/profile/1">Current Person (47A, DFL)</a></div>
          <div id="Elect"><a href="/members/profile/2">Previous Person (47A, DFL)</a></div>'''
        with patch.dict(roster.MAXIMUM, MN=(1,1)):
            rows=roster.parse('mn-lower',html,self.proof('mn-lower'))
        self.assertEqual([(r['name'],r['district']) for r in rows],[('Current Person','47A')])

    def test_montana_inactive_record_is_excluded_and_term_conflict_fails(self):
        person=dict(type='LEGISLATOR',isActive=True,startDate='2025-01-01',endDate='2026-11-03',chamber='House',district='HOUSE DISTRICT 1',firstName='Current',lastName='Person',id=1,politicalParty='Republican',links={'profileUrl':'https://legislators.legmt.gov/#/legislator/1'})
        former=dict(person,id=2,isActive=False,lastName='Former')
        with patch.dict(roster.MAXIMUM, MT=(1,1)):
            rows=roster.parse('mt-roster',json.dumps({'content':[person,former],'recordCount':2,'pageable':{'paged':False}}).encode(),self.proof('mt-roster'))
            self.assertEqual([x['name'] for x in rows],['Current Person'])
            person['endDate']='2025-12-31'
            with self.assertRaisesRegex(AssertionError,'Active flag/term date conflict'):
                roster.parse('mt-roster',json.dumps({'content':[person],'recordCount':1,'pageable':{'paged':False}}).encode(),self.proof('mt-roster'))

    def test_new_jersey_two_people_in_one_district_have_distinct_ids(self):
        def person(id,name):
            return dict(First_Name=name,Last_Name='Person',RosterHouseCode='A',Roster_District=1,Party='D',BioLink='/legislative-roster/'+str(id)+'/assembly-member',VacantSort=0)
        data={'page':'/legislative-roster','props':{'pageProps':{'legrosterData':[[person(1,'First'),person(2,'Second')]]}}}
        raw=('<script id="__NEXT_DATA__">'+json.dumps(data)+'</script>').encode()
        with patch.dict(roster.MAXIMUM,NJ=(2,1)):
            rows=roster.parse('nj-roster',raw,self.proof('nj-roster'))
        self.assertEqual(len({x['id'] for x in rows}),2)
        self.assertEqual({x['district'] for x in rows},{'1'})

    def test_massachusetts_named_district_is_retained(self):
        raw=b'<tr><td></td><td></td><td><a href="/Legislators/Profile/AB1">Example</a></td><td>Person</td><td>Suffolk and Middlesex</td><td>Democrat</td><td>101</td><td></td><td></td></tr>'
        with patch.dict(roster.MAXIMUM,MA=(1,1)):
            row=roster.parse('ma-upper',raw,self.proof('ma-upper'))[0]
        self.assertEqual(row['district'],'Suffolk and Middlesex')

    def test_new_hampshire_returning_former_legislator_is_retained(self):
        text=io.StringIO()
        writer=csv.DictWriter(text,fieldnames=['LastName','FirstName','MiddleName','LegislativeBody','electedStatus','District','County','party'],delimiter='\t')
        writer.writeheader()
        writer.writerows([
          dict(LastName='Returner',FirstName='Example',MiddleName='',LegislativeBody='H',electedStatus='Former',District='1',County='Grafton',party='R'),
          dict(LastName='Departed',FirstName='Another',MiddleName='',LegislativeBody='H',electedStatus='Incumbent',District='2',County='Grafton',party='D')])
        proof=self.proof('nh-roster')
        proof['_currentHouseMembers']=[('123','Returner','Example')]
        with patch.dict(roster.MAXIMUM,NH=(1,1)):
            rows=roster.parse('nh-roster',text.getvalue().encode(),proof)
        self.assertEqual([r['name'] for r in rows],['Example Returner'])
        self.assertNotIn('_currentHouseMembers',proof)

    def test_nebraska_previous_period_in_dropdown_does_not_establish_currency(self):
        html=b'<select id="Legislature"><option value="110" label="110th Legislature (2027-2028)">Current</option><option value="109" label="109th Legislature (2025-2026)">Previous</option></select>'
        with self.assertRaisesRegex(AssertionError,'Nebraska current legislature changed'):
            roster.parse('ne-unicameral',html,self.proof('ne-unicameral'))

    def test_conflicting_display_duplicate_is_rejected(self):
        source=self.proof('mi-upper')
        a=roster.make(source,'MI','upper','First Person','1',identifier=10)
        b=roster.make(source,'MI','upper','Second Person','1',identifier=10)
        with self.assertRaisesRegex(AssertionError,'Conflicting duplicate'):
            roster.deduplicate([a,b])

    def test_missing_roster_fails_closed(self):
        with self.assertRaises(AssertionError):
            roster.parse('ma-upper',b'<h1>Service unavailable</h1>',self.proof('ma-upper'))

    def test_nebraska_remains_unicameral(self):
        source=self.proof('ne-unicameral')
        row=roster.make(source,'NE','unicameral','Example Person','1')
        self.assertEqual(row['body'],'Nebraska Legislature')
        self.assertNotIn('lower',roster.COVERAGE['NE'])

    def test_mississippi_presiding_lieutenant_governor_is_not_district_53(self):
        def card(d,name,extra=''):
            return '<div class="active-member" data-chamber="S" data-fiscal_year="26" data-district="'+str(d)+'" '+extra+'><div class="flex-grow-1">'+name+'</div>'+('President of the Senate' if d==53 else '')+'</div>'
        html='2026 Regular Session'+card(1,'Example Senator')+card(53,'Presiding Officer','data-customurl="https://ltgovhosemann.ms.gov/"')
        with patch.dict(roster.MAXIMUM,MS=(1,1)):
            rows=roster.parse('ms-upper',html.encode(),self.proof('ms-upper'))
        self.assertEqual([x['district'] for x in rows],['1'])

    def test_louisiana_contact_and_portrait_from_enclosing_card(self):
        html=b'''<div class="card"><img src="SenPics/Sen25.jpg"><div class="card-body"><h1><a href="smembers.aspx?ID=25">Abraham, Mark</a></h1>
          District 25 Republican <span id="x_DISTRICTOFFICEPHONELabel1_0">(337)475-3016</span>
          <a href="mailto:AbrahamM@legis.la.gov">abrahamm@legis.la.gov</a></div></div>'''
        with patch.dict(roster.MAXIMUM,LA=(1,1)):
            row=roster.parse('la-upper',html,self.proof('la-upper'))[0]
        self.assertEqual((row['email'],row['phone'],row['photo']),('abrahamm@legis.la.gov','337-475-3016','https://senate.la.gov/SenPics/Sen25.jpg'))
        self.assertNotIn('ids',row)  # profile IDs are district numbers

    def test_maine_senate_party_from_listing_line_and_house_placeholder_photo_skipped(self):
        html=b'<p><a href="/district18">Richard A. Bennett</a>&nbsp;(I-Oxford)</p><p><a href="/District20">Bruce Bickford</a></p>'
        with patch.dict(roster.MAXIMUM,ME=(1,2)):
            rows=roster.parse('me-upper',html,self.proof('me-upper'))
        self.assertEqual([r.get('party') for r in rows],['I',None])
        cells='<td><img src="/house/Repository/MemberProfiles/_NoPhotoHolder.jpg"></td><td><a href="/house/MemberProfiles/Details/1492">Mana Abdi</a></td><td>D</td><td>95</td><td></td><td><a href="mailto:Mana.Abdi@legislature.maine.gov">Email</a></td><td></td><td></td>'
        with patch.dict(roster.MAXIMUM,ME=(1,1)):
            row=roster.parse('me-lower',('<tr>'+cells+'</tr>').encode(),self.proof('me-lower'))[0]
        self.assertEqual((row['email'],row['ids']),('mana.abdi@legislature.maine.gov',{'me-lower':'1492'}))
        self.assertNotIn('photo',row)

    def test_missouri_house_grid_joins_only_identical_district_and_name(self):
        source=self.proof('mo-lower')
        rows=[roster.make(source,'MO','lower','Bill Allen','17'),roster.make(source,'MO','lower','New Person','18')]
        grid=b'''<table id="theTable"><tr><th>x</th></tr>
          <tr><td></td><td>Allen</td><td>Bill</td><td>017</td><td>R</td><td>Kansas City</td><td>573-751-1218</td><td>235</td></tr>
          <tr><td></td><td>Other</td><td>Person</td><td>018</td><td>D</td><td>X</td><td>573-751-0000</td><td>1</td></tr></table>'''
        proof=self.proof('mo-lower-grid')
        self.assertEqual(roster.parse('mo-lower-grid',grid,proof),[])
        roster.join(rows,'mo-lower',roster.mo_lower_grid(grid),lambda r:r['district'],proof)
        self.assertEqual((rows[0]['party'],rows[0]['phone']),('R','573-751-1218'))
        self.assertEqual(rows[0]['fieldEvidence']['party'],{'value':'R','sourceIds':['mo-lower-grid']})
        self.assertEqual([s['id'] for s in rows[0]['sources']],['mo-lower','mo-lower-grid'])
        self.assertNotIn('party',rows[1])
        self.assertEqual(len(rows[1]['sources']),1)

    def test_missouri_senate_directory_joins_by_member_id(self):
        roster_html=b'<a href="https://www.senate.mo.gov/Senators/Member?id=2"><img src="https://www.senate.mo.gov/WebPhotos/SenatorPortraits/Bean25.jpg">Senator Jason Bean District 25</a>'
        with patch.dict(roster.MAXIMUM,MO=(1,1)):
            rows=roster.parse('mo-upper',roster_html,self.proof('mo-upper'))
        def card(href,name,district,party,phone):
            item=lambda k,v:'<div class="detail-grid__item"><span class="detail-grid__label">'+k+'</span><span class="detail-grid__value">'+v+'</span></div>'
            return '<div class="card"><div class="card__header card__header--gradient"><a href="'+href+'">'+name+'</a></div><div class="detail-grid">'+item('District',district)+item('Party',party)+item('Capitol Phone',phone)+'</div></div>'
        page='<div class="card">'+card('https://www.senate.mo.gov/Senators/member?id=2','Jason Bean','District 25','Republican','573-751-4843&#xD;&#xA;')+card('https://www.senate.mo.gov/Senators/VacantSenator?district=10','Vacant','District 10','','573-751-2757')+'</div>'
        roster.join(rows,'mo-upper',roster.mo_upper_directory(page.encode()),lambda r:r['ids']['mo-upper'],self.proof('mo-upper-directory'))
        self.assertEqual({k:rows[0][k] for k in ['party','phone','photo','ids']},{'party':'Republican','phone':'573-751-4843','photo':'https://www.senate.mo.gov/WebPhotos/SenatorPortraits/Bean25.jpg','ids':{'mo-upper':'2'}})

    def test_new_york_assembly_uses_albany_office_line_not_fax(self):
        html=b'''<section class="mem-item" id="121"><div class="mem-pic"><a href="Joe-Angelino"><img src="/write/upload/member_files/121/headshot/121.jpg"></a></div>
          <div class="mem-info"><h3 class="mem-name"><a href="/mem/Joe-Angelino">Joe Angelino <span>District 121</span></a></h3>
          <div class="mem-email"><a href="mailto:angelinoj@nyassembly.gov">angelinoj@nyassembly.gov</a></div></div>
          <div class="mem-address"><div class="full-addr">1 Road Binghamton, NY 13901 607-648-6080 Fax: 607-648-6089</div>
          <div class="full-addr">LOB 549 <br/> Albany, NY 12248 <br/> 518-455-5741 Fax: 518-455-5864</div></div></section>'''
        with patch.dict(roster.MAXIMUM,NY=(1,1)):
            row=roster.parse('ny-lower',html,self.proof('ny-lower'))[0]
        self.assertEqual((row['phone'],row['email'],row['photo'],row['ids']),('518-455-5741','angelinoj@nyassembly.gov','https://nyassembly.gov/write/upload/member_files/121/headshot/121.jpg',{'ny-lower':'Joe-Angelino'}))
        self.assertNotIn('party',row)

    def test_minnesota_senate_portrait_path_and_contacts(self):
        member=dict(mem_id=1216,preferred_full_name='Jim Abeler',party='R',dist='35',mem_bio_pic='35Abeler.jpg',email='sen.jim.abeler@mnsenate.gov',full_phone_number='651-296-3733')
        with patch.dict(roster.MAXIMUM,MN=(1,1)):
            row=roster.parse('mn-upper',json.dumps({'members':[member]}).encode(),self.proof('mn-upper'))[0]
        self.assertEqual((row['photo'],row['phone'],row['ids']),('https://www.mnsenate.gov/img/member_thumbnails/35Abeler.jpg','651-296-3733',{'mn-upper':'1216'}))

    def test_nevada_phone_comes_from_following_detail_row(self):
        html=b'''Current Senators<table><tbody><tr class="thisRow listRow"><td><a href="/x"><img src="https://www.leg.state.nv.us/a.jpg"></a></td>
          <td data-order="Doe, Jane"><a href="/App/Legislator/A/Senate/Current/1">Doe, Jane</a></td><td data-order="Democratic"></td><td data-order="No. 1"></td><td></td></tr>
          <tr class="thisRow"><td colspan="3"><div class="col-6"><span class="fieldName">Carson City Phone:</span> <span class="field">(775) 684-1421</span></div>
          <div class="col-6"><span class="fieldName">Las Vegas Phone:</span> <span class="field">(702) 486-0000</span></div></td></tr></tbody></table>'''
        with patch.dict(roster.MAXIMUM,NV=(1,1)):
            row=roster.parse('nv-upper',html,self.proof('nv-upper'))[0]
        self.assertEqual((row['name'],row['phone'],row['photo']),('Jane Doe','775-684-1421','https://www.leg.state.nv.us/a.jpg'))


if __name__=='__main__':
    unittest.main()
