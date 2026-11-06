from copy import deepcopy
from datetime import datetime,timezone,timedelta
import csv
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from temporal.media_results import combine,write
from temporal.media_common import observation


def fixture():
 s=dict(id='media-test-data',name='Publisher',url='https://apps.npr.org/observed.json',sha256='a'*64,retrievedAt=datetime.now(timezone.utc).isoformat(),representation='http-response-body')
 s['observationId']=observation(s)
 d=dict(state='AA',body='governor',district=None,sourceContestId='race1',sourceCandidateId='choice1',name='Source Name',partyLabel='PublisherParty',designationStatus='media-called-winner',callingOrganization='AP',carryingOrganization='NPR',sourceIds=[s['id']],observationId=s['observationId'],observedAt=s['retrievedAt'],callTime='2026-11-04T00:00:00Z',sourceProof={'field':'winner','value':'X'})
 status=dict(state='AA',body='governor',sourceContestId='race1',called=True,sourceIds=[s['id']],observationIds=[s['observationId']],sourceProof={'field':'raceCallStatus','value':'Called'})
 return dict(designations=[d],raceStatuses=[status],sourceObservations=[s],stateAudits=[])


class MediaResultsTests(unittest.TestCase):
 def test_compressed_publication_preserves_result_and_manifest(self):
  result=combine([fixture()],require_npr_snapshot=False)
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);manifest=write(result,root,compressed=True)
   self.assertEqual(json.loads(gzip.decompress((root/'results.json.gz').read_bytes())),result)
   self.assertFalse((root/'results.json').exists())
   self.assertEqual({f['path'] for f in manifest['files']},{'results.json.gz','results.csv'})
   for f in manifest['files']:self.assertEqual(hashlib.sha256((root/f['path']).read_bytes()).hexdigest(),f['sha256'])
 def test_governor_winner_joins_exact_source_race_and_normalizes_calltime(self):
  p=combine([fixture()],require_npr_snapshot=False);r=p['races'][0]
  self.assertEqual(r['winner']['name'],'Source Name');self.assertEqual(r['mediaCalledAt'],'2026-11-04T00:00:00Z')
  self.assertEqual(r['publisher'],'NPR');self.assertEqual(r['sourceUrl'],'https://apps.npr.org/observed.json')
  self.assertEqual(r['sourceReferences'][0]['sha256'],'a'*64)
  self.assertEqual(r['certificationStatus'],'not-established')
 def test_uncalled_has_no_winner_and_matching_names_do_not_join_other_source_race(self):
  p=fixture();p['designations']=[];p['raceStatuses'][0].update(called=False)
  result=combine([p],require_npr_snapshot=False)
  self.assertIsNone(result['races'][0]['winner']);self.assertIsNone(result['races'][0]['mediaCalledAt'])
  p=fixture();p['designations'][0]['sourceContestId']='other-race'
  with self.assertRaisesRegex(ValueError,'call/designation mismatch'):combine([p],require_npr_snapshot=False)
 def test_standalone_texas_assertions_remain_separate_even_without_district(self):
  p=fixture();p['raceStatuses']=[];p['designations'][0].update(state='TX',body='state-lower',sourceContestId=None,sourceCandidateId=None,district=None)
  second=deepcopy(p['designations'][0]);second.update(name='Different Named Subject',sourceProof={'field':'article assertion','value':'Different name won'})
  p['designations'].append(second);r=combine([p],require_npr_snapshot=False)
  self.assertEqual(len(r['additionalDesignations']),2);self.assertEqual(r['races'],[])
  self.assertTrue(all(d['district'] is None and 'unresolved' in d['linkageStatus'] for d in r['additionalDesignations']))
 def test_acquisition_parser_errors_missing_evidence_and_future_calls_fail(self):
  for kind in ['errors','missing','future','observation-mismatch']:
   p=fixture()
   if kind=='errors':p['coverage']={'parserFailures':{'source':'invalid actual data'}}
   elif kind=='missing':p['sourceObservations']=[]
   elif kind=='future':p['designations'][0]['callTime']=(datetime.fromisoformat(p['sourceObservations'][0]['retrievedAt'])+timedelta(days=1)).isoformat()
   else:p['designations'][0]['observedAt']=(datetime.fromisoformat(p['sourceObservations'][0]['retrievedAt'])+timedelta(minutes=1)).isoformat()
   with self.assertRaises(ValueError):combine([p],require_npr_snapshot=False)
 def test_content_identity_changes_when_parser_output_changes_same_evidence(self):
  a=fixture();b=deepcopy(a);b['designations'][0]['name']='Corrected parser label'
  first=combine([a],require_npr_snapshot=False);second=combine([b],require_npr_snapshot=False)
  self.assertEqual(first['sourceObservations'],second['sourceObservations'])
  self.assertNotEqual(first['datasetId'],second['datasetId'])
 def test_publication_rejects_stale_evidence_and_tampered_content_before_writes(self):
  for stale in [True,False]:
   result=combine([fixture()],require_npr_snapshot=False)
   if stale:result['sourceObservations'][0]['retrievedAt']='2000-01-01T00:00:00Z'
   else:result['races'][0]['winner']['name']='Tampered label'
   with tempfile.TemporaryDirectory() as td:
    destination=Path(td)/'unpublished'
    with self.assertRaises(ValueError):write(result,destination)
    self.assertFalse(destination.exists())
 def test_literal_call_time_and_explicit_uncontested_category_remain_distinct(self):
  p=fixture();d=p['designations'][0];d.pop('callTime');d['publisherCallTimeRaw']='Nov. 4, 2026 at 1:30 am; timezone unstated'
  d['sourceProof']['publisherOutcomeType']='explicit-publisher-uncontested-win'
  result=combine([p],require_npr_snapshot=False);r=result['races'][0]
  self.assertIsNone(r['mediaCalledAt']);self.assertEqual(r['publisherCallTimeRaw'],d['publisherCallTimeRaw'])
  self.assertEqual(result['coverage']['explicitUncontestedWins'],1)
 def test_exact_initial_npr_scope_is_required(self):
  with self.assertRaisesRegex(ValueError,'snapshot coverage'):combine([fixture()])
 def test_json_csv_manifest_are_deterministic_and_checksums_verify(self):
  result=combine([fixture()],require_npr_snapshot=False)
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);a=write(result,root);before={p.name:p.read_bytes() for p in root.iterdir()};b=write(result,root)
   self.assertEqual(a,b);self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
   for f in a['files']:self.assertEqual(hashlib.sha256((root/f['path']).read_bytes()).hexdigest(),f['sha256'])
   with (root/'results.csv').open() as handle:rows=list(csv.DictReader(handle))
   self.assertEqual(rows[0]['name'],'Source Name');self.assertEqual(rows[0]['sourceSha256'],'a'*64)

if __name__=='__main__':unittest.main()
