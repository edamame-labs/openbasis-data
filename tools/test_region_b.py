"""Regression tests for roster eligibility, identities, and source structures."""
import csv
import io
import json
import unittest
from unittest.mock import patch
from regions import region_b as roster


class RegionBTests(unittest.TestCase):
    def proof(self,key):
        return {'url':roster.SOURCES[key][1], 'retrievedAt':'2026-11-01T00:00:00+00:00'}

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


if __name__=='__main__':
    unittest.main()
