import json
import unittest
from temporal import media_south as m


def source(key):return dict(id=key,url=m.SOURCES[key][1],sha256='a'*64,retrievedAt='2026-11-05T06:28:00Z')
def texas():
 rows=[]
 for office,count in [('Texas House',150),('Texas Senate',16)]:
  for district in range(1,count+1):
   rows.append(dict(id=office+str(district),election_date='2026-11-03',election_type='general',office=office,office_slug=office+str(district),
    source='Associated Press',division_type='district',office_division=district,is_called=False,contest_result='not called',
    candidacies=[dict(id='candidate1',name='VOTE LEADER',is_winner=False,votes=999),dict(id='candidate2',name='MARKED WINNER',is_winner=False,votes=1)]))
 rows[0].update(is_called=True,contest_result='winner');rows[0]['candidacies'][1]['is_winner']=True
 special=dict(rows[0],id='special-house1',election_type='special');rows.append(special)
 return rows

def alabama():
 rows=[]
 for office,code,count in [('State House','HD',105),('State Senate','SD',35)]:
  for district in range(1,count+1):
   rows.append(dict(id=office+str(district),name=office+' '+str(district),office=office,district=f'AL-{code}-{district:03}',summary=True,disputed=False,source='sos',
    candidates=[dict(id='source-candidate',name='NAME',winner=True,calledBy='apr',votes=1)]))
 return dict(date='2026-11-03',status='ready',historical=False,races=rows)


class SouthMediaTests(unittest.TestCase):
 def test_texas_marked_low_vote_winner_regular_and_special_separate(self):
  ds,rs=m.parse_texas(json.dumps(texas()).encode(),source('media-south-tt-data'))
  self.assertEqual(len(rs),167);self.assertEqual(len(ds),2)
  self.assertEqual({d['sourceContestId'] for d in ds},{'Texas House1','special-house1'})
  self.assertTrue(all(d['name']=='MARKED WINNER' and d['callingOrganization']=='The Associated Press' for d in ds))
  self.assertTrue(any(r['specialElection'] for r in rs));self.assertTrue(any(not r['called'] for r in rs))
 def test_texas_inconsistent_boolean_flags_or_wrong_year_reject(self):
  for mutation in ['date','string','missing']:
   rows=texas()
   if mutation=='date':rows[0]['election_date']='2024-11-05'
   if mutation=='string':rows[0]['candidacies'][1]['is_winner']='true'
   if mutation=='missing':rows.pop(5)
   with self.assertRaises(AssertionError):m.parse_texas(json.dumps(rows).encode(),source('media-south-tt-data'))
 def test_texas_uncontested_requires_explicit_called_and_winner(self):
  rows=texas();rows[1].update(is_called=True,contest_result='uncontested');rows[1]['candidacies']=[dict(id='one',name='SOLE',is_winner=True)]
  ds,_=m.parse_texas(json.dumps(rows).encode(),source('media-south-tt-data'))
  self.assertEqual(next(d for d in ds if d['name']=='SOLE')['sourceProof']['publisherOutcomeType'],'explicit-publisher-uncontested-win')
  rows[1]['candidacies'][0]['is_winner']=False
  with self.assertRaises(AssertionError):m.parse_texas(json.dumps(rows).encode(),source('media-south-tt-data'))
 def test_alabama_media_call_attribution_is_apr_not_government_or_ap(self):
  ds,rs=m.parse_alabama(json.dumps(alabama()).encode(),source('media-south-al-data'))
  self.assertEqual(len(ds),140);self.assertEqual(len(rs),140)
  self.assertTrue(all(d['callingOrganization']=='Alabama Political Reporter' and d['certificationStatus']=='not-established' for d in ds))
  self.assertEqual(ds[0]['sourceProof']['corroboratingFields'],dict(calledBy='apr'))
 def test_alabama_test_historical_disputed_and_nonapr_markers_fail_closed(self):
  for mutation in ['test','historical','disputed','official','string']:
   data=alabama()
   if mutation=='test':data['testDataShown']=True
   if mutation=='historical':data['historical']=True
   if mutation=='disputed':data['races'][0]['disputed']=True
   if mutation=='official':data['races'][0]['candidates'][0]['calledBy']='official'
   if mutation=='string':data['races'][0]['candidates'][0]['winner']='true'
   if mutation=='string':
    ds,_=m.parse_alabama(json.dumps(data).encode(),source('media-south-al-data'));self.assertEqual(len(ds),139)
   else:
    with self.assertRaises(AssertionError):m.parse_alabama(json.dumps(data).encode(),source('media-south-al-data'))
 def test_north_carolina_only_explicit_defeated_assertions(self):
  paragraphs=''.join('<p>'+fragment+'</p>' for *_,fragment in m.NC_ASSERTIONS)
  raw=('<html><title>Election 2026: Preliminary results for Cape Fear region races</title><article>November 3, 2026'+paragraphs+'<p>House20 Candidate leads by99% with100%counted</p></article></html>').encode()
  ds,rs=m.parse_whqr(raw,source('media-south-nc-whqr'))
  self.assertEqual(len(ds),5);self.assertEqual(len(rs),5)
  self.assertNotIn('20',{d['district'] for d in ds})
  with self.assertRaises(AssertionError):m.parse_whqr(raw.replace(b'Bichler defeated',b'Bichler leads'),source('media-south-nc-whqr'))
 def test_missing_sources_remain_explicit(self):
  def fetch(*args):raise FileNotFoundError()
  p=m.collect(fetch,True);self.assertEqual(p['designations'],[]);self.assertEqual(len(p['stateAudits']),9)
  self.assertTrue(p['stateAudits'][0]['acquisitionFailures'])

if __name__=='__main__':unittest.main()
