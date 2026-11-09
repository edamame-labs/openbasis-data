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
   return a.parse(key,html.encode(),{'id':key,'url':a.SOURCES[key][1]})

 def test_kentucky_displayed_district_is_not_profile_internal_id(self):
  html='Senate Members - County<table><tr><td>Adair - 16</td><td><a href="https://legislature.ky.gov/Legislators/Pages/Legislator-Profile.aspx?DistrictNumber=116">Wise, Max</a></td><td>Republican</td></tr></table>'
  rows=self.parse('ky-upper',html)
  self.assertEqual(rows[0]['district'],'16')
  self.assertIn('DistrictNumber=116',rows[0]['website'])

 def test_arizona_excludes_inactive_and_keeps_multi_member_district(self):
  def member(name,cls=''):
   return '<tr class="'+cls+'"><td><a href="/member/'+name+'">'+name+'</a></td><td>1</td><td>R</td><td>x</td><td>x</td><td>x</td></tr>'
  head='<th title="Same suffix for all members">Email @azleg.gov</th>'
  rows=self.parse('az-roster',head+head+'<table id="HouseRoster">'+member('Alice')+member('Betty')+member('Former','inactive')+'</table><table id="SenateRoster">'+member('Carol')+'</table>')
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
  html=card+pending+'<h1>Representatives for 2026 - 2028 ( Speaker Perez ) who served a partial term</h1>'+card.replace('Current','Former')
  rows=self.parse('fl-lower',html)
  self.assertEqual([r['name'] for r in rows],['Ann Current'])

 def test_florida_house_new_term_without_partial_section_checks_card_dates(self):
  def card(name,dates):
   return '<div class="team-box"><a href="/Sections/Representatives/details.aspx?MemberId=1&amp;LegislativeTermId=92"><h5>'+name+'</h5><p>Democrat — District: 1</p><p> '+dates+' </p></a></div>'
  title='<title>Representatives for 2026 - 2028</title>'
  with patch.object(a,'finish',lambda rows,lo,hi:rows):
   rows=a.parse('fl-lower',(title+card('Current, Ann','11/04/26 - 11/07/28')).encode(),{'id':'fl-lower','url':a.SOURCES['fl-lower'][1],'retrievedAt':'2026-11-09T00:00:00+00:00'})
   self.assertEqual([r['name'] for r in rows],['Ann Current'])
   with self.assertRaisesRegex(AssertionError,'service dates'):
    a.parse('fl-lower',(title+card('Elect, Bob','11/08/28 - 11/03/30')).encode(),{'id':'fl-lower','url':a.SOURCES['fl-lower'][1],'retrievedAt':'2026-11-09T00:00:00+00:00'})

 def test_term_begun_rosters_are_withheld_and_reported_not_collected(self):
  for key,(st,chambers,_) in a.TERM_BEGUN.items():
   for ch in chambers:self.assertEqual(a.COVERAGE[st][ch],'not-collected')
   self.assertTrue(any(a.SOURCES[key][1] in b for b in a.COVERAGE[st]['blockers']))

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

 def test_alaska_capitol_phone_joined_by_member_code(self):
  block='<li><a href="http://www.akleg.gov/basis/Member/Detail/34?code=abc"><img src="//akleg.gov/images/legislators/rounded/ABC.png"><strong class="name">Ann Person</strong></a><dl><dt>City:</dt><dd>Juneau</dd><dt>Phone:</dt><dd>907-465-1111</dd></dl></li>'
  card='<a href="http://www.akleg.gov/basis/Member/Detail/34?code=abc"><img src="//akleg.gov/images/legislators/rounded/ABC.png"><strong class="name">Ann Person</strong> City: Kenai Party: Democrat District: B Phone: 907-283-0000</a>'
  r=self.parse('ak-upper','<ul>'+block+'</ul>'+card)[0]
  self.assertEqual((r['phone'],r['photo'],r['ids']),('907-465-1111','https://akleg.gov/images/legislators/rounded/ABC.png',{'ak-upper':'abc'}))

 def test_alabama_api_contact_fields(self):
  data={'data':{'legislativeMembers':{'data':[{'id':'7','body':'House','fullName':'Ann Smith','district':'House District 3','honorificFullNameAffiliation':'Representative Ann Smith (R)','phone':'(334) 261-0000','email':'Ann@ALHouse.gov','imageUrl':'https://alison.legislature.state.al.us/files/a.png'}]}}}
  r=self.parse('al-roster',json.dumps(data))[0]
  self.assertEqual((r['email'],r['phone'],r['ids']),('ann@alhouse.gov','334-261-0000',{'al-roster':'7'}))

 def test_arizona_email_local_part_uses_stated_domain(self):
  head='<th title="Same suffix for all members">Email @azleg.gov</th>'
  tr='<tr><td><a href="https://www.azleg.gov/House/House-member/?legislature=57&amp;session=130&amp;legislator=2349">Ann Luna<span><img src="https://www.azleg.gov/x.jpg"></span></a></td><td>1</td><td>D</td><td><a href="/emailazleg/?legislatorId=2349">Email: ALUNA-NAJERA</a></td><td>Room 1</td><td>(602) 926-0000</td></tr>'
  r=self.parse('az-roster',head+head+'<table id="HouseRoster">'+tr+'</table><table id="SenateRoster"></table>')[0]
  self.assertEqual((r['name'],r['email'],r['phone'],r['ids']),('Ann Luna','aluna-najera@azleg.gov','602-926-0000',{'az-roster':'2349'}))
  with self.assertRaises(AssertionError):self.parse('az-roster','<table id="HouseRoster">'+tr+'</table><table id="SenateRoster"></table>')

 def test_arkansas_house_party_requires_matching_family_name(self):
  def card(d,name,party,cls='party-republican'):
   return '<a href="https://www.arkansashouse.org/district/'+d+'/" class="rep-card '+cls+'"><span class="rep-card__name">'+name+'</span><span class="rep-card__party">'+party+' </span><span class="rep-card__meta">District '+d+'</span></a>'
  html='Members of the 95th General Assembly'+card('1','Brandon C. Achor','Republican','party-independent')+card('2','Someone Else','Democrat')+''.join(card(str(d),'X Y','Republican') for d in range(3,98))
  src={'id':'ar-roster','url':a.SOURCES['ar-roster'][1]}
  rows=[a.row(src,'AR','lower','Brandon Achor','1'),a.row(src,'AR','lower','Fred Allen','2'),a.row(src,'AR','upper','Sen Person','1')]
  fetch=lambda key,publisher,url,offline:(html.encode(),{'id':key,'url':url})
  a.arkansas_house_party(fetch,True,rows)
  self.assertEqual(rows[0]['party'],'Republican')
  self.assertEqual(rows[0]['fieldEvidence']['party'],{'value':'Republican','sourceIds':['ar-house-members']})
  self.assertEqual([s['id'] for s in rows[0]['sources']],['ar-roster','ar-house-members'])
  self.assertNotIn('party',rows[1]);self.assertNotIn('party',rows[2])

 def test_kansas_profile_contact_skips_fallback_photo_and_obfuscated_email(self):
  html='<img class="leg-hero-photo" src="/static/li_pics/fallback.1.jpg"><h2 class="leg-hero-title">Ann Smith</h2><span class="leg-chamber-badge">House — District 1, County County</span><p class="leg-hero-party">Republican</p><div class="leg-card"><h3 class="leg-card-heading">Contact &amp; Info</h3><div class="detail-row"><span class="label">Phone</span><span class="value">785 296-0000</span></div><div class="detail-row"><span class="label">Email</span><span class="value"><a href="/cdn-cgi/l/email-protection#00">[email protected]</a></span></div></div>'
  with patch.object(a,'finish',lambda rows,*args:rows):
   r=a.parse('ks-lower',html.encode(),{'id':'ks-lower-rep_smith_ann_1','url':'https://www.kslegislature.gov/b2025_26/legislators/rep_smith_ann_1/'})[0]
  self.assertEqual((r['phone'],r['ids']),('785-296-0000',{'ks-lower':'rep_smith_ann_1'}))
  self.assertNotIn('photo',r);self.assertNotIn('email',r)

 def test_idaho_statehouse_phone_and_row_portrait(self):
  html='yr=2026<div class="hcode-inner-row"><div><p><img src="/wp-content/uploads/sessioninfo/2026/directory/Adams1.jpg"></p></div><div><p><strong>Ben Adams</strong>(R)<br><a href="mailto:BAdams@senate.idaho.gov">x</a><br><a href="/legislators/membership/?yr=2026&amp;district=12">District 12</a><br>Home (208) 546-0000<br>Statehouse <a href="tel:+12083320000">(208) 332-0000</a> (Session Only)</p></div></div>'
  r=self.parse('id-upper',html)[0]
  self.assertEqual((r['email'],r['phone'],r['photo']),('badams@senate.idaho.gov','208-332-0000','https://legislature.idaho.gov/wp-content/uploads/sessioninfo/2026/directory/Adams1.jpg'))

 def test_connecticut_contact_form_link_is_not_email(self):
  def tr(d,href):return '<tr><td>'+d+'</td><td><a href="'+href+'">Person, Ann</a></td><td>x</td><td>D</td><td>x</td></tr>'
  rows=self.parse('ct-upper','Senate Members<table>'+tr('S01','https://www.senatedems.ct.gov/senator/a/email-contact')+tr('S02','mailto:Ann.Other@cga.ct.gov')+'</table>')
  self.assertEqual([r.get('email') for r in rows],[None,'ann.other@cga.ct.gov'])

 def test_arkansas_senate_party_from_own_member_page_title(self):
  src={'id':'ar-roster','url':a.SOURCES['ar-roster'][1]}
  link='/Legislators/Detail?member=J.+Scott&ddBienniumSession=2025%2F2026F'
  rows=[a.row(src,'AR','upper','Jamie Scott','12',website=link),a.row(src,'AR','upper','Ann Other','13',website=link.replace('J.+Scott','Other'))]
  pages={'J. Scott':'Jamie Scott (D)','Other':'Someone Else (R)'}
  def fetch(key,publisher,url,offline):
   title='Senator '+pages[a.query(url,'member')]+' - Arkansas State Legislature'
   return ('<title>'+title+'</title>95th General Assembly - Fiscal Session, 2026').encode(),{'id':key,'url':url}
  evidence=a.arkansas_senate_party(fetch,True,rows)
  self.assertEqual(rows[0]['party'],'Democratic')
  self.assertEqual(rows[0]['fieldEvidence']['party'],{'value':'Democratic','sourceIds':['ar-member-j-scott']})
  self.assertEqual([s['id'] for s in rows[0]['sources']],['ar-roster','ar-member-j-scott'])
  self.assertNotIn('party',rows[1])
  self.assertEqual(len(evidence),2)

if __name__=='__main__':unittest.main()
