import unittest
from unittest.mock import patch
from temporal import media_ap_south as m
from temporal.media_common import observation


def source(key,url):return dict(id=key,name='The Associated Press',url=url,sha256='a'*64,retrievedAt='2026-11-05T06:28:41Z')
def context():
 key=next(iter(m.media_ap.SOURCES));s=source(key,m.SOURCES[key][1]);return [dict(s,observationId=observation(s))]
def fetch(key,publisher,url,offline):
 assert offline is True
 return key.encode(),source(key,url)
def parse(metadata_raw,metadata_source,progress_raw,progress_source,context_source_ids):
 state=metadata_source['url'].split('/')[-2]
 assert metadata_raw.decode().endswith('-metadata') and progress_raw.decode().endswith('-progress')
 assert metadata_source['url'].replace('metadata.json','progress.json')==progress_source['url']
 common=dict(state=state,body='state-lower',district='1',sourceContestId='source-race',sourceIds=[progress_source['id'],metadata_source['id']]+context_source_ids,observationId=observation(progress_source),observedAt=progress_source['retrievedAt'])
 return [dict(common,name='PUBLISHER WINNER',designationStatus='media-called-winner')],[dict(common,called=True)]


class APSouthCollectorTests(unittest.TestCase):
 def test_all13_pairs_plus_context_preserve_primary_time(self):
  with patch.object(m.media_ap,'collect_context',return_value=context()),patch.object(m.media_ap,'parse_state',side_effect=parse):p=m.collect(fetch,True)
  self.assertEqual(len(p['raceStatuses']),13);self.assertEqual(len(p['designations']),13)
  self.assertEqual(len(p['sourceObservations']),27)
  self.assertEqual({r['state'] for r in p['raceStatuses']},set(m.STATES))
  self.assertTrue(all(r['observedAt']=='2026-11-05T06:28:41Z' for r in p['raceStatuses']))
 def test_missing_authority_context_fails_closed_for_every_state(self):
  with patch.object(m.media_ap,'collect_context',side_effect=ValueError('Changed winner renderer')),patch.object(m.media_ap,'parse_state') as parser:p=m.collect(fetch,True)
  parser.assert_not_called();self.assertEqual(p['designations'],[])
  self.assertTrue(all('shared-AP-context' in a['validationErrors'] for a in p['stateAudits']))
 def test_one_state_malformed_does_not_relabel_others_as_complete(self):
  def bad(*args,**kwargs):
   if '/GA/' in args[1]['url']:raise AssertionError('Wrong election')
   return parse(*args,**kwargs)
  with patch.object(m.media_ap,'collect_context',return_value=context()),patch.object(m.media_ap,'parse_state',side_effect=bad):p=m.collect(fetch,True)
  self.assertEqual(len(p['raceStatuses']),12)
  audit=next(a for a in p['stateAudits'] if a['state']=='GA')
  self.assertEqual(audit['status'],'not-collected');self.assertIn('GA',audit['validationErrors'])
 def test_missing_progress_preserves_metadata_reference_without_result(self):
  def missing(key,publisher,url,offline):
   if key=='media-ap-south-nc-progress':raise FileNotFoundError('Missing observation')
   return fetch(key,publisher,url,offline)
  with patch.object(m.media_ap,'collect_context',return_value=context()),patch.object(m.media_ap,'parse_state',side_effect=parse):p=m.collect(missing,True)
  audit=next(a for a in p['stateAudits'] if a['state']=='NC')
  self.assertEqual(audit['observedLegislativeRaceCount'],0)
  self.assertIn('media-ap-south-nc-metadata',audit['sourceIds']);self.assertIn('media-ap-south-nc-progress',audit['acquisitionFailures'])
 def test_exact_static_epoch_urls(self):
  keys=[k for k in m.SOURCES if k.startswith('media-ap-south-')]
  self.assertEqual(len(keys),26)
  self.assertTrue(all('/data-live/2026-11-03/results/races/' in m.SOURCES[k][1] for k in keys))

if __name__=='__main__':unittest.main()
