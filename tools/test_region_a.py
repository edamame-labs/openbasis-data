"""Parser regression tests for official current/previous member distinctions."""
import sys
import json
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
from regions import region_a as a

class RegionATest(unittest.TestCase):
 def parse(self,key,html):
  with patch.object(a,'finish',lambda rows,*args:rows):
   return a.parse(key,html.encode(),{'url':a.SOURCES[key][1]})

 def test_kentucky_displayed_district_is_not_profile_internal_id(self):
  html='Senate Members - County<table><tr><td>Adair - 16</td><td><a href="https://legislature.ky.gov/Legislators/Pages/Legislator-Profile.aspx?DistrictNumber=116">Wise, Max</a></td><td>Republican</td></tr></table>'
  rows=self.parse('ky-upper',html)
  self.assertEqual(rows[0]['district'],'16')
  self.assertIn('DistrictNumber=116',rows[0]['website'])

 def test_arizona_excludes_inactive_and_keeps_multi_member_district(self):
  def member(name,cls=''):
   return '<tr class="'+cls+'"><td><a href="/member/'+name+'">'+name+'</a></td><td>1</td><td>R</td><td>x</td><td>x</td><td>x</td></tr>'
  rows=self.parse('az-roster','<table id="HouseRoster">'+member('Alice')+member('Betty')+member('Former','inactive')+'</table><table id="SenateRoster">'+member('Carol')+'</table>')
  self.assertEqual([r['name'] for r in rows],['Alice','Betty','Carol'])
  self.assertEqual(len({r['id'] for r in rows}),3)

 def test_arkansas_explicit_departure_labels(self):
  def member(name,status=''):
   return '<div role="row" data-fixed="true"><div aria-colindex="1"><a href="/Legislators/Detail?member=x">'+name+'</a> '+status+'</div><div aria-colindex="2">Chamber: House</div><div aria-colindex="3">Seniority: 1</div><div aria-colindex="4">District: 1</div></div>'
  rows=self.parse('ar-roster','95th General Assembly 2026'+member('Alice')+member('Former','(Resigned)')+member('Late','(Deceased)'))
  self.assertEqual([r['name'] for r in rows],['Alice'])

 def test_colorado_resignation_note_excluded(self):
  def member(name,note=''):
   return '<tr><td data-label="Title">Senator</td><th data-label="Name"><a href="/legislators/test">'+name+'</a>'+note+'</th><td data-label="District">1</td><td data-label="Party">Democrat</td></tr>'
  rows=self.parse('co-roster','2026 Regular Session<table>'+member('Current, Ann')+member('Former, Bob','Senator resigned as of 2/13/26')+'</table>')
  self.assertEqual([r['name'] for r in rows],['Ann Current'])

 def test_iowa_former_member_table_not_current(self):
  def member(name):
   return '<tr><td>House</td><td><a href="/legislators/legislator?ga=91&amp;personID=1">'+name+'</a></td><td>1</td><td>Democrat</td><td>County</td><td>mail</td></tr>'
  rows=self.parse('ia-lower','<table id="sortableTable">'+member('Current Person')+'</table><table>'+member('Former Person (01/13/2025 - 10/05/2026)')+'</table>')
  self.assertEqual([r['name'] for r in rows],['Current Person'])

 def test_alaska_letter_district(self):
  rows=self.parse('ak-upper','<a href="http://www.akleg.gov/basis/Member/Detail/34?code=x"><strong class="name">Ann Person</strong> City: Juneau Party: Democrat District: B Phone: 907-000-0000</a>')
  self.assertEqual(rows[0]['district'],'B')

 def test_kansas_requires_profile_not_abbreviated_directory_name(self):
  with self.assertRaises(AssertionError):self.parse('ks-lower','<tr><td>Rep. Smith</td></tr>')
  rows=self.parse('ks-lower','<h2 class="leg-hero-title">Ann Smith</h2><span class="leg-chamber-badge">House — District 1, County County</span><p class="leg-hero-party">Republican</p>')
  self.assertEqual(rows[0]['name'],'Ann Smith')

 def test_delaware_requires_complete_api_page(self):
  with self.assertRaises(AssertionError):
   self.parse('de-lower',json.dumps({'Data':[],'Total':41,'Errors':None}))
  data={'Data':[{'PersonId':1,'PersonFullName':'Ann Smith','DistrictNumber':1,'PartyCode':'D','ChamberId':2,'LegislatorDetailLink':'https://legis.delaware.gov/LegislatorDetail?personId=1'}], 'Total':1,'Errors':None}
  rows=self.parse('de-lower',json.dumps(data))
  self.assertEqual(rows[0]['name'],'Ann Smith')
  self.assertEqual(rows[0]['sources'][0]['url'],a.SOURCES['de-lower'][1])

 def test_hawaii_ended_term_excluded(self):
  def member(name,note=''):
   return '<div class="contact-box"><a href="/legislature/memberpage.aspx?member=1&amp;year=2026"><h2 class="namecard">'+name+' (D)</h2></a>House District 28 Area '+note+'</div>'
  rows=self.parse('hi-lower','Showing Representatives for the 2026 regular session'+member('Current, Ann')+member('Former, Bob','Term of Office Ended: 02/13/2026'))
  self.assertEqual([r['name'] for r in rows],['Ann Current'])

 def test_florida_house_pending_and_former_sections_excluded(self):
  card='<div class="team-box"><a href="/Sections/Representatives/details.aspx?MemberId=1"><h5>Current, Ann</h5></a>Democrat — District: 1</div>'
  pending='<div class="team-box">Pending Election — District: 2</div>'
  html=card+pending+'<h1>Representatives for 2024 - 2026 ( Speaker Perez ) who served a partial term</h1>'+card.replace('Current','Former')
  rows=self.parse('fl-lower',html)
  self.assertEqual([r['name'] for r in rows],['Ann Current'])

 def test_illinois_desktop_mobile_dedup_and_former_section(self):
  card='<div class="member-card"><h2 class="card-title"><a href="/House/Members/Details/1">Ann Person</a> (D)</h2><p class="card-text">Majority Leader 1st District</p></div>'
  rows=self.parse('il-lower','104th General Assembly (2025-2026)'+card+card+'<h2>Former Members</h2>'+card.replace('Ann','Former'))
  self.assertEqual([r['name'] for r in rows],['Ann Person'])

 def test_georgia_until_annotation_excluded(self):
  def member(name):
   return '<tr><td>Photo</td><td><a href="/members/house/1">'+name+'</a></td><td>Democrat</td><td>1</td><td>City</td></tr>'
  rows=self.parse('ga-lower','2025-2026 Regular Session (Current)<table class="memberList">'+member('Ann Current')+member('Bob Former (Until 03/08/2026)')+'</table>')
  self.assertEqual([r['name'] for r in rows],['Ann Current'])
  future=self.parse('ga-lower','2025-2026 Regular Session (Current)<table class="memberList">'+member('Ann Current (Until 12/31/2099)')+'</table>')
  self.assertEqual([r['name'] for r in future],['Ann Current'])

 def test_indiana_districtless_entry_excluded_without_departure_inference(self):
  html='2026 (Current) Legislators for 2026 Session<a href="/legislative/2026/legislators/legislator_ann_1">Sen. Ann Current (R) District 17 Senate</a><a href="/legislative/2026/legislators/legislator_bob_1">Sen. Bob Unsupported (R) Senate</a>'
  rows=self.parse('in-roster',html)
  self.assertEqual([r['name'] for r in rows],['Ann Current'])
  self.assertIn('has no district',rows[0]['sources'][0]['excludedEntries'][0]['reason'])

 def test_html_challenge_fails_closed(self):
  for key in ['az-roster','ar-roster','co-roster','ct-lower','id-upper','ia-upper','ky-lower','fl-upper']:
   with self.subTest(key=key),self.assertRaises(AssertionError):a.parse(key,b'<html>Request Rejected</html>',{'url':a.SOURCES[key][1]})

if __name__=='__main__':unittest.main()
