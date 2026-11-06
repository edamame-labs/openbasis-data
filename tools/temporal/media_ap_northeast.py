"""Explicit AP legislative calls from eleven Northeast state publications."""
from . import media_ap
from .media_common import observation

STATES='NY PA MA NH CT RI ME VT NJ DE MD'.split()
SOURCES={**media_ap.SOURCES}
for state in STATES:
 for kind in ['metadata','progress']:
  SOURCES[f'media-northeast-ap-{state.lower()}-{kind}']=('The Associated Press',media_ap.BASE+f'data-live/2026-11-03/results/races/{state}/{kind}.json')
DELEGATIONS={}


def collect(fetch,offline=False):
 observations=[];designations=[];statuses=[];audits=[];context_error=None
 try:observations=media_ap.collect_context(fetch,offline)
 except Exception as exc:context_error=type(exc).__name__+': '+str(exc)
 context_ids=[s['id'] for s in observations]
 for state in STATES:
  acquired={};failures={};errors={}
  for kind in ['metadata','progress']:
   key=f'media-northeast-ap-{state.lower()}-{kind}'
   try:
    raw,s=fetch(key,*SOURCES[key],offline);acquired[kind]=(raw,s);observations.append(dict(s,observationId=observation(s)))
   except Exception as exc:failures[key]=type(exc).__name__
  d=[];r=[]
  if context_error:errors['AP-application-context']=context_error
  elif not failures:
   try:d,r=media_ap.parse_state(*acquired['metadata'],*acquired['progress'],context_source_ids=context_ids)
   except Exception as exc:errors[state]=type(exc).__name__+': '+str(exc)
  designations.extend(d);statuses.extend(r)
  audits.append(dict(state=state,status='checked' if not failures and not errors else 'access-blocked',
   observedLegislativeRaceCount=len(r),explicitMediaCallCount=len(d),
   sourceIds=context_ids+[s['id'] for _,s in acquired.values()],observationIds=[s['observationId'] for s in observations if s['id'] in context_ids]+[observation(s) for _,s in acquired.values()],
   scope='Exact November3 AP state dictionary, officeIDs Y/Z; absent offices do not establish not-on-ballot',
   acquisitionFailures=failures,validationErrors=errors,missingRowsEstablishNotOnBallot=False))
 return dict(designations=designations,raceStatuses=statuses,stateAudits=audits,sourceObservations=observations)
