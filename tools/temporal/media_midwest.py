"""Explicit original Midwest media outcome statements, never vote-rank calls."""
import datetime as dt
import gzip
import re
from build import HTML
from .media_common import ELECTION_ID,observation,digest

SOURCES={'media-midwest-wpr-legislative-story':('Wisconsin Public Radio','https://www.wpr.org/news/wisconsin-assembly-senate-election-results-2026')}
DELEGATIONS={}
# Exact district/name/outcome clauses published in the original WPR report.
# Positive and passive clauses have different winner directions.
WI_STATEMENTS=[
 ('state-upper','5','Robyn Vining','defeated','before','D'),
 ('state-upper','21','Trevor Jung','defeated','before','Democrat'),
 ('state-lower','21','Daniel Bukiewicz','defeated','before','Democrat'),
 ('state-lower','53','Becky Nichols','defeated','before','Democrat'),
 ('state-lower','51','Ben Gruber','lost to','after','Democratic'),
 ('state-lower','61','Ben Brist','was defeated by','after','Democratic'),
 ('state-lower','88','Brandy Tollefson','was defeated by','after','Democratic'),
 ('state-lower','30','Kevin Knoke','was defeated by','after','Democratic'),
 ('state-lower','85','John Kroll','lost to','after','Democratic'),
 ('state-lower','92','Jeremiah Fredrickson','was defeated by','after','Democratic'),
 ('state-lower','26','Joe Sheehan','defeated','before','D'),
 ('state-lower','89','Ryan Spaude','defeated','before',None),
 ('state-lower','91','Jodi Emerson','defeated','before','D'),
]


def parse_wpr(raw,source):
    if raw.startswith(b'\x1f\x8b'):raw=gzip.decompress(raw)
    root=HTML(raw).root
    titles=root.find(lambda n:n.tag=='h1')
    assert len(titles)==1 and titles[0].text()=='Democrats flip Wisconsin Legislature, setting up single-party control'
    metas={n.attrs.get('property'):n.attrs.get('content') for n in root.find(lambda n:n.tag=='meta')}
    published=metas.get('article:published_time');updated=metas.get('article:modified_time')
    assert published and published.startswith('2026-11-04T'),'Wrong publication election epoch'
    assert dt.datetime.fromisoformat(published)<=dt.datetime.fromisoformat(source['retrievedAt'].replace('Z','+00:00'))
    paragraphs=[n.text() for n in root.find(lambda n:n.tag=='p')]
    designations=[];statuses=[]
    for body,district,name,verb,direction,party in WI_STATEMENTS:
        matches=[(i,text) for i,text in enumerate(paragraphs) if name in text and re.search(r'\b'+district+r'(?:st|nd|rd|th)\b',text)]
        assert len(matches)==1,'Explicit candidate/district clause missing or ambiguous: '+name
        index,text=matches[0]
        # Isolate the specific sentence, because a paragraph may state several races.
        sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z])',text)
        # Abbreviated Rep./Sen. can split the sentence; choose the smallest
        # candidate-containing span retaining its exact outcome verb.
        spans=[part for part in sentences if name in part and verb in part]
        if not spans:spans=[text]
        assert len(spans)==1
        clause=spans[0]
        assert verb in clause and not re.search(r'\b(?:if|could|may|might|would|leading|projected to lose|conceded|claims?)\b',clause,re.I),'Not an explicit outcome clause'
        position=clause.index(name);vp=clause.index(verb)
        assert (position<vp if direction=='before' else position>vp),'Wrong outcome direction'
        if direction=='before':assert 'was defeated by' not in clause and 'lost to' not in clause
        if party:
            assert (re.search(r'\bD-[A-Z]',text) if party=='D' else party in text),'Party field unsupported'
        proof=dict(field='publisherOutcomeVerb',value=verb,selector='article p index '+str(index),
            paragraphSHA256=digest(text.encode()),sourceCandidateName=name,sourceDistrict=district,winnerDirection=direction,
            semantics='Original WPR reporting explicitly states the named candidate defeated an opponent, or an opponent lost to/was defeated by the named candidate. Not a vote calculation.')
        identifier='media-designation:'+digest([observation(source),'WI',body,district,name,proof])
        designations.append(dict(id=identifier,electionId=ELECTION_ID,state='WI',body=body,district=district,name=name,partyLabel=party,
            sourceContestId=None,sourceCandidateId=None,designationStatus='media-called-winner',callingOrganization='Wisconsin Public Radio',carryingOrganization='Wisconsin Public Radio',
            certificationStatus='not-established',personId=None,personLinkStatus='unresolved-official-identifier-required',sourceIds=[source['id']],
            observationId=observation(source),observedAt=source['retrievedAt'],callTime=None,callTimeStatus='not-provided',publisherPublishedAt=published,publisherUpdatedAt=updated,
            sourceProof=proof,limitations='Original media outcome statement only. Publication/update times are not race-call times; no official certification or service inference.'))
        statuses.append(dict(id='media-race:'+digest([observation(source),'WI',body,district]),electionId=ELECTION_ID,state='WI',body=body,district=district,
            sourceRaceId=None,sourceRaceLabel=('Wisconsin Senate District ' if body=='state-upper' else 'Wisconsin Assembly District ')+district,
            status='called',called=True,designationCount=1,electionDate='2026-11-03',specialElection=None,specialElectionStatus='not-provided',
            callingOrganization='Wisconsin Public Radio',sourceIds=[source['id']],observationIds=[observation(source)],sourceProof=proof,missingRowsEstablishNotOnBallot=False))
    return designations,statuses


def collect(fetch,offline=False):
    sources=[];designations=[];races=[];failures={};issues={}
    for key,(publisher,url) in SOURCES.items():
        try:
            raw,source=fetch(key,publisher,url,offline);sources.append(dict(source,observationId=observation(source)))
        except Exception as exc:failures[key]=type(exc).__name__;continue
        try:
            d,r=parse_wpr(raw,source);designations.extend(d);races.extend(r)
        except Exception as exc:issues[key]=type(exc).__name__+': '+str(exc)
    audits=[]
    for state in ['WI','MI','IA','IL','IN','OH']:
        for body in ['state-upper','state-lower']:
            count=sum(d['state']==state and d['body']==body for d in designations)
            audits.append(dict(state=state,body=body,status='partial' if count else 'not-collected',designationCount=count,
                sourceIds=[s['id'] for s in sources] if state=='WI' else [],observationIds=[observation(s) for s in sources] if state=='WI' else [],
                missingRowsEstablishNotOnBallot=False,reason='Selected explicit candidate-level original media outcome statements only; no exhaustive ballot universe or uncalled-race list established.'))
    return dict(designations=designations,raceStatuses=races,stateAudits=audits,sourceObservations=sources,
                coverage=dict(acquisitionFailures=failures,parserFailures=issues,complete=False,uncalledCoverage='not-collected; article is selected outcomes only'))
