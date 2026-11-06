"""AP governor calls carried by NPR; separate from official certification."""
import datetime as dt
import gzip
import json
from .media_common import ELECTION_ID,observation,digest
from .media_common import STATE_FIPS

BASE='https://apps.npr.org/2026-election-results/'
SOURCES={
 'media-state-npr-governor-page':('NPR',BASE+'governors.html'),
 'media-state-npr-application':('NPR',BASE+'app.js'),
 'media-state-npr-governor-data':('NPR',BASE+'data/gov.json'),
}
GOV_KEYS=list(SOURCES)
SOURCES.update({
 'media-state-mpr-page':('MPR News','https://elections.mpr.org/'),
 'media-state-mpr-application':('MPR News','https://elections.mpr.org/static/js/main.d7c051c9.js'),
 'media-state-mpr-house':('MPR News','https://electionsapi.publicradio.org/2026-11-03/mn_house_races'),
 'media-state-mpr-senate':('MPR News','https://electionsapi.publicradio.org/2026-11-03/mn_senate_races'),
})
DELEGATIONS={}

def decoded(raw):
    return (gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw).decode('utf-8-sig')


def parse_governors(raw,source):
    document=json.loads(decoded(raw));rows=document['results']
    assert isinstance(rows,list) and rows,'Empty governor feed'
    seen=set();designations=[];audits=[]
    for index,row in enumerate(rows):
        state=row['state'];assert state in STATE_FIPS and state not in seen,'Duplicate or nonstate governor contest';seen.add(state)
        assert row['test'] is False and row['office']=='G' and row['officeName']=='Governor'
        assert row['type']=='General' and row['resultsType']=='live' and row['level']=='state','Wrong race scope/type'
        contest=str(row['id']);assert contest
        marked=[(i,c) for i,c in enumerate(row['candidates']) if c.get('winner')=='X']
        assert len(marked)<=1,'Multiple called governor winners'
        if marked:
            assert row.get('called') is True and row.get('raceCallStatus')=='Called','Inconsistent call flags'
            ci,c=marked[0];assert c['id'] and c.get('first') and c.get('last') and c.get('party')
            assert not str(c['id']).startswith('other-'),'Aggregate Others cannot be a called person'
            call=c.get('winnerDateTime');parsed=None
            if call:
                parsed=dt.datetime.fromisoformat(call.replace('Z','+00:00'));assert parsed.tzinfo and parsed.date()>=dt.date(2026,11,3),'Wrong call date'
                assert parsed<=dt.datetime.fromisoformat(source['retrievedAt'].replace('Z','+00:00')), 'Call time after source observation'
            name=c['first']+' '+c['last']
            proof=dict(jsonPointer='/results/'+str(index)+'/candidates/'+str(ci)+'/winner',field='winner',value='X',
                       contestCalledPointer='/results/'+str(index)+'/called',contestCalledValue=True,
                       raceCallStatus=row['raceCallStatus'],first=c['first'],last=c['last'],
                       semantics='NPR application renders candidate.winner === X as its winner icon and labels winnerDateTime as Winner called.')
            designations.append(dict(id='media-designation:'+digest([observation(source),state,contest,c['id'],proof]),
                electionId=ELECTION_ID,state=state,body='governor',district=None,name=name,partyLabel=c['party'],
                sourceContestId=contest,sourceCandidateId=str(c['id']),designationStatus='media-called-winner',callingOrganization='Associated Press',
                carryingOrganization='NPR',certificationStatus='not-established',personId=None,personLinkStatus='unresolved-official-identifier-required',
                sourceIds=[source['id'],'media-state-npr-governor-page','media-state-npr-application'],
                observationId=observation(source),observedAt=source['retrievedAt'],callTime=call,callTimeStatus='publisher-provided' if call else 'not-provided',
                publisherUpdatedAtUnixMillis=row.get('updated'),sourceProof=proof,
                limitations='Media race call only; separate from official certification, legal service and government roster membership. No vote-rank inference.'))
        else:
            assert row.get('called') is not True,'Contest called without explicit candidate winner'
        audits.append(dict(state=state,body='governor',status='called' if marked else 'uncalled',sourceContestId=contest,
            callingOrganization='Associated Press',carryingOrganization='NPR',sourceIds=[source['id']],observationIds=[observation(source)],
            publisherRaceCallStatus=row.get('raceCallStatus'),designationCount=len(marked),missingRowsEstablishNotOnBallot=False,
            id='media-race:'+digest([observation(source),contest]),electionId=ELECTION_ID,sourceRaceId=contest,
            electionDate='2026-11-03',publisherRaceType=row['type'],publisherOffice=row['office'],called=bool(marked),
            specialElection=row.get('isSpecial') if isinstance(row.get('isSpecial'),bool) else None,
            specialElectionStatus='publisher-provided' if isinstance(row.get('isSpecial'),bool) else 'not-provided',
            sourceProof=dict(jsonPointer='/results/'+str(index),field='raceCallStatus',value=row.get('raceCallStatus'))))
    return designations,audits



def parse_mpr_legislative(raw,source,body,root_key,office):
    import re
    rows=json.loads(decoded(raw))[root_key]
    assert body in {'state-upper','state-lower'} and rows
    seen=set();designations=[];audits=[]
    for ri,row in enumerate(rows):
        assert row['type']=='Race' and row['source']=='ap' and row['apOfficeId']==office,'Wrong MPR source/office'
        match=re.fullmatch(r'District (\d+[AB]?)',row['district']);assert match
        district=match[1];assert district not in seen;seen.add(district)
        assert row['name']==('State House District ' if body=='state-lower' else 'State Senate District ')+district
        choices=row['candidates'];assert choices and len({c['candidateId'] for c in choices})==len(choices)
        assert all(str(c['id']).startswith('2026-11-03-') for c in choices), 'Wrong candidate election epoch'
        marked=[(ci,c) for ci,c in enumerate(choices) if c.get('winner') is True]
        assert len(marked)<=1,'Multiple MN legislative winners require explicit multiseat modeling'
        for ci,c in marked:
            assert c['type']=='Candidate' and c['name'] and c['candidateId'] and c.get('party')
            assert str(c['id']).startswith('2026-11-03-'),'Wrong candidate election epoch'
            updated=c.get('lastUpdated')
            if updated:
                timestamp=dt.datetime.fromisoformat(updated.replace('Z','+00:00'))
                assert timestamp.tzinfo and timestamp<=dt.datetime.fromisoformat(source['retrievedAt'].replace('Z','+00:00')),'Future publisher update'
            proof=dict(jsonPointer='/'+root_key+'/'+str(ri)+'/candidates/'+str(ci)+'/winner',field='winner',value=True,
                publisherSourceField=row['source'],publisherOffice=row['apOfficeId'],officeLabel=row['name'],
                semantics='MPR renders candidate.winner true as checkmark/candidate_pct_win; publisher source field ap identifies AP.')
            designations.append(dict(id='media-designation:'+digest([observation(source),'MN',body,district,c['candidateId'],proof]),
                electionId=ELECTION_ID,state='MN',body=body,district=district,name=c['name'],partyLabel=c['party'],
                sourceContestId=None,sourceRaceLabel=row['name'],sourceCandidateId=str(c['candidateId']),publisherCandidateRecordId=c['id'],
                designationStatus='media-called-winner',callingOrganization='Associated Press',carryingOrganization='MPR News',certificationStatus='not-established',
                personId=None,personLinkStatus='unresolved-official-identifier-required',sourceIds=[source['id'],'media-state-mpr-page','media-state-mpr-application'],
                observationId=observation(source),observedAt=source['retrievedAt'],callTime=None,callTimeStatus='not-provided',publisherUpdatedAt=updated,
                sourceProof=proof,limitations='AP-sourced media winner flag; lastUpdated is not a call timestamp. No official certification or legal service inference.'))
        audits.append(dict(id='media-race:'+digest([observation(source),'MN',body,district]),electionId=ELECTION_ID,state='MN',body=body,district=district,
            sourceRaceId=None,sourceRaceLabel=row['name'],status='called' if marked else 'uncalled',called=bool(marked),designationCount=len(marked),
            electionDate='2026-11-03',specialElection=None,specialElectionStatus='not-provided',sourceIds=[source['id']],observationIds=[observation(source)],
            callingOrganization='Associated Press',carryingOrganization='MPR News',missingRowsEstablishNotOnBallot=False,
            sourceProof=dict(jsonPointer='/'+root_key+'/'+str(ri),field='source',value='ap')))
    return designations,audits


def collect(fetch,offline=False):
    acquired={};sources=[];failures={};issues={};designations=[];audits=[]
    for key,(publisher,url) in SOURCES.items():
        try:
            raw,source=fetch(key,publisher,url,offline);acquired[key]=(raw,source);sources.append(dict(source,observationId=observation(source)))
        except Exception as exc:failures[key]=type(exc).__name__
    if all(k in acquired for k in GOV_KEYS):
        try:
            page=decoded(acquired['media-state-npr-governor-page'][0]);script=decoded(acquired['media-state-npr-application'][0])
            assert '2026' in page and 'governor' in page.lower() and 'app.js' in page
            assert './data/gov.json' in script and 'Election results are tabulated by The Associated Press.' in script
            assert 'winner === "X"' in script and 'Winner called:' in script,'Publisher call-field semantics unavailable'
            designations,audits=parse_governors(*acquired['media-state-npr-governor-data'])
        except Exception as exc:issues['governor-publication']=type(exc).__name__+': '+str(exc)
    governor_races=[dict(a) for a in audits]
    for key,body,root_key,office in [('media-state-mpr-house','state-lower','mnHouse','Y'),('media-state-mpr-senate','state-upper','mnSenate','Z')]:
        if all(k in acquired for k in [key,'media-state-mpr-page','media-state-mpr-application']):
            try:
                script=decoded(acquired['media-state-mpr-application'][0]);page=decoded(acquired['media-state-mpr-page'][0])
                assert '/static/js/main.d7c051c9.js' in page and 'https://electionsapi.publicradio.org' in script
                assert ('/mn_house_races' if body=='state-lower' else '/mn_senate_races') in script and 'candidate_pct_win' in script
                d,a=parse_mpr_legislative(*acquired[key],body,root_key,office)
                designations.extend(d);audits.extend(a)
            except Exception as exc:issues[key]=type(exc).__name__+': '+str(exc)
    observed={a['state'] for a in governor_races}
    observed_scopes={(a['state'],a['body']) for a in audits}
    for state in STATE_FIPS:
        if state not in observed:
            audits.append(dict(state=state,body='governor',status='not-collected',designationCount=0,sourceIds=[s['id'] for s in sources],
                observationIds=[observation(s) for s in sources],missingRowsEstablishNotOnBallot=False,
                reason='No validated contest in the observed governor feed; no independent not-on-ballot assertion.'))
        for body in ['state-upper','state-lower']:
            if (state,body) in observed_scopes:continue
            audits.append(dict(state=state,body=body,status='not-collected',designationCount=0,sourceIds=[],observationIds=[],
                missingRowsEstablishNotOnBallot=False,reason='NPR governor feed does not provide candidate-level state legislative calls; no chamber-control or vote-leader substitution.'))
    return dict(designations=designations,raceStatuses=[a for a in audits if a.get('sourceRaceId') or a.get('sourceRaceLabel')],stateAudits=audits,sourceObservations=sources,
                coverage=dict(acquisitionFailures=failures,parserFailures=issues,mediaCallsSeparateFromOfficialCertification=True,
                              observedGovernorContests=len(observed),calledGovernorContests=sum(d['body']=='governor' for d in designations),stateLegislativeCandidateCalls='Minnesota AP-sourced candidate flags only; other states pending'))
