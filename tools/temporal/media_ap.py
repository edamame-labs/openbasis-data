"""Shared parser for explicitly called AP state legislative candidates."""
from datetime import datetime
import gzip
import json
import re
from .media_common import observation,digest

BASE='https://interactives.apelections.org/election-results/'
SOURCES={
 'media-northeast-ap-layout-client':('The Associated Press',BASE+'assets/microsite/layoutClient.js'),
 'media-northeast-ap-remote-entry':('The Associated Press',BASE+'assets/cycle-2026/remoteEntry.js'),
 'media-northeast-ap-visualization-manifest':('The Associated Press',BASE+'assets/cycle-2026/__cdn__/js/1809.a93380216042dc96c9e2.js'),
 'media-northeast-ap-result-card-script':('The Associated Press',BASE+'assets/cycle-2026/__cdn__/js/2834.a7ebc2b48766f5b6b1a7.js'),
 'media-northeast-pa-layout':('The Associated Press',BASE+'customers/layouts/organization-layouts/published/124213/37083.html'),
}


def decoded(raw):
 return (gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw).decode('utf-8-sig')


def instant(value):
 parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
 assert parsed.tzinfo is not None,'Timestamp requires timezone'
 return parsed


def collect_context(fetch,offline=False):
 sources=[];raws={}
 for key,(publisher,url) in SOURCES.items():
  raw,s=fetch(key,publisher,url,offline);raws[key]=decoded(raw);sources.append(dict(s,observationId=observation(s)))
 layout=raws['media-northeast-pa-layout'];client=raws['media-northeast-ap-layout-client'];remote=raws['media-northeast-ap-remote-entry'];manifest=raws['media-northeast-ap-visualization-manifest'];cards=raws['media-northeast-ap-result-card-script']
 assert '2026-11-03' in layout and 'layoutClient.js' in layout,'Missing live election layout context'
 assert BASE+'data-live' in client and 'cycle-${o}' in client,'Unverified AP live-data prefix/cycle'
 assert '1809' in remote and 'a93380216042dc96c9e2' in remote and '2834' in remote and 'a7ebc2b48766f5b6b1a7' in remote,'Changed visualization chunks require review'
 assert 'ResultsCardGrid' in manifest and 'a.e(2834)' in manifest,'Unverified AP result-card component'
 assert '${e}/results/races/${n}/progress.json' in cards and '${e}/results/races/${n}/metadata.json' in cards,'Unverified state data path construction'
 assert '"X"===e.winner' in cards and 'wins. AP race call at ' in cards and 'calledAt' in cards,'Unverified AP candidate winner/call-time semantics'
 return sources


def parse_state(metadata_raw,metadata_source,progress_raw,progress_source,context_source_ids=None):
 metadata=json.loads(decoded(metadata_raw));progress=json.loads(decoded(progress_raw))
 assert isinstance(metadata,dict) and isinstance(progress,dict),'Expected AP state race dictionaries'
 match=re.fullmatch(re.escape(BASE)+r'data-live/2026-11-03/results/races/([A-Z]{2})/metadata.json',metadata_source['url'])
 assert match,'Wrong metadata source/date';state=match[1]
 assert progress_source['url']==metadata_source['url'].removesuffix('metadata.json')+'progress.json','Metadata/progress source mismatch'
 source_ids=[progress_source['id'],metadata_source['id']]+list(context_source_ids or [])
 obs=observation(progress_source);out=[];statuses=[];seen=set()
 for code,m in metadata.items():
  if m['officeID'] not in {'Y','Z'}:continue
  assert m['officeName'] in {'State House','State Senate','State Legislature','House of Delegates','State Assembly'},'Unknown AP legislative office'
  assert code==m['raceID'] and code.startswith('20261103'+state),'Wrong source race ID/date/state'
  assert m['electionDate']=='2026-11-03' and m['statePostal']==state,'Wrong election date/state'
  if 'Primary' in m['raceType']:continue  # Same-day primaries are a distinct election, never general outcomes.
  assert m['raceType'] in {'General','Special General','Nonpartisan Election','Special Nonpartisan','Nonpartisan Special Election'},'Unknown general-date legislative race type'
  assert code in progress,'Missing publisher race observation'
  p=progress[code]
  assert p['raceID']==code and p['statePostal']==state and p['level']=='state','Wrong component reporting scope'
  assert p['test'] is False and p['resultsType']=='live','Test or non-live data'
  body='state-upper' if m['officeID']=='Z' else 'state-lower'
  assert code not in seen;seen.add(code)
  # Numeric seatNum is an AP display/sort code in named-district states.
  # Preserve seatName for those states, never turn sort codes into districts.
  seat=m.get('seatName');assert isinstance(seat,str) and seat,'Missing exact publisher seat label'
  numbered=re.fullmatch(r'District (\d+[A-Za-z]?)(?: - Position (\d+))?',seat)
  district=numbered[1] if numbered else seat
  entries=p['candidates'];assert isinstance(entries,list)
  assert len({str(c['candidateID']) for c in entries})==len(entries),'Duplicate AP candidate choice'
  winners=[(i,c) for i,c in enumerate(entries) if c.get('winner')=='X']
  direct_num=m.get('numWinners')
  if direct_num is not None:
   assert type(direct_num) is int and direct_num>0 and len(winners)<=direct_num,'Invalid winner count against publisher numWinners'
  context=dict(state=state,body=body,district=district,sourceContestId=code,sourceRaceId=code,
    sourceRaceLabel=m['officeName']+' '+seat,sourceSeatLabel=seat,sourceSeatNumber=m.get('seatNum'),sourceOfficeID=m['officeID'],
    sourcePosition=m.get('position',m.get('positionNum')) if m.get('position',m.get('positionNum')) is not None else numbered[2] if numbered and numbered[2] else None,
    sourceElectionType=m['raceType'],publisherNumWinners=direct_num,publisherCensusDistrict=m.get('censusDistrict'),
    metadataObservationId=observation(metadata_source),progressObservationId=obs,
    sourceIds=source_ids,observationId=obs,observedAt=progress_source['retrievedAt'],callingOrganization='The Associated Press',publisher='The Associated Press')
  statuses.append(dict(context,id='media-race:'+digest([obs,code]),called=bool(winners),
    status='called' if winners else 'uncalled',fullyCalled=m.get('raceCallStatus')=='Called',publisherRaceCallStatus=m.get('raceCallStatus'),
    calledCandidateCount=len(winners),publisherUncontested=m.get('uncontested'),
    sourceProof=dict(jsonPointer='/'+code,field='candidates[].winner',value='X' if winners else None,metadataJsonPointer='/'+code,metadataObservationId=observation(metadata_source),progressObservationId=obs,
       winnerSemanticsSourceId='media-northeast-ap-result-card-script'),
    missingRowsEstablishNotOnBallot=False))
  for index,c in winners:
   candidate_id=str(c['candidateID']);assert candidate_id in m['candidates'],'Called candidate missing in same-source metadata'
   ca=m['candidates'][candidate_id];assert str(ca['candidateID'])==candidate_id,'Candidate source identifier mismatch'
   assert ca.get('last') and ca['last'].casefold() not in {'other','total write-ins','write-ins','write-in'},'Aggregate is not a named called winner'
   name=' '.join(str(ca[k]).strip() for k in ['first','middle','last','suffix'] if ca.get(k));assert name
   call=c.get('calledAt')
   if call:assert instant(call)<=instant(progress_source['retrievedAt']),'Call time after actual observation'
   proof=dict(jsonPointer=f'/{code}/candidates/{index}/winner',field='winner',value='X',
      candidateMetadataJsonPointer=f'/{code}/candidates/{candidate_id}',metadataObservationId=observation(metadata_source),progressObservationId=obs,callTimeJsonPointer=f'/{code}/candidates/{index}/calledAt' if call else None,
      publisherOutcomeType='explicit-publisher-uncontested-win' if m.get('uncontested') is True else 'explicit-AP-race-call',
      semanticsSourceId='media-northeast-ap-result-card-script')
   out.append(dict(context,id='media-designation:'+digest([obs,code,candidate_id]),name=name,partyLabel=ca.get('party'),
      sourceCandidateId=candidate_id,sourceNameComponents={k:ca[k] for k in ['first','middle','last','suffix'] if k in ca},
      designationStatus='media-called-winner',certificationStatus='not-established',publisherCertificationFlag=m.get('isCertified'),
      mediaCalledAt=call,mediaCallTimeStatus='publisher-provided-timezone-qualified' if call else 'not-provided',
      sourceProof=proof,personId=None,identityStatus='AP source race/candidate IDs only; no government person or serving membership join',
      scopeLimitations='Individual explicit AP candidate call; multiwinner race may remain partly uncalled. No vote-rank or uncontested-list inference.'))
 return out,statuses
