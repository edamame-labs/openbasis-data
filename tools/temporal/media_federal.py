"""Explicit AP calls published by NPR; separate from government results."""
from collections import Counter
from datetime import datetime
import gzip
import json
import re
from .media_common import observation

BASE='https://apps.npr.org/2026-election-results/'
SOURCES={
 'media-federal-npr-index':('NPR',BASE),
 'media-federal-npr-script':('NPR',BASE+'app.js'),
 'media-federal-npr-house':('NPR',BASE+'house.html'),
 'media-federal-npr-senate':('NPR',BASE+'senate.html'),
 'media-federal-npr-house-data':('NPR',BASE+'data/house.json'),
 'media-federal-npr-senate-data':('NPR',BASE+'data/senate.json'),
}
DELEGATIONS={}
STATES=set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())
AT_LARGE={'AK','DE','ND','SD','VT','WY'}


def decode(raw):
    # Preserve HTTP entity bytes/checksum; decoding is an explicit parser step.
    return (gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw).decode('utf-8')


def instant(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    assert parsed.tzinfo is not None,'Publisher call time lacks timezone'
    return parsed


def validate_context(index_raw,script_raw):
    index=decode(index_raw);script=decode(script_raw)
    assert '2026 Election Results' in index and 'src="app.js"' in index,'Wrong year/application context'
    assert 'Election results are tabulated by The Associated Press.' in script,'Missing publisher AP attribution'
    assert 'd.winner === "X"' in script and 'el.classList.add("winner")' in script,'Winner encoding no longer verified by rendering code'
    assert 'winnerDateTime' in script and 'Winner called:' in script,'Call-time meaning unverified'
    for name in ['house','senate']:
        assert './data/'+name+'.json' in script,'Feed not explicitly referenced by publisher application'


def parse_feed(raw,source,body,context_sources,race_statuses=None):
    assert body in {'us-house','us-senate'}
    part='house' if body=='us-house' else 'senate'
    assert source['url']==SOURCES['media-federal-npr-'+part+'-data'][1],'Wrong media feed URL'
    rows=json.loads(decode(raw))['results'];assert isinstance(rows,list) and rows,'Empty media race list'
    designations=[];audits=Counter();calls=Counter();seen=set()
    for i,race in enumerate(rows):
        state=race['state']
        assert state in STATES and race.get('test') is False,'Unknown jurisdiction or test result'
        assert race['office']==('H' if body=='us-house' else 'S') and race['level']=='state','Wrong office or component reporting scope'
        assert race['resultsType']=='live','Non-live results cannot establish media calls'
        assert race['type'] in ({'General','Nonpartisan Election'} if body=='us-house' else {'General','Special General'}),'Unexpected race type'
        code=str(race['id']);assert code and code not in seen,'Duplicate source race';seen.add(code)
        district=None
        if body=='us-house':
            match=re.fullmatch(r'District (\d+)',race['seat']);assert match and match[1]==race['seatNumber'],'District/seat source disagreement'
            district='0' if state in AT_LARGE else str(int(match[1]))
            if state in AT_LARGE:assert int(match[1])==1,'Unknown at-large source-seat alias'
        candidates=race['candidates'];assert len({str(c['id']) for c in candidates})==len(candidates),'Duplicate source candidate'
        winners=[(j,c) for j,c in enumerate(candidates) if c.get('winner')=='X']
        called=race.get('called') is True
        assert called==bool(winners) and len(winners)<=1,'Conflicting winner/called fields'
        audits[state]+=1
        if race_statuses is not None:
            winner=winners[0][1] if winners else None
            race_statuses.append(dict(state=state,body=body,district=district,sourceContestId=code,
                sourceSeatNumber=race['seatNumber'],sourceSeatLabel=race['seat'],sourceElectionType=race['type'],
                called=called,status='media-called' if called else 'not-called',publisherRaceCallStatus=race.get('raceCallStatus'),
                winner=dict(sourceCandidateId=str(winner['id']),name=' '.join(v.strip() for v in [winner.get('first',''),winner.get('last','')] if v.strip()),partyLabel=winner.get('party')) if winner else None,
                mediaCalledAt=winner.get('winnerDateTime') if winner else None,
                sourceIds=[source['id']]+context_sources,observationId=observation(source),observedAt=source['retrievedAt'],
                sourceProof=dict(jsonPointer=f'/results/{i}',calledFieldPresent='called' in race,calledValue=race.get('called'),raceCallStatus=race.get('raceCallStatus')),
                callingOrganization='The Associated Press',publisher='NPR',certificationStatus='not-established'))
        if not called:continue
        assert race.get('raceCallStatus')=='Called','Call-status corroboration missing'
        for j,c in winners:
            assert c['id'] and not str(c['id']).startswith('other-'),'Aggregate Other is not a named winner'
            name=' '.join(v.strip() for v in [c.get('first',''),c.get('last','')] if v.strip());assert name,'Missing called candidate label'
            calltime=c.get('winnerDateTime')
            if calltime:assert instant(calltime)<=instant(source['retrievedAt']),'Call time is after actual observation'
            calls[state]+=1
            designations.append(dict(state=state,body=body,district=district,
                sourceContestId=code,sourceCandidateId=str(c['id']),name=name,partyLabel=c.get('party'),
                sourceSeatNumber=race['seatNumber'],sourceSeatLabel=race['seat'],sourceElectionType=race['type'],
                districtNormalization='AP District1 alias for single at-large district0' if body=='us-house' and state in AT_LARGE else 'publisher district label' if district else None,
                designationStatus='media-called-winner',callingOrganization='The Associated Press',publisher='NPR',
                publisherAttribution='Election results are tabulated by The Associated Press.',
                certificationStatus='not-established',sourceIds=[source['id']]+context_sources,
                observationId=observation(source),observedAt=source['retrievedAt'],
                mediaCalledAt=calltime,mediaCallTimeStatus='publisher-provided-timezone-qualified' if calltime else 'not-provided',
                sourceProof=dict(jsonPointer=f'/results/{i}/candidates/{j}/winner',field='winner',value='X',
                    corroboratingFields={'called':True,'raceCallStatus':'Called'},callTimeJsonPointer=f'/results/{i}/candidates/{j}/winnerDateTime' if calltime else None,
                    semanticsSourceId='media-federal-npr-script'),
                identityStatus='AP election/contest/candidate identifiers; unresolved against government candidacies and global people',
                scopeLimitations='Media race call only; no government certification, legal term or serving membership inferred.'))
    return designations,audits,calls


def collect(fetch,offline=False):
    acquired={};sources=[];failures={};errors={};designations=[];race_statuses=[];races=Counter();calls=Counter()
    for key,(publisher,url) in SOURCES.items():
        try:
            raw,s=fetch(key,publisher,url,offline);acquired[key]=(raw,s);sources.append(dict(s,observationId=observation(s)))
        except Exception as exc:failures[key]=type(exc).__name__
    context=['media-federal-npr-index','media-federal-npr-script'];valid=False
    if all(k in acquired for k in context):
        try:validate_context(acquired[context[0]][0],acquired[context[1]][0]);valid=True
        except Exception as exc:errors['context']=str(exc)
    for part,body in [('house','us-house'),('senate','us-senate')]:
        key='media-federal-npr-'+part+'-data'
        if not valid or key not in acquired:continue
        try:
            feed_statuses=[]
            ds,rs,cs=parse_feed(*acquired[key],body,context,feed_statuses)
            race_statuses.extend(feed_statuses)
            designations.extend(ds);races.update(rs);calls.update(cs)
        except Exception as exc:errors[part]=str(exc)
    return dict(designations=designations,raceStatuses=race_statuses,stateAudits=[dict(state=state,status='checked' if races[state] else 'access-blocked',
        observedFederalRaceCount=races[state],explicitMediaCallCount=calls[state],
        sourceIds=[s['id'] for s in sources],observationIds=[s['observationId'] for s in sources],
        scope='Observed NPR/AP federal races only; uncalled and missing offices remain unresolved',
        acquisitionFailures=failures,validationErrors=errors) for state in sorted(STATES)],sourceObservations=sources)
