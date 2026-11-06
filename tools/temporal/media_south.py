"""AP legislative race calls carried by southern newsrooms."""
import json
import re
from .media_common import observation,digest,ELECTION_ID
from .media_federal import decode

TTBASE='https://apps.texastribune.org/features/2026/texas-general-election-live-results-2026/'
TTFEED='https://s3.amazonaws.com/sos-test-2.texastribune.org/2026_general/republic_json/results_FLAT.json'
SOURCES={
 'media-south-tt-index':('The Texas Tribune',TTBASE),
 'media-south-tt-script':('The Texas Tribune',TTBASE+'scripts/main.b04f0e5dfd.mjs'),
 'media-south-tt-data':('The Texas Tribune',TTFEED),
 'media-south-al-index':('Alabama Political Reporter','https://www.alreporter.com/?ui=desktop'),
 'media-south-al-script':('Alabama Political Reporter','https://www.alreporter.com/_next/static/chunks/2yt3y_gbjse3r.js'),
 'media-south-al-data':('Alabama Political Reporter','https://www.alreporter.com/api/election-results'),
 'media-south-nc-whqr':('WHQR','https://www.whqr.org/local/2026-11-03/election-2026-preliminary-results-for-cape-fear-region-races'),
}
DELEGATIONS={'media-south-tt-data':dict(authoritySourceId='media-south-tt-script',serviceUrl=TTFEED,javascriptURLLiteral=True)}
STATES='TX NC GA FL VA SC AL TN KY'.split()


def tt_context(index_raw,script_raw):
 index=decode(index_raw);script=decode(script_raw)
 assert 'Texas 2026' in index and 'scripts/main.b04f0e5dfd.mjs' in index,'Wrong application epoch or unlinked script'
 assert TTFEED in script and 'Associated Press' in script and 'AP projection' in script,'Missing media feed/attribution context'
 assert 'is_winner' in script and '"winner"==' in script and 'contest_result' in script,'Missing winner semantics'


def parse_texas(raw,source):
 assert source['url']==TTFEED,'Unexpected Texas feed URL'
 rows=json.loads(decode(raw));assert isinstance(rows,list) and rows
 designations=[];statuses=[];seen=set();general={'state-upper':set(),'state-lower':set()}
 for ri,row in enumerate(rows):
  body={'Texas House':'state-lower','Texas Senate':'state-upper'}.get(row['office'])
  if body is None:continue
  assert row['election_date']=='2026-11-03' and row['election_type'] in {'general','special'},'Wrong legislative election'
  assert row['source']=='Associated Press' and row['division_type']=='district','Wrong source/report scope'
  code=str(row['id']);assert code and code not in seen,'Duplicate publisher contest ID';seen.add(code)
  district=str(row['office_division']);assert district.isdigit(),'Unknown publisher district'
  if row['election_type']=='general':general[body].add(int(district))
  marked=[(ci,c) for ci,c in enumerate(row['candidacies']) if c.get('is_winner') is True]
  outcome=row['contest_result'];called=row['is_called']
  assert isinstance(called,bool) and outcome in {'winner','uncontested','not called'},'Unexpected contest outcome'
  assert called==bool(marked) and called==(outcome!='not called') and len(marked)<=1,'Conflicting source call flags'
  if outcome=='uncontested':assert len(row['candidacies'])==len(marked)==1,'Uncontested outcome lacks unique explicit winner'
  common=dict(state='TX',body=body,district=district,sourceContestId=code,sourceRaceLabel=row['office_slug'],
   sourceIds=[source['id'],'media-south-tt-index','media-south-tt-script'],observationId=observation(source),observedAt=source['retrievedAt'],
   callingOrganization='The Associated Press',publisher='The Texas Tribune',sourceElectionType=row['election_type'])
  proof=dict(jsonPointer=f'/{ri}/contest_result',field='contest_result',value=outcome,corroboratingFields=dict(is_called=called,source=row['source']),
   publisherOutcomeType='explicit-publisher-uncontested-win' if outcome=='uncontested' else 'explicit-AP-race-call' if called else 'not-called',semanticsSourceId='media-south-tt-script')
  statuses.append(dict(common,id='media-race:'+digest([observation(source),code]),electionId=ELECTION_ID,called=called,status='called' if called else 'uncalled',
   designationCount=len(marked),electionDate='2026-11-03',specialElection=row['election_type']=='special',specialElectionStatus='publisher-provided',sourceProof=proof))
  for ci,c in marked:
   assert c['id'] and c['name'],'Missing source candidate identity'
   designations.append(dict(common,id='media-designation:'+digest([observation(source),code,c['id']]),electionId=ELECTION_ID,
    sourceCandidateId=str(c['id']),name=c['name'],partyLabel=c.get('party'),designationStatus='media-called-winner',certificationStatus='not-established',
    mediaCalledAt=None,mediaCallTimeStatus='not-provided',personId=None,identityStatus='Publisher contest/candidate identifiers; government identity unresolved',
    sourceProof=dict(proof,candidateJsonPointer=f'/{ri}/candidacies/{ci}/is_winner',candidateField='is_winner',candidateValue=True),
    limitations='Source AP call flag only; no government certification, service interval or maximum-vote inference.'))
 assert len(general['state-lower'])==150 and len(general['state-upper'])==16,'Unexpected Texas general-election coverage'
 return designations,statuses


NC_ASSERTIONS=[('Jessica Bichler','state-upper','7','Democrat','Jessica Bichler defeated Republican incumbent Michael Lee'),
 ('Bill Rabon','state-upper','8','Republican','Bill Rabon defeated Democrat challenger Richard Combes'),
 ('Frank Iler','state-lower','17','Republican','Frank Iler defeated Democratic challenger Dennis Breen'),
 ('Deb Butler','state-lower','18','Democrat','Deb Butler defeated Republican challenger Latisha Grady'),
 ('Charlie Miller','state-lower','19','Republican','Charlie Miller defeated Democrat challenger Scott Nasiff')]

def parse_whqr(raw,source):
 from build import HTML
 root=HTML(decode(raw).encode()).root
 assert source['url']==SOURCES['media-south-nc-whqr'][1] and 'Election 2026: Preliminary results for Cape Fear region races' in root.text()
 assert 'November 3, 2026' in root.text(),'Wrong article publication'
 articles=root.find(lambda n:n.tag=='article');assert articles
 paragraphs=articles[0].find(lambda n:n.tag=='p')
 output=[];statuses=[]
 for name,body,district,party,fragment in NC_ASSERTIONS:
  matched=[(i,p.text()) for i,p in enumerate(paragraphs) if fragment in p.text()];assert len(matched)==1,'Explicit newsroom outcome changed'
  pi,text=matched[0];proof=dict(selector='article p',paragraphIndex=pi,field='explicit named defeated assertion',value=fragment)
  common=dict(state='NC',body=body,district=district,sourceContestId=None,sourceIds=[source['id']],observationId=observation(source),observedAt=source['retrievedAt'],
   callingOrganization='WHQR',publisher='WHQR',sourceRaceLabel=('State Senate District ' if body=='state-upper' else 'NC House ')+district)
  output.append(dict(common,name=name,partyLabel=party,sourceCandidateId=None,designationStatus='media-called-winner',certificationStatus='not-established',
   mediaCalledAt=None,mediaCallTimeStatus='not-provided',sourceProof=proof,identityStatus='Named article subject and exact district; government candidate identity unresolved'))
  statuses.append(dict(common,called=True,status='called',electionDate='2026-11-03',specialElection=None,specialElectionStatus='not-provided',sourceProof=proof))
 return output,statuses



def parse_alabama(raw,source):
 data=json.loads(decode(raw));assert data['date']=='2026-11-03' and data['status']=='ready' and data['historical'] is False
 assert data.get('testDataShown') is not True,'Test publisher dataset'
 designations=[];statuses=[];seen=set();districts={'state-lower':set(),'state-upper':set()}
 for ri,row in enumerate(data['races']):
  body={'State House':'state-lower','State Senate':'state-upper'}.get(row['office'])
  if body is None:continue
  assert row['summary'] is True and row['disputed'] is False,'Not undisputed aggregate media result'
  match=re.fullmatch(r'AL-(HD|SD)-(\d{3})',row['district']);assert match,'Unexpected source district'
  assert match[1]==('HD' if body=='state-lower' else 'SD')
  district=str(int(match[2]));assert district not in districts[body];districts[body].add(district)
  code=str(row['id']);assert code and code not in seen;seen.add(code)
  marked=[(ci,c) for ci,c in enumerate(row['candidates']) if c.get('winner') is True];assert len(marked)<=1
  assert all(c.get('calledBy')=='apr' and c.get('writeIn') is not True for _,c in marked),'Not a named APR media call'
  proof=dict(jsonPointer=f'/races/{ri}',field='winner / calledBy',publisherVoteSource=row['source'],semanticsSourceId='media-south-al-script')
  common=dict(state='AL',body=body,district=district,sourceContestId=code,sourceRaceLabel=row['name'],
   sourceIds=[source['id'],'media-south-al-index','media-south-al-script'],observationId=observation(source),observedAt=source['retrievedAt'],
   callingOrganization='Alabama Political Reporter',publisher='Alabama Political Reporter',publisherUpdatedAt=row.get('updatedAt'))
  statuses.append(dict(common,called=bool(marked),status='called' if marked else 'uncalled',electionDate=data['date'],
   specialElection=None,specialElectionStatus='not-provided',sourceProof=proof))
  for ci,c in marked:
   assert c['id'] and c['name']
   designations.append(dict(common,name=c['name'],partyLabel=c.get('party'),sourceCandidateId=str(c['id']),
    designationStatus='media-called-winner',certificationStatus='not-established',mediaCalledAt=None,mediaCallTimeStatus='not-provided',
    sourceProof=dict(proof,jsonPointer=f'/races/{ri}/candidates/{ci}/winner',value=True,corroboratingFields=dict(calledBy='apr')),
    identityStatus='Publisher candidate ID and district; government identity unresolved'))
 assert len(districts['state-lower'])==105 and len(districts['state-upper'])==35,'Incomplete Alabama chamber feed'
 return designations,statuses


def collect(fetch,offline=False):
 acquired={};observations=[];designations=[];statuses=[];failures={};errors={}
 for key,(publisher,url) in SOURCES.items():
  try:
   raw,s=fetch(key,publisher,url,offline);acquired[key]=(raw,s);observations.append(dict(s,observationId=observation(s)))
  except Exception as exc:failures[key]=type(exc).__name__
 if all(k in acquired for k in ['media-south-tt-index','media-south-tt-script','media-south-tt-data']):
  try:
   tt_context(acquired['media-south-tt-index'][0],acquired['media-south-tt-script'][0]);d,r=parse_texas(*acquired['media-south-tt-data']);designations+=d;statuses+=r
  except Exception as exc:errors['TX']=type(exc).__name__+': '+str(exc)
 if all(k in acquired for k in ['media-south-al-index','media-south-al-script','media-south-al-data']):
  try:
   index=decode(acquired['media-south-al-index'][0]);script=decode(acquired['media-south-al-script'][0])
   assert '/_next/static/chunks/2yt3y_gbjse3r.js' in index and '/api/election-results' in script and 'APR call' in script and 'Race called by APR' in script
   d,r=parse_alabama(*acquired['media-south-al-data']);designations+=d;statuses+=r
  except Exception as exc:errors['AL']=type(exc).__name__+': '+str(exc)
 if 'media-south-nc-whqr' in acquired:
  try:d,r=parse_whqr(*acquired['media-south-nc-whqr']);designations+=d;statuses+=r
  except Exception as exc:errors['NC']=type(exc).__name__+': '+str(exc)
 return dict(designations=designations,raceStatuses=statuses,sourceObservations=observations,stateAudits=[dict(state=state,
  status='checked' if any(r['state']==state for r in statuses) else 'not-collected',
  observedLegislativeRaceCount=sum(r['state']==state for r in statuses),explicitMediaCallCount=sum(d['state']==state for d in designations),
  sourceIds=[s['id'] for s in observations],observationIds=[s['observationId'] for s in observations],
  scope='Texas AP and Alabama APR state-legislative feeds; North Carolina five named regional outcomes; other assigned states not collected',
  acquisitionFailures=failures,validationErrors=errors) for state in STATES])
