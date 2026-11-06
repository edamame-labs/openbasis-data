from copy import deepcopy
import gzip
import json
import unittest
from temporal import media_federal as m


def race(body='us-house',state='AL'):
 return dict(test=False,id='source-race',office='H' if body=='us-house' else 'S',officeName='U.S. House',resultsType='live',type='General',level='state',state=state,seatNumber='1',seat='District 1' if body=='us-house' else 'Class I',called=True,raceCallStatus='Called',candidates=[dict(id='ap-choice',first='Source',last='Candidate',party='GOP',votes=10,winner='X',winnerDateTime='2026-11-04T04:00:00Z'),dict(id='larger-vote',first='Vote',last='Leader',votes=999,party='Dem')])


def source(body='us-house'):
 key='media-federal-npr-'+('house' if body=='us-house' else 'senate')+'-data'
 return dict(id=key,url=m.SOURCES[key][1],sha256='a'*64,retrievedAt='2026-11-05T05:25:51Z')


def parse(rows,body='us-house'):
 return m.parse_feed(json.dumps(dict(results=rows)).encode(),source(body),body,['media-federal-npr-index','media-federal-npr-script'])


class MediaFederalTests(unittest.TestCase):
 def test_explicit_call_not_vote_rank_and_exact_proof(self):
  ds,rs,cs=parse([race()]);self.assertEqual(len(ds),1);d=ds[0]
  self.assertEqual(d['name'],'Source Candidate');self.assertEqual(d['sourceCandidateId'],'ap-choice')
  self.assertEqual(d['mediaCalledAt'],'2026-11-04T04:00:00Z');self.assertEqual(d['observedAt'],source()['retrievedAt'])
  self.assertEqual(d['designationStatus'],'media-called-winner');self.assertEqual(d['certificationStatus'],'not-established')
  self.assertEqual(d['callingOrganization'],'The Associated Press')
  self.assertEqual(d['sourceProof']['jsonPointer'],'/results/0/candidates/0/winner')
  self.assertEqual(d['sourceProof']['value'],'X');self.assertNotIn('personId',d)
 def test_uncalled_leader_and_runoff_do_not_generate_call(self):
  r=race();r.pop('called');r['raceCallStatus']='Too Early to Call';r['reportingPercent']=1
  r['candidates'][0]['winner']='R'
  ds,rs,cs=parse([r]);self.assertEqual(ds,[]);self.assertEqual(rs['AL'],1);self.assertEqual(cs['AL'],0)
 def test_test_results_future_naive_time_and_inconsistent_calls_rejected(self):
  for mutation in [lambda r:r.update(test=True),lambda r:r.update(called=False),lambda r:r.update(resultsType='test'),lambda r:r['candidates'][0].update(winnerDateTime='2026-11-06T00:00:00Z'),lambda r:r['candidates'][0].update(winnerDateTime='2026-11-04T04:00:00')]:
   r=race();mutation(r)
   with self.assertRaises(AssertionError):parse([r])
 def test_atlarge_alias_and_special_senate_source_seat_preserved(self):
  ds,_,_=parse([race(state='VT')]);self.assertEqual(ds[0]['district'],'0');self.assertEqual(ds[0]['sourceSeatNumber'],'1')
  r=race('us-senate','FL');r.update(type='Special General',seat='Class III Unexpired Term',seatNumber='3')
  other=deepcopy(r);other.update(id='other-source-seat',seat='Class I',seatNumber='1')
  ds,_,_=parse([r,other],'us-senate');self.assertEqual(len(ds),2)
  self.assertEqual(ds[0]['sourceElectionType'],'Special General');self.assertEqual(ds[0]['sourceSeatLabel'],'Class III Unexpired Term')
  self.assertIsNone(ds[0]['district']);self.assertNotEqual(ds[0]['sourceContestId'],ds[1]['sourceContestId'])
 def test_aggregate_other_duplicate_race_and_candidate_rejected(self):
  r=race();r['candidates'][0]['id']='other-source'
  with self.assertRaises(AssertionError):parse([r])
  with self.assertRaises(AssertionError):parse([race(),race()])
  r=race();r['candidates'][1]['id']=r['candidates'][0]['id']
  with self.assertRaises(AssertionError):parse([r])
 def test_application_context_requires_actual_links_and_explicit_semantics(self):
  index=b'2026 Election Results <script src="app.js">'
  script=b'Election results are tabulated by The Associated Press. d.winner === "X" el.classList.add("winner") winnerDateTime Winner called: ./data/house.json ./data/senate.json'
  m.validate_context(gzip.compress(index),gzip.compress(script))
  for bad in [script.replace(b'The Associated Press',b'Unknown'),script.replace(b'./data/senate.json',b'unknown'),script.replace(b'd.winner === "X"',b'voteLeader')]:
   with self.assertRaises(AssertionError):m.validate_context(index,bad)
 def test_every_race_status_includes_uncalled_and_preserves_unknown_call_time(self):
  a=race();b=race();b['id']='uncalled-source';b.pop('called');b['raceCallStatus']='Too Early to Call';b['candidates'][0].pop('winner');b['candidates'][0].pop('winnerDateTime')
  statuses=[];m.parse_feed(json.dumps(dict(results=[a,b])).encode(),source(),'us-house',[],statuses)
  self.assertEqual(len(statuses),2);self.assertEqual(statuses[0]['winner']['sourceCandidateId'],'ap-choice')
  self.assertFalse(statuses[1]['called']);self.assertIsNone(statuses[1]['winner']);self.assertIsNone(statuses[1]['mediaCalledAt'])
  self.assertFalse(statuses[1]['sourceProof']['calledFieldPresent'])
 def test_missing_media_sources_do_not_create_calls(self):
  def fetch(*args):raise FileNotFoundError('No actual observation')
  p=m.collect(fetch,True);self.assertEqual(p['designations'],[]);self.assertEqual(len(p['stateAudits']),50)
  self.assertTrue(all(a['status']=='access-blocked' for a in p['stateAudits']))

if __name__=='__main__':unittest.main()
