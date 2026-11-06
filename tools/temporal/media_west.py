"""OPB's published AP legislative results for Oregon and Washington."""
import gzip
import json
import re
from datetime import datetime
from .media_common import observation,ELECTION_ID,digest

SOURCES={'media-west-opb':('OPB','https://www.opb.org/elections-2026/')}
DELEGATIONS={}

def parse(raw,source):
    text=(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw).decode('utf-8')
    marker='Fusion.globalContent='
    assert text.count(marker)==1,'Missing unique publisher result payload'
    data=json.JSONDecoder().raw_decode(text.split(marker,1)[1])[0]
    assert data['test'] is False and data['APResults']['electionDate']=='2026-11-03'
    rows=data['APResults']['races'];designations=[];statuses=[];seen=set()
    for i,r in enumerate(rows):
        if r['officeID'] not in {'Y','Z'}:continue
        assert r['test'] is False and r['resultsType']=='live' and r['eventID']=='20261103'
        assert r['raceType']=='General' and r['raceTypeID']=='G'
        state=r['statePostal'];assert state in {'OR','WA'}
        body={'Y':'state-lower','Z':'state-upper'}[r['officeID']]
        assert r['officeName']=={'Y':'State House','Z':'State Senate'}[r['officeID']]
        contest=str(r['raceID']);assert contest not in seen;seen.add(contest)
        district=str(int(r['censusDistrict']));seat=r['seatName']
        assert int(r['seatNum'])==int(district) and re.match(r'^District '+district+r'(?:$| - Position [12]$)',seat)
        # Washington elects two distinct House positions within one boundary.
        position=r.get('position');assert not position or (state=='WA' and body=='state-lower' and position in {'1','2'})
        units=[(j,u) for j,u in enumerate(r['reportingUnits']) if u.get('level')=='state']
        assert len(units)==1 and units[0][1]['statePostal']==state,'No unique districtwide observation'
        ui,unit=units[0];candidates=unit['candidates']
        assert candidates==r['candidates'],'Publisher summary differs from state-level report'
        marked=[(j,c) for j,c in enumerate(candidates) if c.get('winner')=='X']
        assert len(marked)<=1
        assert bool(marked)==(r['raceCallStatus']=='Called'),'Inconsistent publisher call marker'
        common=dict(state=state,body=body,district=district,sourceContestId=contest,
            sourceIds=[source['id']],observationId=observation(source),observedAt=source['retrievedAt'],
            callingOrganization='The Associated Press',publisher='OPB',sourceSeatLabel=seat,
            sourceSeatNumber=r['seatNum'],sourcePosition=position,sourceElectionType=r['raceType'])
        proof=dict(payload='Fusion.globalContent.APResults',jsonPointer='/APResults/races/'+str(i),
            raceCallStatus=r['raceCallStatus'],sourcePosition=position,
            semantics='OPB renders winner candidates with class winner and aria-label Winner; APResults marks those candidates winner X.')
        statuses.append(dict(common,called=bool(marked),status='called' if marked else 'uncalled',sourceProof=proof))
        if marked:
            ci,c=marked[0];assert c.get('first') and c.get('last') and c.get('candidateID') and c.get('label')
            call=c.get('winnerDateTime')
            if call:
                parsed=datetime.fromisoformat(call.replace('Z','+00:00'))
                assert parsed.tzinfo and parsed<=datetime.fromisoformat(source['retrievedAt'].replace('Z','+00:00'))
            winnerproof=dict(proof,jsonPointer='/APResults/races/'+str(i)+'/reportingUnits/'+str(ui)+'/candidates/'+str(ci)+'/winner',field='winner',value='X')
            designations.append(dict(common,id='media-designation:'+digest([observation(source),contest,c['candidateID']]),
                electionId=ELECTION_ID,name=c['label'],partyLabel=c.get('party'),sourceCandidateId=str(c['candidateID']),
                designationStatus='media-called-winner',certificationStatus='not-established',
                mediaCalledAt=call,sourceProof=winnerproof))
    return designations,statuses

def collect(fetch,offline=False):
    designations=[];statuses=[];sources=[];errors={}
    for key,(publisher,url) in SOURCES.items():
        try:
            raw,source=fetch(key,publisher,url,offline);sources.append(dict(source,observationId=observation(source)))
            d,r=parse(raw,source);designations.extend(d);statuses.extend(r)
        except Exception as exc:errors[key]=type(exc).__name__+': '+str(exc)
    return dict(designations=designations,raceStatuses=statuses,sourceObservations=sources,stateAudits=[],coverage=dict(parserFailures=errors))
