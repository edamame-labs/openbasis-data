"""AP California legislative calls from preserved browser accessibility snapshots."""
import re
from .media_common import observation,digest,ELECTION_ID

BASE='https://interactives.apelections.org/election-results/customers/layouts/organization-layouts/published/117697/'
SOURCES={
 'media-california-ap-senate-ax':('The Associated Press',BASE+'38146.html'),
 'media-california-ap-assembly-cards-ax':('The Associated Press',BASE+'38133.html'),
}
DELEGATIONS={}
OFFICES={'media-california-ap-senate-ax':('state-upper','California State Senate',set(range(2,41,2))),
         'media-california-ap-assembly-cards-ax':('state-lower','California State Assembly',set(range(1,81)))}


def parse_snapshot(raw,source):
 key=source['id'];assert key in OFFICES and source['url']==SOURCES[key][1],'Unknown AP snapshot publication'
 assert source.get('representation')=='browser-accessibility-tree','Requires original accessibility-tree representation'
 body,heading,expected=OFFICES[key];text=raw.decode('utf-8')
 if 'AXWebArea' in text.splitlines()[0]:
  assert source['url'].split('://',1)[1] in text.splitlines()[0],'Accessibility document URL mismatch'
 else:
  assert (source.get('acquisition') or {}).get('engine')=='Playwright.domSnapshot','Unidentified accessibility projection engine'
 assert heading in text,'Wrong source chamber'
 # Text nodes can span multiple complete cards. Node numbers and image labels
 # are accessibility structure, not candidate data; preserve original raw bytes.
 nodes=[]
 for line in text.splitlines():
  match=re.match(r'^\s*\d+ text (.*)$',line) or re.match(r'^\s*- (?:generic|text): (.*)$',line)
  if match:nodes.append(match[1])
 rendered=' '.join(nodes)
 assert re.search(r'Updated Nov [34], 2026 at ',rendered),'Wrong or missing current publication context'
 starts=list(re.finditer(r'\bDISTRICT (\d+)\b',rendered,re.I));districts=[int(m[1]) for m in starts]
 assert set(districts)==expected and len(districts)==len(expected),'Incomplete or duplicate chamber cards'
 output=[];statuses=[]
 for i,match in enumerate(starts):
  district=match[1];card=rendered[match.end():starts[i+1].start() if i+1<len(starts) else len(rendered)].strip()
  called=re.match(r'^WINNER (.+?)\s+wins\.\s+AP race call at\s+(.+?\bon\s+Nov\. [34], 2026)\s*\.',card)
  uncontested=re.fullmatch(r'UNCONTESTED (.+?) wins, running unopposed\.',card)
  marked=bool(called or uncontested)
  assert marked or ('WINNER' not in card and 'leads by' in card),'Unrecognized or incomplete AP card outcome'
  proof=dict(accessibilityCardDistrict=district,field='explicit AP card narrative',
   value='WINNER / wins. / AP race call at' if called else 'UNCONTESTED / wins, running unopposed.' if uncontested else 'leads by',
   publisherOutcomeType='explicit-AP-race-call' if called else 'explicit-publisher-uncontested-win' if uncontested else 'lead-only',
   publisherCardText=card,sourceHeading=heading,
   publisherCallTimeRaw=called[2].strip() if called else None,callTimeTimezone='not-established')
  common=dict(state='CA',body=body,district=district,sourceContestId=None,sourceRaceLabel=heading+' District '+district,
   sourceIds=[key],observationId=observation(source),observedAt=source['retrievedAt'],callingOrganization='The Associated Press',publisher='The Associated Press')
  statuses.append(dict(common,id='media-race:'+digest([observation(source),body,district]),electionId=ELECTION_ID,
   called=marked,status='called' if marked else 'uncalled',designationCount=int(marked),
   electionDate='2026-11-03',sourceElectionType='General',specialElection=None,specialElectionStatus='not-provided',
   missingRowsEstablishNotOnBallot=False,sourceProof=proof))
  if marked:
   name=(called or uncontested)[1].strip();assert name and not re.search(r'leads by|DISTRICT|WINNER',name),'Invalid called candidate label'
   output.append(dict(common,id='media-designation:'+digest([observation(source),body,district,name]),electionId=ELECTION_ID,
    name=name,partyLabel=None,sourceCandidateId=None,designationStatus='media-called-winner',certificationStatus='not-established',
    personId=None,identityStatus='Exact rendered publisher candidate label; abbreviations preserved; government identity unresolved',
    mediaCalledAt=None,mediaCallTimeStatus='publisher-literal-without-established-timezone' if called else 'no-call-time-uncontested-win',publisherCallTimeRaw=called[2].strip() if called else None,
    sourceProof=proof,limitations='AP media race call only; no legal certification, serving membership or full-name expansion inferred.'))
 return output,statuses


def collect(fetch,offline=False):
 designations=[];statuses=[];observations=[];failures={};errors={}
 for key,(publisher,url) in SOURCES.items():
  try:
   raw,source=fetch(key,publisher,url,offline);observations.append(dict(source,observationId=observation(source)))
   try:
    d,r=parse_snapshot(raw,source);designations.extend(d);statuses.extend(r)
   except Exception as exc:errors[key]=type(exc).__name__+': '+str(exc)
  except Exception as exc:failures[key]=type(exc).__name__
 return dict(designations=designations,raceStatuses=statuses,sourceObservations=observations,stateAudits=[dict(state='CA',
  status='checked' if statuses else 'access-blocked',observedLegislativeRaceCount=len(statuses),explicitMediaCallCount=len(designations),
  sourceIds=[s['id'] for s in observations],observationIds=[s['observationId'] for s in observations],
  scope='Rendered AP California legislative cards; call-time timezone and candidate identifiers unresolved',
  acquisitionFailures=failures,validationErrors=errors)])
