"""Direct AP state legislative call feeds for twelve Midwest/Plains states."""
from .media_common import observation
from .media_ap import SOURCES as CONTEXT_SOURCES

STATES=['WI','MI','IA','IL','IN','OH','ND','SD','NE','KS','MO','OK']
BASE='https://interactives.apelections.org/election-results/data-live/2026-11-03/results/races/'
SOURCES={f'media-ap-midwest-{state.lower()}-{kind}':('Associated Press',BASE+state+'/'+kind+'.json')
         for state in STATES for kind in ['metadata','progress']}
SOURCES={**CONTEXT_SOURCES,**SOURCES}
DELEGATIONS={}


def collect(fetch,offline=False):
    from .media_ap import parse_state,collect_context
    sources=[];designations=[];races=[];audits=[];failures={};issues={};context_ready=False
    try:
        sources=collect_context(fetch,offline);context_ready=True
    except Exception as exc:issues['AP-context']=type(exc).__name__+': '+str(exc)
    context_ids=[source['id'] for source in sources]
    for state in STATES:
        acquired={}
        for kind in ['metadata','progress']:
            key='media-ap-midwest-'+state.lower()+'-'+kind
            try:
                raw,source=fetch(key,*SOURCES[key],offline);acquired[kind]=(raw,source)
                sources.append(dict(source,observationId=observation(source)))
            except Exception as exc:failures[key]=type(exc).__name__
        d=[];r=[]
        if len(acquired)==2 and context_ready:
            try:
                d,r=parse_state(*acquired['metadata'],*acquired['progress'],context_source_ids=context_ids)
                assert all(row['state']==state for row in d+r),'AP state crossed collection boundary'
                designations.extend(d);races.extend(r)
            except Exception as exc:issues[state]=type(exc).__name__+': '+str(exc)
        refs=[source['id'] for _,source in acquired.values()]
        epochs=[observation(source) for _,source in acquired.values()]
        for body in ['state-upper','state-lower']:
            observed=[row for row in r if row['body']==body];calls=[row for row in d if row['body']==body]
            audits.append(dict(state=state,body=body,status='collected' if observed else 'not-collected',
                raceCount=len(observed),designationCount=len(calls),sourceIds=refs,observationIds=epochs,
                missingRowsEstablishNotOnBallot=False,
                reason='Direct AP candidate call flags and all selected race statuses, including uncalled and multiwinner races. No vote ranking, chamber-control inference, or official certification. Missing offices do not establish no election.'))
    assert len({row['id'] for row in designations})==len(designations),'Duplicate AP designation IDs'
    assert len({row['id'] for row in races})==len(races),'Duplicate AP race observation IDs'
    return dict(designations=designations,raceStatuses=races,stateAudits=audits,sourceObservations=sources,
                coverage=dict(acquisitionFailures=failures,parserFailures=issues,complete=False,
                    observationAtomicity='Metadata and progress are separately observed original AP publications; no atomic simultaneous snapshot claim.',
                    scope='Selected AP state legislative offices from twelve states; uncollected states/offices remain explicit.'))
