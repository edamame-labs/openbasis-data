"""Exact AP state-legislative metadata/progress publications, southern states."""
from . import media_ap
from .media_common import observation

STATES='TX NC GA FL VA SC AL TN KY AR LA MS WV'.split()
BASE=media_ap.BASE+'data-live/2026-11-03/results/races/'
SOURCES=dict(media_ap.SOURCES)
for state in STATES:
 for part in ['metadata','progress']:
  SOURCES[f'media-ap-south-{state.lower()}-{part}']=('The Associated Press',BASE+state+'/'+part+'.json')
DELEGATIONS={}


def collect(fetch,offline=False):
 sources=[];designations=[];statuses=[];audits=[];failures={};errors={}
 try:context=media_ap.collect_context(fetch,offline);sources.extend(context)
 except Exception as exc:
  context=[];errors['shared-AP-context']=type(exc).__name__+': '+str(exc)
 ids=[s['id'] for s in context]
 for state in STATES:
  acquired={};state_sources=[];state_d=[];state_r=[]
  for part in ['metadata','progress']:
   key=f'media-ap-south-{state.lower()}-{part}'
   try:
    raw,source=fetch(key,*SOURCES[key],offline);acquired[part]=(raw,source)
    obs=dict(source,observationId=observation(source));sources.append(obs);state_sources.append(obs)
   except Exception as exc:failures[key]=type(exc).__name__+': '+str(exc)
  if context and len(acquired)==2:
   try:
    state_d,state_r=media_ap.parse_state(*acquired['metadata'],*acquired['progress'],context_source_ids=ids)
    designations.extend(state_d);statuses.extend(state_r)
   except Exception as exc:errors[state]=type(exc).__name__+': '+str(exc)
  audits.append(dict(state=state,status='checked' if state_r else 'not-collected',observedLegislativeRaceCount=len(state_r),
   explicitMediaCallCount=len(state_d),sourceIds=[s['id'] for s in state_sources]+ids,
   observationIds=[s['observationId'] for s in state_sources+context],
   scope='AP published November3 legislative race observations only; missing rows establish neither no election nor a vacant seat',
   acquisitionFailures={k:v for k,v in failures.items() if k.startswith('media-ap-south-'+state.lower()+'-')},
   validationErrors={k:v for k,v in errors.items() if k in {state,'shared-AP-context'}}))
 return dict(designations=designations,raceStatuses=statuses,sourceObservations=sources,stateAudits=audits)
