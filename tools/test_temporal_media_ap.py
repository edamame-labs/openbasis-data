from copy import deepcopy
import gzip
import json
import unittest
from temporal.media_ap import parse_state,BASE


def fixture(state='VT',seat='Caledonia-3',num_winners=2):
 code='20261103'+state+'source-race'
 m=dict(raceID=code,officeID='Y',officeName='State House',raceType='General',electionDate='2026-11-03',statePostal=state,
        seatName=seat,seatNum='515',censusDistrict='CA3',numWinners=num_winners,raceCallStatus='Too Early to Call',isCertified=False,
        candidates={'ap1':dict(candidateID='ap1',first='Source',middle='M.',last='Candidate',suffix='II',party='Prg/Dem'),
                    'ap2':dict(candidateID='ap2',first='Higher',last='Votes',party='GOP')})
 p=dict(raceID=code,statePostal=state,level='state',test=False,resultsType='live',candidates=[dict(candidateID='ap1',winner='X',voteCount=1,calledAt='2026-11-04T05:00:00Z'),dict(candidateID='ap2',voteCount=999)])
 ms=dict(id='media-meta',url=BASE+f'data-live/2026-11-03/results/races/{state}/metadata.json',sha256='a'*64,retrievedAt='2026-11-05T06:00:00Z')
 ps=dict(id='media-progress',url=BASE+f'data-live/2026-11-03/results/races/{state}/progress.json',sha256='b'*64,retrievedAt='2026-11-05T06:01:00Z')
 return {code:m},ms,{code:p},ps


def parse(packet):
 m,ms,p,ps=packet
 return parse_state(json.dumps(m).encode(),ms,json.dumps(p).encode(),ps,['media-context'])


class SharedAPTests(unittest.TestCase):
 def test_partial_multiwinner_call_is_individual_not_vote_leader_or_complete_slate(self):
  ds,rs=parse(fixture());self.assertEqual(len(ds),1);self.assertEqual(ds[0]['name'],'Source M. Candidate II')
  self.assertEqual(ds[0]['district'],'Caledonia-3');self.assertEqual(ds[0]['sourceSeatNumber'],'515')
  self.assertEqual(ds[0]['publisherCensusDistrict'],'CA3');self.assertEqual(ds[0]['publisherNumWinners'],2)
  self.assertEqual(ds[0]['sourceCandidateId'],'ap1');self.assertEqual(ds[0]['partyLabel'],'Prg/Dem')
  self.assertTrue(rs[0]['called']);self.assertFalse(rs[0]['fullyCalled']);self.assertEqual(rs[0]['calledCandidateCount'],1)
  self.assertEqual(ds[0]['sourceIds'][:2],['media-progress','media-meta'])
  self.assertEqual(ds[0]['sourceProof']['metadataObservationId'],ds[0]['metadataObservationId'])
 def test_multiple_explicit_winners_preserved_per_contest(self):
  packet=fixture();p=next(iter(packet[2].values()));p['candidates'][1].update(winner='X',calledAt='2026-11-04T05:01:00Z')
  ds,rs=parse(packet);self.assertEqual(len(ds),2);self.assertEqual(rs[0]['calledCandidateCount'],2)
  self.assertEqual(len({d['id'] for d in ds}),2);self.assertEqual(len({d['sourceContestId'] for d in ds}),1)
 def test_uncontested_needs_positive_x_not_candidate_list(self):
  packet=fixture();m=next(iter(packet[0].values()));m['uncontested']=True
  p=next(iter(packet[2].values()));p['candidates'][0].pop('winner')
  ds,rs=parse(packet);self.assertEqual(ds,[]);self.assertFalse(rs[0]['called'])
  p['candidates'][0]['winner']='X';ds,rs=parse(packet)
  self.assertEqual(ds[0]['sourceProof']['publisherOutcomeType'],'explicit-publisher-uncontested-win')
  self.assertEqual(ds[0]['certificationStatus'],'not-established')
 def test_exact_washington_position_and_named_districts(self):
  ds,rs=parse(fixture('WA','District 1 - Position 2'));self.assertEqual(rs[0]['district'],'1');self.assertEqual(rs[0]['sourcePosition'],'2')
  ds,rs=parse(fixture('MA','Cape & Islands'));self.assertEqual(rs[0]['district'],'Cape & Islands')
  ds,rs=parse(fixture('VA','District 20 Unexpired Term'));self.assertEqual(rs[0]['district'],'District 20 Unexpired Term')
 def test_same_day_primary_is_excluded_without_losing_general(self):
  packet=fixture();code=next(iter(packet[0]));primary=deepcopy(packet[0][code]);primary.update(raceID='20261103VTprimary',raceType='Special Primary')
  packet[0][primary['raceID']]=primary
  ds,rs=parse(packet);self.assertEqual(len(ds),1);self.assertEqual(len(rs),1)
 def test_runoff_candidate_and_reporting100percent_do_not_generate_winner(self):
  packet=fixture();p=next(iter(packet[2].values()));p['candidates'][0]['winner']='R';p['eevp']=100
  ds,rs=parse(packet);self.assertEqual(ds,[]);self.assertFalse(rs[0]['called'])
 def test_wrong_date_test_component_future_time_and_unresolved_candidate_rejected(self):
  for name in ['date','test','county','future','candidate']:
   packet=fixture();m=next(iter(packet[0].values()));p=next(iter(packet[2].values()))
   if name=='date':m['electionDate']='2024-11-05'
   elif name=='test':p['test']=True
   elif name=='county':p['level']='county'
   elif name=='future':p['candidates'][0]['calledAt']='2026-11-06T00:00:00Z'
   else:p['candidates'][0]['candidateID']='unresolved'
   with self.assertRaises(AssertionError):parse(packet)
 def test_exact_gzip_raw_inputs_decode_without_changing_source_identity(self):
  packet=fixture();a=parse(packet);m,ms,p,ps=packet
  b=parse_state(gzip.compress(json.dumps(m).encode()),ms,gzip.compress(json.dumps(p).encode()),ps,['media-context'])
  self.assertEqual(a,b)

if __name__=='__main__':unittest.main()
