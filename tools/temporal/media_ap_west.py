"""Source-scoped AP legislative observations for fourteen western states."""
from .media_ap import parse_state,collect_context,SOURCES as CONTEXT_SOURCES
from .media_common import observation

STATES='AK AZ CA CO HI ID MT NV NM OR UT WA WY MN'.split()
BASE='https://interactives.apelections.org/election-results/data-live/2026-11-03/results/races/'
SOURCES={f'media-ap-west-{s.lower()}-{kind}':('The Associated Press',BASE+s+'/'+kind+'.json') for s in STATES for kind in ['metadata','progress']}
SOURCES={**CONTEXT_SOURCES,**SOURCES}
DELEGATIONS={}

def collect(fetch,offline=False):
    designations=[];statuses=[];sources=collect_context(fetch,offline);errors={};audits=[]
    context_ids=[s['id'] for s in sources]
    for state in STATES:
        try:
            acquired=[]
            for kind in ['metadata','progress']:
                key=f'media-ap-west-{state.lower()}-{kind}';publisher,url=SOURCES[key]
                raw,source=fetch(key,publisher,url,offline);sources.append(dict(source,observationId=observation(source)));acquired.extend([raw,source])
            d,r=parse_state(*acquired,context_source_ids=context_ids);designations.extend(d);statuses.extend(r)
            audits.append(dict(state=state,status='collected-publisher-scope',observedLegislativeRaces=len(r),explicitWinnerDesignations=len(d),sourceIds=[acquired[1]['id'],acquired[3]['id']]))
        except Exception as exc:errors[state]=type(exc).__name__+': '+str(exc)
    return dict(designations=designations,raceStatuses=statuses,sourceObservations=sources,stateAudits=audits,coverage=dict(parserFailures=errors))
