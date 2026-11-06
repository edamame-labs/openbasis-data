"""National media integration using trimmed actual NH/VT publisher records."""
import csv
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from temporal.media_ap import BASE,parse_state
from temporal.media_results import combine,write
from temporal import media_ap_northeast,media_ap_midwest,media_ap_south,media_ap_west
from temporal.media_federal import STATES
from temporal.media_common import observation


def actual_case(state):
 # These minimal fixtures preserve the actual AP race/candidate identifiers,
 # seat labels, winner markers and call times observed on November5.
 if state=='NH':
  code='20261103NH31479';seat='Carroll District 1';num=3;raw_num='510';census='101';status='Called'
  people=[('176381','Benjamin',None,'Colbath','Dem',2680,'2026-11-04T01:31:37.242Z'),('141038','David',None,'Paige','Dem',2579,'2026-11-04T01:33:51.371Z'),('140071','Ellin','M.','Leonard','Dem',2339,'2026-11-04T17:27:47.397Z'),('135947','Karen','C.','Umberger','GOP',1732,None)]
 else:
  code='20261103VT46216';seat='Caledonia-3';num=2;raw_num='515';census='CA3';status='Too Early to Call'
  people=[('165184','Beth','M.','Quimby','GOP',1875,'2026-11-04T05:45:45.605Z'),('148909','Dennis','R.','LaBounty','Dem',1607,None),('175124','Erik','R.','Lavallee','GOP',1510,None)]
 candidates={};choices=[]
 for key,first,middle,last,party,votes,call in people:
  candidates[key]=dict(candidateID=key,first=first,last=last,party=party)
  if middle:candidates[key]['middle']=middle
  choice=dict(candidateID=key,voteCount=votes)
  if call:choice.update(winner='X',calledAt=call)
  choices.append(choice)
 m={code:dict(raceID=code,officeID='Y',officeName='State House',raceType='General',electionDate='2026-11-03',statePostal=state,seatName=seat,seatNum=raw_num,censusDistrict=census,numWinners=num,raceCallStatus=status,isCertified=False,candidates=candidates)}
 p={code:dict(raceID=code,statePostal=state,level='state',test=False,resultsType='live',candidates=choices)}
 now=datetime.now(timezone.utc).isoformat()
 def src(kind,raw):
  s=dict(id='media-fixture-'+state.lower()+'-'+kind,name='The Associated Press',url=BASE+f'data-live/2026-11-03/results/races/{state}/{kind}.json',sha256=hashlib.sha256(raw).hexdigest(),retrievedAt=now,representation='http-response-body')
  return dict(s,observationId=observation(s))
 mr=json.dumps(m).encode();pr=json.dumps(p).encode();ms=src('metadata',mr);ps=src('progress',pr)
 ds,rs=parse_state(mr,ms,pr,ps)
 return dict(designations=ds,raceStatuses=rs,stateAudits=[],sourceObservations=[ms,ps]),(m,p)


class NationalMediaIntegrationTests(unittest.TestCase):
 def test_nh_actual_three_winner_slate_has_no_single_winner(self):
  packet,_=actual_case('NH');result=combine([packet],require_npr_snapshot=False);r=result['races'][0]
  self.assertEqual(r['district'],'Carroll District 1');self.assertEqual(r['sourceSeatNumber'],'510')
  self.assertEqual(r['publisherCensusDistrict'],'101');self.assertEqual(r['publisherNumWinners'],3)
  self.assertTrue(r['fullyCalled']);self.assertIsNone(r['winner'])
  self.assertEqual({w['sourceCandidateId'] for w in r['winners']},{'176381','141038','140071'})
  self.assertEqual(result['coverage']['mediaWinnerDesignations'],3)
  with tempfile.TemporaryDirectory() as td:
   write(result,td)
   with (Path(td)/'results.csv').open() as handle:rows=list(csv.DictReader(handle))
  self.assertEqual(len(rows),3);self.assertEqual({r['sourceCandidateId'] for r in rows},{'176381','141038','140071'})
  self.assertEqual({r['sourceContestId'] for r in rows},{'20261103NH31479'})
  self.assertTrue(all(r['mediaCalledAt'] for r in rows))
 def test_vt_actual_partial_slate_retains_one_call_without_declaring_whole_race(self):
  packet,_=actual_case('VT');result=combine([packet],require_npr_snapshot=False);r=result['races'][0]
  self.assertTrue(r['called']);self.assertFalse(r['fullyCalled']);self.assertEqual(r['publisherRaceCallStatus'],'Too Early to Call')
  self.assertEqual(r['publisherNumWinners'],2);self.assertEqual(len(r['winners']),1)
  self.assertEqual(r['winners'][0]['sourceCandidateId'],'165184');self.assertEqual(r['district'],'Caledonia-3')
  self.assertEqual(r['sourceSeatNumber'],'515');self.assertEqual(r['winner']['name'],'Beth M. Quimby')
  self.assertEqual(result['coverage']['mediaWinnerDesignations'],1)
 def test_unmarked_vote_leader_never_enters_slate_and_evidence_proofs_resolve(self):
  packet,(metadata,progress)=actual_case('VT')
  row=next(iter(progress.values()));row['candidates'][1]['voteCount']=999999
  raw=json.dumps(progress).encode();ms,ps=packet['sourceObservations'];ps=dict(ps,sha256=hashlib.sha256(raw).hexdigest());ps['observationId']=observation(ps)
  ds,rs=parse_state(json.dumps(metadata).encode(),ms,raw,ps)
  packet.update(designations=ds,raceStatuses=rs,sourceObservations=[ms,ps])
  # This deliberately perturbs only votes: the same source marker still wins.
  # No maximum-vote candidate is promoted by the assembler.
  result=combine([packet],require_npr_snapshot=False);r=result['races'][0]
  self.assertEqual([w['sourceCandidateId'] for w in r['winners']],['165184'])
  sources={s['observationId']:s for s in result['sourceObservations']}
  self.assertIn(r['observationId'],sources)
  proof=r['winners'][0]['sourceProof']
  self.assertIn(proof['metadataObservationId'],sources);self.assertIn(proof['progressObservationId'],sources)
  self.assertEqual(r['sourceUrl'],sources[proof['progressObservationId']]['url'])
  self.assertEqual(r['sourceSha256'],sources[proof['progressObservationId']]['sha256'])
  self.assertEqual(r['certificationStatus'],'not-established')
 def test_national_region_catalog_partitions_exactly50states_and100_data_urls(self):
  modules=[media_ap_northeast,media_ap_midwest,media_ap_south,media_ap_west]
  states=[s for module in modules for s in module.STATES]
  self.assertEqual(len(states),50);self.assertEqual(len(set(states)),50);self.assertEqual(set(states),STATES)
  urls=[url for module in modules for _,url in module.SOURCES.values() if '/data-live/2026-11-03/results/races/' in url]
  self.assertEqual(len(urls),100);self.assertEqual(len(set(urls)),100)
  for state in STATES:
   self.assertIn(BASE+f'data-live/2026-11-03/results/races/{state}/metadata.json',urls)
   self.assertIn(BASE+f'data-live/2026-11-03/results/races/{state}/progress.json',urls)

if __name__=='__main__':unittest.main()
