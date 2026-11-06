import unittest
from unittest.mock import patch
from temporal import media_ap_northeast as m


class APNortheastTests(unittest.TestCase):
 def test_catalog_has_all11_states_and_exact_november_source_pairs(self):
  self.assertEqual(len(m.STATES),11)
  for state in m.STATES:
   for kind in ['metadata','progress']:
    publisher,url=m.SOURCES[f'media-northeast-ap-{state.lower()}-{kind}']
    self.assertEqual(publisher,'The Associated Press')
    self.assertTrue(url.endswith(f'/2026-11-03/results/races/{state}/{kind}.json'))
 def test_access_failure_is_explicit_for_every_assigned_state(self):
  def fetch(*args):raise FileNotFoundError('No evidence')
  p=m.collect(fetch,True)
  self.assertEqual(p['raceStatuses'],[]);self.assertEqual(p['designations'],[])
  self.assertEqual(len(p['stateAudits']),11)
  self.assertTrue(all(a['status']=='access-blocked' and a['acquisitionFailures'] for a in p['stateAudits']))
  self.assertTrue(all(a['missingRowsEstablishNotOnBallot'] is False for a in p['stateAudits']))
 def test_empty_office_set_not_inferred_no_election(self):
  def fetch(key,publisher,url,offline):
   return b'{}',dict(id=key,name=publisher,url=url,sha256='a'*64,retrievedAt='2026-11-05T06:00:00Z')
  with patch('temporal.media_ap.collect_context',return_value=[]),patch('temporal.media_ap.parse_state',return_value=([],[])):
   p=m.collect(fetch,True)
  self.assertEqual(p['designations'],[]);self.assertTrue(all(a['observedLegislativeRaceCount']==0 and a['status']=='checked' for a in p['stateAudits']))
  self.assertTrue(all(a['missingRowsEstablishNotOnBallot'] is False for a in p['stateAudits']))

if __name__=='__main__':unittest.main()
