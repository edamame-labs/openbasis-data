import unittest
from temporal import media_california as m

KEY='media-california-ap-senate-ax'
def source():return dict(id=KEY,name='The Associated Press',url=m.SOURCES[KEY][1],finalUrl=m.SOURCES[KEY][1],representation='browser-accessibility-tree',sha256='a'*64,retrievedAt='2026-11-05T05:31:26Z')
def fixture():
 # One accessibility text node spans several cards, as in the actual renderer.
 cards=[]
 for district in range(2,41,2):
  narrative='WINNER A. Named  wins. AP race call at 10:16 p.m. on Nov. 3, 2026 .' if district==2 else 'HIGH VOTE LEADER leads by 99 percentage points with an estimated 100% of votes counted.'
  cards.append('DISTRICT '+str(district)+' '+narrative)
 return ('0 AXWebArea '+m.SOURCES[KEY][1].split('://')[1]+'\n\t1 heading California State Senate\n\t2 text Updated Nov 4, 2026 at 5:54 PM '+' '.join(cards)+'\n\t3 image Winner').encode()


class CaliforniaMediaTests(unittest.TestCase):
 def test_full_chamber_text_node_and_explicit_call_only(self):
  ds,rs=m.parse_snapshot(fixture(),source())
  self.assertEqual(len(rs),20);self.assertEqual(len(ds),1)
  self.assertEqual(sum(r['called'] for r in rs),1)
  d=ds[0];self.assertEqual(d['name'],'A. Named');self.assertEqual(d['district'],'2')
  self.assertEqual(d['publisherCallTimeRaw'],'10:16 p.m. on Nov. 3, 2026')
  self.assertIsNone(d['mediaCalledAt']);self.assertIsNone(d['sourceCandidateId']);self.assertIsNone(d['partyLabel'])
  self.assertEqual(d['certificationStatus'],'not-established');self.assertEqual(d['observedAt'],source()['retrievedAt'])
 def test_call_requires_all_three_markers(self):
  for old,new in [(b'WINNER A. Named',b'A. Named'),(b' wins.',b' leads.'),(b'AP race call at',b'Reported at')]:
   with self.assertRaises(AssertionError):m.parse_snapshot(fixture().replace(old,new),source())
 def test_missing_duplicate_cards_or_wrong_context_fail_closed(self):
  for raw in [fixture().replace(b'DISTRICT 40 ',b'DISTRICT 38 '),fixture().replace(b'Nov 4, 2026',b'Nov 4, 2024'),fixture().replace(b'California State Senate',b'California State Assembly')]:
   with self.assertRaises(AssertionError):m.parse_snapshot(raw,source())
 def test_http_or_dom_label_cannot_substitute_for_ax_evidence(self):
  for rep in ['http-response-body','browser-dom']:
   s=source();s['representation']=rep
   with self.assertRaises(AssertionError):m.parse_snapshot(fixture(),s)
 def test_source_url_and_accessibility_document_url_bound(self):
  s=source();s['url']=s['url'].replace('38146','38134')
  with self.assertRaises(AssertionError):m.parse_snapshot(fixture(),s)
  with self.assertRaises(AssertionError):m.parse_snapshot(fixture().replace(b'38146.html',b'38134.html'),source())
 def test_playwright_projection_and_explicit_uncontested_win(self):
  key='media-california-ap-assembly-cards-ax';s=source();s.update(id=key,url=m.SOURCES[key][1],acquisition=dict(engine='Playwright.domSnapshot'))
  lines=['- heading "California State Assembly" [level=2]','- generic: Updated Nov 4, 2026 at 6:00 PM']
  for district in range(1,81):
   lines.append('- generic: District '+str(district))
   lines.extend(['- img "Winner"','- generic: UNCONTESTED','- text: Named Candidate wins, running unopposed.'] if district==4 else ['- generic: Leader leads by 1 percentage points with an estimated 90% of votes counted.'])
  raw='\n'.join(lines).encode();ds,rs=m.parse_snapshot(raw,s)
  self.assertEqual(len(rs),80);self.assertEqual(len(ds),1)
  self.assertEqual(ds[0]['sourceProof']['publisherOutcomeType'],'explicit-publisher-uncontested-win')
  self.assertIsNone(ds[0]['publisherCallTimeRaw']);self.assertIsNone(ds[0]['mediaCalledAt'])
  # A candidate list labeled uncontested without the explicit wins statement is insufficient.
  with self.assertRaises(AssertionError):m.parse_snapshot(raw.replace(b'wins, running unopposed.',b'running unopposed.'),s)
  s['acquisition']={}
  with self.assertRaises(AssertionError):m.parse_snapshot(raw,s)
 def test_collect_failures_explicit_and_original_timestamp_preserved(self):
  def fetch(key,publisher,url,offline):
   self.assertTrue(offline)
   if key!=KEY:raise FileNotFoundError()
   return fixture(),source()
  p=m.collect(fetch,True);self.assertEqual(len(p['raceStatuses']),20)
  self.assertEqual(p['sourceObservations'][0]['retrievedAt'],source()['retrievedAt'])
  self.assertIn('media-california-ap-assembly-cards-ax',p['stateAudits'][0]['acquisitionFailures'])

if __name__=='__main__':unittest.main()
