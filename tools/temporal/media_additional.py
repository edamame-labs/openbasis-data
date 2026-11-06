"""Explicit named election outcomes reported by an independent newsroom."""
import hashlib
import json
from .media_common import observation
from .media_federal import decode,instant

KEY='media-additional-texas-tribune-legislature'
SOURCES={KEY:('The Texas Tribune','https://www.texastribune.org/2026/11/03/texas-house-legislature-outcomes-control-republicans-democrats-2026/')}
DELEGATIONS={}
# Exact article assertions; unnamed losses, concessions, leads and party-control
# statements do not identify a winning candidate and are deliberately excluded.
ASSERTIONS=[
 ('Kristian Carranza','state-lower','Democrat','Carranza flipped a seat'),
 ('Mark Dorazio','state-lower',None,'Mark Dorazio won reelection'),
 ('Mano DeAyala','state-lower',None,'as did Houston Rep. Mano DeAyala'),
 ('Morgan Meyer','state-lower',None,'Morgan Meyer won'),
 ('Taylor Rehmet','state-upper','Democrat','Rehmet won a full four-year term'),
]


def parse_article(raw,source):
 from build import HTML
 root=HTML(decode(raw).encode()).root
 assert source['url']==SOURCES[KEY][1],'Unexpected article URL'
 schemas=[]
 for node in root.find(lambda n:n.tag=='script' and n.attrs.get('type')=='application/ld+json'):
  obj=json.loads(node.text());schemas.extend(obj.get('@graph',[obj]))
 articles=[x for x in schemas if x.get('@type') in {'NewsArticle','Article'}]
 assert articles and len({instant(x['datePublished']) for x in articles})==1,'Conflicting article metadata'
 metadata=articles[0]
 assert metadata['datePublished'][:10] in {'2026-11-03','2026-11-04'},'Wrong election publication'
 assert 'Texas House' in metadata['headline'],'Unexpected article context'
 article_nodes=root.find(lambda n:n.tag=='article')
 assert article_nodes,'Missing article body'
 paragraphs=article_nodes[0].find(lambda n:n.tag=='p')
 output=[]
 for name,body,party,fragment in ASSERTIONS:
  matches=[(i,p.text()) for i,p in enumerate(paragraphs) if fragment in p.text() and name in p.text()]
  assert len(matches)==1,'Explicit named outcome assertion changed: '+name
  index,text=matches[0]
  if name=='Mano DeAyala':assert 'won reelection' in text,'Missing grammatical outcome context'
  output.append(dict(state='TX',body=body,district=None,sourceContestId=None,sourceCandidateId=None,
   name=name,partyLabel=party,designationStatus='media-called-winner',callingOrganization='The Texas Tribune',
   publisher='The Texas Tribune',publisherAttribution='Direct named outcome statement in newsroom election reporting',
   certificationStatus='not-established',sourceIds=[source['id']],observationId=observation(source),
   observedAt=source['retrievedAt'],mediaCalledAt=None,mediaCallTimeStatus='not-provided',
   publisherPublishedAt=metadata['datePublished'],publisherModifiedAt=metadata.get('dateModified'),
   sourceProof=dict(selector=f'article p (paragraph index {index})',field='explicit named election outcome statement',
    value=fragment,paragraphSha256=hashlib.sha256(text.encode()).hexdigest()),
   identityStatus='Named media subject only; district and government identity unresolved',
   scopeLimitations='Article assertion only. District, source candidate ID, call time, certification and service are not inferred.'))
 return output


def collect(fetch,offline=False):
 observations=[];designations=[];failures={}
 for key,(publisher,url) in SOURCES.items():
  try:
   raw,s=fetch(key,publisher,url,offline);observations.append(dict(s,observationId=observation(s)))
   designations.extend(parse_article(raw,s))
  except Exception as exc:failures[key]=str(exc)
 return dict(designations=designations,sourceObservations=observations,stateAudits=[dict(state='TX',
  status='checked' if designations else 'access-blocked',explicitMediaCallCount=len(designations),
  sourceIds=[s['id'] for s in observations],observationIds=[s['observationId'] for s in observations],
  scope='Five named article assertions only; not statewide or chamber-complete',validationErrors=failures)])
