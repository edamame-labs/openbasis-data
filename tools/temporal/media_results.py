"""Reproducible media outcome master; government evidence remains separate."""
import csv
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from . import media_federal,media_state,media_additional,media_california,media_west,media_midwest,media_south
from . import media_ap_northeast,media_ap_midwest,media_ap_south,media_ap_west
from .media_common import digest,observation
from .evidence import validate_observations
from .media_evidence import MediaEvidenceStore

COLLECTORS=(media_federal,media_state,media_additional,media_california,media_west,media_midwest,media_south)
AP_COLLECTORS=(media_ap_northeast,media_ap_midwest,media_ap_south,media_ap_west)


def _instant(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Media timestamp requires timezone')
    return result


def _check_errors(packet):
    def visit(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in {'acquisitionFailures','parserFailures','validationErrors','validationError'} and item:
                    raise ValueError('Media collection failed: '+key+' '+str(item))
                visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(packet)


def _key(row):
    # Exact publisher office/district identity, never a candidate-name join.
    return (row['state'],row['body'],str(row.get('district')),row.get('sourceContestId'),tuple(sorted(row['sourceIds'][:1])))


def combine(packets, *, require_npr_snapshot=True):
    sources={};designations=[];statuses=[];audits=[]
    for packet in packets:
        _check_errors(packet)
        for s in packet['sourceObservations']:
            oid=s.get('observationId') or observation(s)
            if oid!=observation(s):raise ValueError('Media observation identity mismatch')
            s=dict(s,observationId=oid)
            if oid in sources and sources[oid]!=s:raise ValueError('Conflicting immutable media observation')
            sources[oid]=s
        designations.extend(packet['designations']);statuses.extend(packet.get('raceStatuses',[]));audits.extend(packet.get('stateAudits',[]))
    by_source={s['id'] for s in sources.values()}
    def refs(row):
        oid=row.get('observationId')
        if oid is None:
            ids=row.get('observationIds',[])
            if len(ids)!=1:raise ValueError('Media race needs an exact primary observation')
            oid=ids[0]
        if oid not in sources:raise ValueError('Missing media primary observation')
        primary=sources[oid]
        if not set(row['sourceIds'])<=by_source:raise ValueError('Missing media context source')
        if row.get('observedAt',primary['retrievedAt'])!=primary['retrievedAt']:raise ValueError('Media observation time mismatch')
        return primary,[dict(sourceId=s['id'],observationId=s['observationId'],publisher=s['name'],url=s['url'],sha256=s['sha256'],observedAt=s['retrievedAt'],representation=s.get('representation')) for s in sources.values() if s['id'] in row['sourceIds']]
    indexed={}
    for d in designations:
        if d['designationStatus']!='media-called-winner':raise ValueError('Unexpected media designation status')
        key=_key(d)
        if d.get('sourceContestId') is None and d.get('district') is None and d['body'] in {'state-upper','state-lower'}:continue
        group=indexed.setdefault(key,[])
        if any((v.get('sourceCandidateId'),v['name'])==(d.get('sourceCandidateId'),d['name']) for v in group):
            raise ValueError('Duplicate source media candidate designation')
        group.append(d)
    races=[];consumed=set();seen=set()
    for status in statuses:
        key=_key(status)
        if key in seen:raise ValueError('Duplicate publisher media race identity')
        seen.add(key);group=indexed.get(key,[]);d=group[0] if group else None;called=status.get('called')
        if not isinstance(called,bool) or called!=bool(group):raise ValueError('Media race call/designation mismatch')
        primary,source_refs=refs(d or status);winners=[]
        for designation in group:
            candidate_primary,_=refs(designation)
            if candidate_primary!=primary:raise ValueError('Candidate calls mix source observations')
            when=designation.get('mediaCalledAt',designation.get('callTime'))
            if when and _instant(when)>_instant(primary['retrievedAt']):raise ValueError('Media call is after observation')
            winners.append(dict(name=designation['name'],partyLabel=designation.get('partyLabel'),sourceCandidateId=designation.get('sourceCandidateId'),designationStatus=designation['designationStatus'],sourceProof=designation['sourceProof'],mediaCalledAt=when,publisherCallTimeRaw=designation.get('publisherCallTimeRaw'),publisherOutcomeType=designation['sourceProof'].get('publisherOutcomeType','explicit-media-winner-flag')))
        if group:consumed.add(key)
        winner=winners[0] if len(winners)==1 else None
        calltime=winner['mediaCalledAt'] if winner else None
        source_code=status.get('sourceContestId',status.get('sourceRaceId'))
        row=dict(id='media-race:'+digest([primary['observationId'],status['state'],status['body'],status.get('district'),source_code]),
             electionId='us-2026-general',state=status['state'],body=status['body'],district=status.get('district'),
             sourceContestId=source_code,sourceRaceLabel=status.get('sourceRaceLabel'),
             sourceSeatNumber=status.get('sourceSeatNumber'),sourceSeatLabel=status.get('sourceSeatLabel'),
             sourcePosition=status.get('sourcePosition'),
             sourceElectionType=status.get('sourceElectionType',status.get('publisherRaceType')),
             called=called,outcomeStatus=('partially-called' if status.get('fullyCalled') is False else 'media-called-winner') if called else 'not-called',winner=winner,winners=winners,
             fullyCalled=status.get('fullyCalled'),publisherRaceCallStatus=status.get('publisherRaceCallStatus'),
             publisherNumWinners=status.get('publisherNumWinners'),publisherCensusDistrict=status.get('publisherCensusDistrict'),
             callingOrganization=(d or status).get('callingOrganization'),publisher=(d or status).get('publisher',(d or status).get('carryingOrganization')),
             mediaCalledAt=calltime,publisherCallTimeRaw=d.get('publisherCallTimeRaw') if d else None,
             publisherOutcomeType=d['sourceProof'].get('publisherOutcomeType','explicit-media-winner-flag') if d else None,certificationStatus='not-established',
             observationId=primary['observationId'],observedAt=primary['retrievedAt'],sourceUrl=primary['url'],sourceSha256=primary['sha256'],
             sourceIds=(d or status)['sourceIds'],sourceReferences=source_refs,sourceProof=status.get('sourceProof'),
             identityStatus='Publisher race/candidate identity only; no government person or serving membership join')
        races.append(row)
    additional=[]
    for d in designations:
        if _key(d) in consumed:continue
        primary,source_refs=refs(d);row=dict(d)
        row.update(id='media-designation:'+digest([primary['observationId'],d['state'],d['body'],d.get('sourceCandidateId'),d['sourceProof']]),
                   sourceUrl=primary['url'],sourceSha256=primary['sha256'],sourceReferences=source_refs,
                   linkageStatus='standalone-media-assertion; unresolved across publisher race identities; not merged into canonical race rows')
        additional.append(row)
    npr=[r for r in races if any(k.startswith(('media-federal-npr-','media-state-npr-')) for k in r['sourceIds'])]
    if require_npr_snapshot:
        h=[r for r in npr if r['body']=='us-house'];s=[r for r in npr if r['body']=='us-senate'];g=[r for r in npr if r['body']=='governor']
        if len(h)!=435 or {r['state'] for r in h}!=media_federal.STATES or len(s)!=35 or len(g)!=36:
            raise ValueError('NPR snapshot coverage must be435House across50states,35Senate,36governor')
    races.sort(key=lambda r:(r['state'],r['body'],str(r['district']),str(r['sourceContestId']),r['id']))
    additional.sort(key=lambda r:(r['state'],r['body'],r['name'],r['id']))
    sources_list=sorted(sources.values(),key=lambda s:s['observationId'])
    result=dict(schemaVersion=1,
         electionId='us-2026-general',latestObservedAt=max((s['retrievedAt'] for s in sources_list),key=_instant),
         races=races,additionalDesignations=additional,stateAudits=audits,sourceObservations=sources_list,
         coverage=dict(observedMediaRaces=len(races),calledMediaRaces=sum(r['called'] for r in races),uncalledMediaRaces=sum(not r['called'] for r in races),
                       nprObservedRaces=len(npr),standaloneNamedAssertions=len(additional),
                       mediaWinnerDesignations=sum(len(r['winners']) for r in races),
                       stateLegislativeStates=sorted({r['state'] for r in races if r['body'] in {'state-upper','state-lower'}}),
                       explicitUncontestedWins=sum(w['publisherOutcomeType']=='explicit-publisher-uncontested-win' for r in races for w in r['winners']),
                       byBody=[dict(body=body,observedRaces=sum(r['body']==body for r in races),called=sum(r['body']==body and r['called'] for r in races),uncalled=sum(r['body']==body and not r['called'] for r in races)) for body in sorted({r['body'] for r in races})],
                       positivePublisherOutcomeTypes=dict(sorted(Counter(w['publisherOutcomeType'] for r in races for w in r['winners']).items())),
                       scope='Explicit publisher media calls only; government certification and serving membership remain separate'))
    result['datasetId']='media-results:'+digest(result)
    return result


def collect(store=None,offline=True):
    store=store or MediaEvidenceStore()
    packets=[module.collect(store.acquire,offline) for module in AP_COLLECTORS]
    checked=[state for module in AP_COLLECTORS for state in module.STATES]
    if len(checked)!=50 or set(checked)!=media_federal.STATES:
        raise ValueError('AP state collection partition must cover all 50 states exactly once')
    # Keep the national federal/governor universe once. Direct AP state feeds
    # replace duplicate AP partner observations in the legislative race table.
    packets.append(media_federal.collect(store.acquire,offline))
    governors=media_state.collect(store.acquire,offline)
    governors['designations']=[r for r in governors['designations'] if r['body']=='governor']
    governors['raceStatuses']=[r for r in governors['raceStatuses'] if r['body']=='governor']
    governors['stateAudits']=[r for r in governors['stateAudits'] if r['body']=='governor']
    packets.append(governors)
    # Independent newsroom assertions remain additional observations; matching
    # an AP district or name does not silently merge publication identities.
    for module in [media_additional,media_midwest,media_south]:
        packet=module.collect(store.acquire,offline)
        packet['designations']=[r for r in packet['designations'] if r.get('callingOrganization') not in {'The Associated Press','Associated Press'}]
        packet['raceStatuses']=[]
        packets.append(packet)
    result=combine(packets)
    result['coverage']['stateLegislativeSourceStatesChecked']=sorted(checked)
    result['coverage']['stateLegislativeSourceStatesCheckedCount']=len(checked)
    result['coverage']['partialPublisherCalledRaces']=sum(r['fullyCalled'] is False and r['called'] for r in result['races'])
    result['coverage']['byState']=[dict(state=state,
        observedLegislativeRaces=sum(r['state']==state and r['body'] in {'state-upper','state-lower'} for r in result['races']),
        explicitLegislativeWinnerDesignations=sum(len(r['winners']) for r in result['races'] if r['state']==state and r['body'] in {'state-upper','state-lower'}),
        legislativeRacesWithoutWinnerMarkers=sum(r['state']==state and r['body'] in {'state-upper','state-lower'} and not r['called'] for r in result['races']),
        missingRowsEstablishNoElection=False) for state in sorted(checked)]
    result['datasetId']='media-results:'+digest({k:v for k,v in result.items() if k!='datasetId'})
    return result


def write(result,destination,compressed=False):
    validate_observations(result['sourceObservations'],require_fresh=True)
    payload={k:v for k,v in result.items() if k!='datasetId'}
    if result['datasetId']!='media-results:'+digest(payload):raise ValueError('Assembled media content identity mismatch')
    root=Path(destination);root.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
    previous=root/'results.json'
    if previous.is_file() and previous.read_bytes()!=raw:
        old=previous.read_bytes();old_id=json.loads(old)['datasetId'].split(':')[-1]
        history=root/'history';history.mkdir(exist_ok=True)
        import gzip
        target=history/(old_id+'.json.gz')
        if not target.exists():target.write_bytes(gzip.compress(old,mtime=0))
    json_name='results.json.gz' if compressed else 'results.json'
    if compressed:
        import gzip
        (root/json_name).write_bytes(gzip.compress(raw,mtime=0))
    else:(root/json_name).write_bytes(raw)
    fields=['recordType','state','body','district','sourcePosition','sourceSeatLabel','sourceElectionType','sourceContestId','called','fullyCalled','publisherNumWinners','outcomeStatus','name','partyLabel','sourceCandidateId','callingOrganization','publisher','mediaCalledAt','publisherCallTimeRaw','publisherOutcomeType','observedAt','sourceUrl','sourceSha256','observationId','identityStatus']
    with (root/'results.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for r in result['races']:
            for winner in r['winners'] or [{}]:
                row={key:r.get(key) for key in fields};row.update(recordType='publisher-race',name=winner.get('name'),partyLabel=winner.get('partyLabel'),sourceCandidateId=winner.get('sourceCandidateId'),mediaCalledAt=winner.get('mediaCalledAt'),publisherOutcomeType=winner.get('publisherOutcomeType'),publisherCallTimeRaw=winner.get('publisherCallTimeRaw'));writer.writerow(row)
        for r in result['additionalDesignations']:
            row={key:r.get(key) for key in fields};row.update(recordType='standalone-article-assertion',called=True,outcomeStatus=r['designationStatus'],identityStatus=r['linkageStatus']);writer.writerow(row)
    manifest=dict(schemaVersion=1,datasetId=result['datasetId'],files=[dict(path=name,sha256=hashlib.sha256((root/name).read_bytes()).hexdigest(),bytes=(root/name).stat().st_size) for name in [json_name,'results.csv']],sourceObservationCount=len(result['sourceObservations']),coverage=result['coverage'])
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest
