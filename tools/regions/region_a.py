"""Government-published legislative directories for region A; no fallback inputs."""
import concurrent.futures
from collections import Counter
import datetime as dt
import hashlib
import json
import re
from urllib.parse import parse_qs, urljoin, urlencode, urlparse
from build import HTML, Node, contact, has_class, party_name

SOURCES = {
 'az-roster': ('Arizona Legislature', 'https://www.azleg.gov/MemberRoster/'),
 'ar-roster': ('Arkansas General Assembly', 'https://www.arkleg.state.ar.us/Legislators/List'),
 'co-roster': ('Colorado General Assembly', 'https://leg.colorado.gov/legislators'),
 'ct-lower': ('Connecticut General Assembly', 'https://www.cga.ct.gov/asp/menu/hlist.asp'),
 'ct-upper': ('Connecticut General Assembly', 'https://www.cga.ct.gov/asp/menu/slist.asp'),
 'id-lower': ('Idaho Legislature', 'https://legislature.idaho.gov/house/membership/'),
 'id-upper': ('Idaho Legislature', 'https://legislature.idaho.gov/senate/membership/'),
 'ia-lower': ('Iowa General Assembly', 'https://www.legis.iowa.gov/legislators/house'),
 'ia-upper': ('Iowa General Assembly', 'https://www.legis.iowa.gov/legislators/senate'),
 'ky-lower': ('Kentucky General Assembly', 'https://apps.legislature.ky.gov/Legislators/hmembers_county.html'),
 'ky-upper': ('Kentucky General Assembly', 'https://apps.legislature.ky.gov/Legislators/smembers_county.html'),
 'fl-upper': ('Florida Senate', 'https://www.flsenate.gov/Senators'),
 'ks-lower': ('Kansas Legislature', 'https://www.kslegislature.gov/b2025_26/house/representatives/?per_page=all'),
 'ks-upper': ('Kansas Legislature', 'https://www.kslegislature.gov/b2025_26/senate/senators/?per_page=all'),
}
AL_QUERY = '{legislativeMembers(where:{active:{eq:true},elected:{eq:true}}){data{id body fullName district honorificFullNameAffiliation phone email imageUrl}}}'
SOURCES['al-roster'] = ('Alabama Legislature', 'https://alison.legislature.state.al.us/graphql?'+urlencode({'query':AL_QUERY}))
SOURCES['de-lower'] = ('Delaware General Assembly', 'https://legis.delaware.gov/json/House/GetRepresentatives')
SOURCES['de-upper'] = ('Delaware General Assembly', 'https://legis.delaware.gov/json/Senate/GetSenators')
SOURCES['fl-lower'] = ('Florida House of Representatives', 'https://www.flhouse.gov/representatives')
SOURCES['il-lower'] = ('Illinois General Assembly', 'https://www.ilga.gov/House/Members')
SOURCES['il-upper'] = ('Illinois General Assembly', 'https://www.ilga.gov/Senate/Members')
SOURCES['hi-lower'] = ('Hawaii State Legislature', 'https://www.capitol.hawaii.gov/legislature/legislators.aspx?chamber=H')
SOURCES['hi-upper'] = ('Hawaii State Legislature', 'https://www.capitol.hawaii.gov/legislature/legislators.aspx?chamber=S')
SOURCES['ga-lower'] = ('Georgia General Assembly', 'https://www.legis.ga.gov/members/house')
SOURCES['ga-upper'] = ('Georgia General Assembly', 'https://www.legis.ga.gov/members/senate')
SOURCES['in-roster'] = ('Indiana General Assembly', 'https://iga.in.gov/legislative/2026/legislators')
SOURCE_HOSTS = {'www.kslegislature.gov','www.arkleg.state.ar.us'}
# Florida's legislative term; members take office upon election (Fla. Const. art. III, s. 15(d)).
FL_TERM = '2026-2028'
# Party for the Arkansas House: arkleg's list omits it; the House's own member list publishes it.
AUX = {'ar-house-members': ('Arkansas House of Representatives', 'https://www.arkansashouse.org/representatives/members/')}
SOURCES.update(AUX)
SOURCES['ak-upper'] = ('Alaska Legislature', 'https://w3.akleg.gov/senate.php')
SOURCES['ak-lower'] = ('Alaska Legislature', 'https://w3.akleg.gov/house.php')
NAMES = dict(IN='Indiana', HI='Hawaii', GA='Georgia', IL='Illinois', DE='Delaware', AK='Alaska', AL='Alabama', AZ='Arizona', AR='Arkansas', CO='Colorado', CT='Connecticut', ID='Idaho', IA='Iowa', KY='Kentucky', FL='Florida', KS='Kansas')
COVERAGE = {st: {'upper':'not-collected','lower':'not-collected','blockers':[]} for st in 'AL AK AZ AR CO CT DE FL GA HI ID IL IN IA KS KY'.split()}
for st in NAMES:
 COVERAGE[st].update(upper='collected',lower='collected')
COVERAGE['FL']['lower']='collected'
COVERAGE['FL']['blockers']=[]
COVERAGE['AL']['blockers']=[]
COVERAGE['AK']['blockers']=[]
COVERAGE['DE']['blockers']=[]
COVERAGE['GA']['blockers']=[]
COVERAGE['HI']['blockers']=[]
COVERAGE['IL']['blockers']=[]
COVERAGE['IN']['blockers']=['The official 2026 roster contains one additional Senate entry without a district (Andy Zay); that unsupported entry is excluded pending explicit current-office evidence: https://iga.in.gov/legislative/2026/legislators/legislator_andy_zay_1']

# Rosters withheld because the 2026 general election began new terms (Nov. 3-4, 2026) while the official
# directory still lists the previous membership. Publishing it would present departed members as sitting;
# the chamber is reported not collected until the publisher lists the new membership. Key -> (state, chambers, basis).
TERM_BEGUN = {
 'al-roster': ('AL', ['upper','lower'], 'Ala. Const. art. IV, s. 46: legislative terms begin the day after the general election (November 4, 2026). The official directory still lists the members elected in 2022.'),
 'in-roster': ('IN', ['upper','lower'], 'Ind. Const. art. 4, s. 3: terms run from the day after the general election (November 4, 2026). The official directory still reads "Legislators for 2026 Session".'),
 'hi-lower': ('HI', ['lower'], 'Haw. Const. art. III, s. 4: a term begins on the day of the general election (November 3, 2026). The official directory still shows Representatives for the 2026 regular session.'),
 'hi-upper': ('HI', ['upper'], 'Haw. Const. art. III, s. 4: a term begins on the day of the general election (November 3, 2026). The official directory still shows Senators for the 2026 regular session.'),
}
for key,(st,chambers,basis) in TERM_BEGUN.items():
 for ch in chambers:COVERAGE[st][ch]='not-collected'
 COVERAGE[st]['blockers']=COVERAGE[st]['blockers']+[basis+' Withheld source: '+SOURCES[key][1]]


def cells(node):
 return [n for n in node.children if isinstance(n,Node) and n.tag in {'td','th'}]


def normal_name(name):
 name=' '.join(name.split())
 if ',' in name:
  last,first=name.split(',',1)
  return first.strip()+' '+last.strip()
 return name


def query(url, key):
 values=parse_qs(urlparse(url).query).get(key)
 return values[0] if values and len(values)==1 else None


def row(source, st, chamber, name, district, party=None, website=None, pid=None, **details):
 assert name and 'vacant' not in name.lower(), 'Vacant seat is not a person'
 body=NAMES[st]+' '+('Senate' if chamber=='upper' else 'House of Representatives')
 # Person component prevents collisions in Arizona and Idaho multi-member districts.
 district=str(int(district)) if str(district).isdigit() else str(district)
 person=hashlib.sha256(name.encode()).hexdigest()[:12]
 result=dict(id=st.lower()+'-'+chamber+'-'+district+'-'+person,name=name,state=st,level='state',jurisdiction=st,body=body,office=body,district=district,sources=[source])
 if party:result['party']=party
 if website:result['website']=urljoin(source['url'],website)
 if pid:result['ids']={source['id']:str(pid)}
 result.update(details)
 return result


def finish(rows, minimum, maximum):
 assert minimum <= len(rows) <= maximum, 'Roster cardinality outside reviewed structural bounds'
 ids=[r['id'] for r in rows]
 assert len(set(ids))==len(ids),'Duplicate person/district'
 counts=Counter((r['state'],r['body'],r['district']) for r in rows)
 for (st,body,district),count in counts.items():
  assert count <= (2 if st in {'AZ','ID'} and 'House' in body else 1), 'Conflicting current occupants for district'
 return rows


def parse(key,raw,source):
 st=key[:2].upper(); chamber=key.split('-')[1]
 tree=HTML(raw).root; rows=[]
 source['effectivePeriod']='current official directory at retrieval; no publication date supplied'
 if st=='IN':
  assert '2026 (Current)' in tree.text() and 'Legislators for 2026 Session' in tree.text(),'Session changed'
  source['effectivePeriod']='2026 current session directory; district-less entries excluded'
  anchors=tree.find(lambda n:n.tag=='a' and n.attrs.get('href','').startswith('/legislative/2026/legislators/'))
  assert anchors,'Missing legislator cards'
  excluded=[]
  for card in anchors:
   match=re.fullmatch(r'(Rep\.|Sen\.) (.+) \(([RDI])\) District (\d+) (House|Senate)',card.text())
   if not match:
    assert re.fullmatch(r'(Rep\.|Sen\.) .+ \(([RDI])\) (House|Senate)',card.text()),'Unexpected Indiana membership card'
    excluded.append({'sourceLabel':card.text(),'url':urljoin(source['url'],card.attrs['href']),'reason':'Directory entry has no district; current district assignment is unsupported'})
    continue
   ch={'House':'lower','Senate':'upper'}[match.group(5)]
   assert match.group(1)==('Rep.' if ch=='lower' else 'Sen.')
   rows.append(row(source,st,ch,match.group(2),match.group(4),match.group(3),card.attrs['href']))
  if excluded:source['excludedEntries']=excluded
  return finish(rows,135,150)
 if st=='HI':
  assert ('Showing Representatives for the 2026 regular session' if chamber=='lower' else 'Showing Senators for the 2026 regular session') in tree.text(),'Session changed'
  source['effectivePeriod']='2026 regular session; explicit ended terms excluded'
  for card in tree.find(lambda n:has_class(n,'contact-box')):
   titles=card.find(lambda n:has_class(n,'namecard'))
   if not titles:continue
   assert len(titles)==1
   if 'Term of Office Ended:' in card.text():continue
   name=re.fullmatch(r'(.+) \(([RDI])\)',titles[0].text());assert name
   district=re.search(r'(House|Senate) District (\d+) ',card.text());assert district
   assert district.group(1)==('House' if chamber=='lower' else 'Senate')
   links=card.find(lambda n:n.tag=='a' and '/legislature/memberpage.aspx?' in n.attrs.get('href',''));assert len(links)==1
   assert 'year=2026' in links[0].attrs['href']
   rows.append(row(source,st,chamber,normal_name(name.group(1)),district.group(2),name.group(2),links[0].attrs['href']))
  return finish(rows,45 if chamber=='lower' else 22,51 if chamber=='lower' else 25)
 if st=='GA':
  assert '2025-2026 Regular Session (Current)' in tree.text(),'Session changed'
  source['effectivePeriod']='2025-2026 Regular Session (Current)'
  tables=tree.find(lambda n:n.tag=='table' and has_class(n,'memberList'));assert len(tables)==1
  for tr in tables[0].find(lambda n:n.tag=='tr'):
   c=cells(tr)
   if not c or c[0].tag=='th':continue
   assert len(c)==5
   until=re.search(r'\(Until (\d{2}/\d{2}/\d{4})\)',c[1].text())
   observed=dt.datetime.fromisoformat(source['retrievedAt']).date() if source.get('retrievedAt') else dt.datetime.now(dt.timezone.utc).date()
   if until and dt.datetime.strptime(until.group(1),'%m/%d/%Y').date()<observed:continue
   links=c[1].find(lambda n:n.tag=='a' and '/members/' in n.attrs.get('href',''));assert len(links)==1
   rows.append(row(source,st,chamber,re.sub(r'\s*\(Until \d{2}/\d{2}/\d{4}\)','',links[0].text()),c[3].text(),c[2].text(),links[0].attrs['href']))
  return finish(rows,160 if chamber=='lower' else 48,180 if chamber=='lower' else 56)
 if st=='IL':
  assert '104th General Assembly (2025-2026)' in tree.text(),'Assembly changed'
  source['effectivePeriod']='104th General Assembly (2025-2026)'
  current=re.split(rb'<h2[^>]*>Former Members</h2>',raw)
  assert len(current)==2,'Former-member boundary changed'
  cards=HTML(current[0]).root.find(lambda n:has_class(n,'member-card'))
  seen={}
  for card in cards:
   titles=card.find(lambda n:n.tag=='h2' and has_class(n,'card-title'));assert len(titles)==1
   match=re.fullmatch(r'(.+) \(([RDI])\)',titles[0].text());assert match
   label=card.find(lambda n:has_class(n,'card-text'));assert len(label)==1
   district=re.search(r' (\d+)(?:st|nd|rd|th) District$',label[0].text());assert district
   links=titles[0].find(lambda n:n.tag=='a' and '/Members/Details/' in n.attrs.get('href',''));assert len(links)==1
   r=row(source,st,chamber,match.group(1),district.group(1),match.group(2),links[0].attrs['href'])
   if r['id'] in seen:assert seen[r['id']]==r,'Desktop/mobile member disagreement'
   seen[r['id']]=r
  return finish(list(seen.values()),105 if chamber=='lower' else 50,118 if chamber=='lower' else 59)
 if st=='DE':
  data=json.loads(raw);assert not data.get('Errors'), 'Delaware API error'
  assert data['Total']==len(data['Data']), 'Truncated Delaware roster'
  source['effectivePeriod']='current General Assembly official chamber directory'
  for m in data['Data']:
   if m['PersonId'] is None:continue
   assert m['ChamberId']==(2 if chamber=='lower' else 1)
   rows.append(row(source,st,chamber,m['PersonFullName'],m['DistrictNumber'],m['PartyCode'],m['LegislatorDetailLink'],m['PersonId']))
  return finish(rows,35 if chamber=='lower' else 18,41 if chamber=='lower' else 21)
 if st=='AK':
  source['effectivePeriod']='34th Alaska Legislature (2025-2026), current member directory'
  member=lambda n:n.tag=='a' and '/basis/Member/Detail/34?' in n.attrs.get('href','')
  # Blocks view lists the capitol phone; the list view (parsed below) a home-district one.
  phones={}
  for li in tree.find(lambda n:n.tag=='li'):
   kids=[c for c in li.children if isinstance(c,Node)]
   a=[c for c in kids if member(c)];dl=[c for c in kids if c.tag=='dl']
   if len(a)!=1 or len(dl)!=1:continue
   terms=[c for c in dl[0].children if isinstance(c,Node) and c.tag in {'dt','dd'}]
   pairs=dict((terms[i].text(),terms[i+1].text()) for i in range(len(terms)-1) if terms[i].tag=='dt' and terms[i+1].tag=='dd')
   code=query(a[0].attrs['href'],'code');assert code and code not in phones,'Alaska block card changed'
   phones[code]=pairs.get('Phone:')
  for a in tree.find(lambda n:member(n) and 'Phone:' in n.text()):
   names=a.find(lambda n:n.tag=='strong' and has_class(n,'name'));assert len(names)==1
   match=re.search(r'Party: (.+?) District: ([A-T]|\d+) Phone:',a.text());assert match,'Alaska membership card changed'
   code=query(a.attrs['href'],'code');imgs=a.find(lambda n:n.tag=='img')
   rows.append(row(source,st,chamber,names[0].text(),match.group(2),match.group(1),pid=code,**contact(source['url'],phone=phones.get(code),photo=imgs[0].attrs.get('src') if imgs else None)))
  return finish(rows,35 if chamber=='lower' else 18,40 if chamber=='lower' else 20)
 if st=='AL':
  data=json.loads(raw);assert not data.get('errors'), 'Government GraphQL error'
  members=data['data']['legislativeMembers']['data']
  source['effectivePeriod']='active elected legislators from the current official directory'
  for m in members:
   ch={'House':'lower','Senate':'upper'}[m['body']]
   district=re.fullmatch(r'(House|Senate) District (\d+)',m['district']);assert district
   party=re.search(r'\(([RDI])\)$',m['honorificFullNameAffiliation'])
   rows.append(row(source,st,ch,m['fullName'],district.group(2),party.group(1) if party else None,pid=m['id'],**contact(source['url'],email=m.get('email'),phone=m.get('phone'),photo=m.get('imageUrl'))))
  return finish(rows,125,140)
 if st=='AZ':
  assert b'HouseRoster' in raw and b'SenateRoster' in raw
  # The email column publishes the local part; its header states the shared domain.
  assert raw.count(b'<th title="Same suffix for all members">Email @azleg.gov</th>')==2,'Email column changed'
  # Isolate tables: upstream contains an unmatched closing table before these rosters.
  for ch,table in [('lower','HouseRoster'),('upper','SenateRoster')]:
   match=re.search(rb'<table id="'+table.encode()+rb'".*?</table>',raw,re.S)
   assert match,'Missing chamber roster'
   for tr in HTML(match.group()).root.find(lambda n:n.tag=='tr'):
    c=cells(tr)
    if not c or c[0].tag=='th' or c[0].text()=='Legislator':continue
    if has_class(tr,'inactive'):continue
    assert len(c)==6
    a=c[0].find(lambda n:n.tag=='a' and 'href' in n.attrs)
    assert a,'Missing person link'
    name=a[0].text().split(' -- ',1)[0]
    if 'vacant' in name.lower():continue
    imgs=a[0].find(lambda n:n.tag=='img');local=re.fullmatch(r'Email: ([A-Za-z0-9.-]+)',c[3].text())
    rows.append(row(source,st,ch,name,c[1].text(),c[2].text(),a[0].attrs['href'],query(a[0].attrs['href'],'legislator'),**contact(source['url'],email=local and local.group(1)+'@azleg.gov',phone=c[5].text(),photo=imgs[0].attrs.get('src') if imgs else None)))
  return finish(rows,80,90)
 if st=='AR':
  assert '95th General Assembly' in tree.text() and '2026' in tree.text(),'Session changed'
  source['effectivePeriod']='95th General Assembly, 2026 fiscal session'
  for tr in tree.find(lambda n:n.attrs.get('role')=='row' and n.attrs.get('data-fixed')=='true'):
   c={n.attrs['aria-colindex']:n for n in tr.children if isinstance(n,Node) and n.attrs.get('aria-colindex')}
   assert set(c)=={'1','2','3','4'}
   if c['1'].attrs.get('role')=='columnheader':continue
   if re.search(r'\((?:Resigned|Deceased)\)',c['1'].text(),re.I):continue
   a=c['1'].find(lambda n:n.tag=='a' and '/Legislators/Detail?' in n.attrs.get('href',''))
   assert len(a)==1
   ch={'House':'lower','Senate':'upper'}[c['2'].text().replace('Chamber:','').strip()]
   mail=c['1'].find(lambda n:n.tag=='a' and n.attrs.get('href','').startswith('mailto:'))
   rows.append(row(source,st,ch,a[0].text(),c['4'].text().replace('District:','').strip(),website=a[0].attrs['href'],pid=query(a[0].attrs['href'],'member'),**contact(source['url'],email=mail[0].attrs['href'] if len(mail)==1 else None)))
  return finish(rows,125,135)
 if st=='CO':
  assert '2026 Regular Session' in tree.text(),'Session changed'
  source['effectivePeriod']='2026 Regular Session, 75th General Assembly'
  for tr in tree.find(lambda n:n.tag=='tr'):
   c={n.attrs.get('data-label'):n for n in cells(tr)}
   if 'Title' not in c:continue
   assert {'Name','District','Party'}<=set(c)
   if re.search(r'\b(?:resigned|deceased)\b',c['Name'].text(),re.I):continue
   ch={'Senator':'upper','Representative':'lower'}[c['Title'].text()]
   a=c['Name'].find(lambda n:n.tag=='a' and '/legislators/' in n.attrs.get('href',''))
   assert len(a)==1
   mail=c.get('Email') and c['Email'].find(lambda n:n.tag=='a' and n.attrs.get('href','').startswith('mailto:'))
   rows.append(row(source,st,ch,normal_name(a[0].text()),c['District'].text(),c['Party'].text(),a[0].attrs['href'],a[0].attrs['href'].rstrip('/').rsplit('/',1)[1],**contact(source['url'],email=mail[0].attrs['href'] if mail else None,phone=c['Capitol Phone #'].text() if 'Capitol Phone #' in c else None)))
  return finish(rows,90,100)
 if st=='CT':
  assert ('House of Representatives Members' if chamber=='lower' else 'Senate Members') in tree.text()
  for tr in tree.find(lambda n:n.tag=='tr'):
   c=cells(tr)
   if not c or not re.fullmatch(r'S?\d+',c[0].text()):continue
   assert len(c)==5 and c[3].text() in {'R','D','I'},'Roster structure changed'
   if c[1].text().lower()=='vacant':continue
   # Senate name links are mostly caucus contact forms; only mailto links are addresses.
   mail=c[1].find(lambda n:n.tag=='a' and n.attrs.get('href','').startswith('mailto:'))
   rows.append(row(source,st,chamber,normal_name(c[1].text()),c[0].text().removeprefix('S'),c[3].text(),**contact(source['url'],email=mail[0].attrs['href'] if mail else None)))
  return finish(rows,130 if chamber=='lower' else 30,151 if chamber=='lower' else 36)
 if st=='ID':
  assert 'yr=2026' in raw.decode(),'Roster year changed'
  source['effectivePeriod']='2026 membership directory'
  # Portraits sit in a sibling column of the same directory row.
  photos={}
  for div in tree.find(lambda n:has_class(n,'hcode-inner-row')):
   ps=div.find(lambda n:n.tag=='p' and n.find(lambda a:a.tag=='a' and 'yr=2026&district=' in a.attrs.get('href','')))
   imgs=div.find(lambda n:n.tag=='img' and '/directory/' in n.attrs.get('src',''))
   if len(ps)==1 and imgs and len({i.attrs['src'] for i in imgs})==1:photos[id(ps[0])]=imgs[0].attrs['src']
  for p in tree.find(lambda n:n.tag=='p'):
   links=p.find(lambda n:n.tag=='a' and re.search(r'yr=2026&district=\d+',n.attrs.get('href','')))
   if not links:continue
   assert len(links)==1
   names=[n for n in p.children if isinstance(n,Node) and n.tag=='strong']
   assert names
   party=re.search(r'^'+re.escape(names[0].text())+r'\s+\(([RDI])\)',p.text())
   assert party,'Missing party'
   mail=p.find(lambda n:n.tag=='a' and n.attrs.get('href','').startswith('mailto:'))
   office=re.search(r'Statehouse (\(\d{3}\) \d{3}-\d{4})',p.text())
   rows.append(row(source,st,chamber,names[0].text(),links[0].text().replace('District ',''),party.group(1),**contact(source['url'],email=mail[0].attrs['href'] if mail else None,phone=office and office.group(1),photo=photos.get(id(p)))))
  return finish(rows,60 if chamber=='lower' else 30,70 if chamber=='lower' else 35)
 if st=='IA':
  tables=tree.find(lambda n:n.attrs.get('id')=='sortableTable');assert len(tables)==1
  source['effectivePeriod']='91st General Assembly (2025-2026); current table excludes separately listed former members'
  for tr in tables[0].find(lambda n:n.tag=='tr'):
   c=cells(tr)
   if not c or c[0].tag=='th':continue
   assert len(c)==6 and c[0].text()==('House' if chamber=='lower' else 'Senate')
   a=c[1].find(lambda n:n.tag=='a' and 'ga=91&personID=' in n.attrs.get('href',''))
   assert len(a)==1,'Assembly or person link changed'
   assert not re.search(r'\(\d\d/\d\d/\d{4}',a[0].text()),'Former member in current table'
   mail=c[5].find(lambda n:n.tag=='a' and n.attrs.get('href','').startswith('mailto:'))
   rows.append(row(source,st,chamber,a[0].text(),c[2].text(),c[3].text(),a[0].attrs['href'],query(urljoin(source['url'],a[0].attrs['href']),'personID'),**contact(source['url'],email=mail[0].attrs['href'] if mail else None)))
  return finish(rows,85 if chamber=='lower' else 40,100 if chamber=='lower' else 50)
 if st=='KY':
  assert ('House Members - County' if chamber=='lower' else 'Senate Members - County') in tree.text()
  seen={}
  for tr in tree.find(lambda n:n.tag=='tr'):
   c=cells(tr)
   if len(c)!=3:continue
   a=c[1].find(lambda n:n.tag=='a' and 'Legislator-Profile.aspx?DistrictNumber=' in n.attrs.get('href',''))
   if not a:continue
   assert len(a)==1
   # The Senate profile query uses internal IDs101..138, not district numbers.
   label=re.search(r' - (\d+)$',c[0].text())
   assert label,'Missing displayed county/district label'
   district=label.group(1)
   name=normal_name(a[0].text());identity=(district,name)
   imgs=a[0].find(lambda n:n.tag=='img')
   r=row(source,st,chamber,name,district,c[2].text(),a[0].attrs['href'],**contact(source['url'],photo=imgs[0].attrs.get('src') if imgs else None))
   if identity in seen:assert seen[identity]==r,'Conflicting county repeated person'
   seen[identity]=r
  return finish(list(seen.values()),90 if chamber=='lower' else 32,100 if chamber=='lower' else 38)
 if st=='FL' and chamber=='lower':
  # Fla. Const. art. III, s. 15(d): members take office upon election, so the
  # 2026-2028 term began at the November 3, 2026 general election.
  assert 'Representatives for '+FL_TERM.replace('-',' - ') in tree.text(),'Term changed'
  source['effectivePeriod']=FL_TERM+' House term (members take office upon election, Fla. Const. art. III s. 15(d)); current directory section only'
  current=re.split(rb'<h1[^>]*>Representatives for '+FL_TERM.replace('-',' - ').encode()+rb' .*?who served a partial term</h1>',raw)
  # Early in a term the partial-term section is absent; every card's own service dates are then checked.
  assert len(current) in {1,2},'Former-member section boundary changed'
  observed=dt.datetime.fromisoformat(source['retrievedAt']).date() if source.get('retrievedAt') else dt.datetime.now(dt.timezone.utc).date()
  for card in HTML(current[0]).root.find(lambda n:has_class(n,'team-box')):
   if card.text().startswith('Pending Election — District:'):continue
   names=card.find(lambda n:n.tag=='h5');assert len(names)==1
   if names[0].text()=='Pending Election':continue
   links=card.find(lambda n:n.tag=='a' and '/Sections/Representatives/details.aspx?' in n.attrs.get('href',''));assert len(links)==1
   match=re.search(r'(Republican|Democrat|Independent) — District: (\d+)',card.text());assert match
   assert 'Resigned' not in card.text() and 'Deceased' not in card.text()
   served=re.search(r'(\d\d/\d\d/\d\d) - (\d\d/\d\d/\d\d)',card.text())
   if len(current)==1:assert served,'Florida House service dates missing'
   if served:
    start,end=(dt.datetime.strptime(x,'%m/%d/%y').date() for x in served.groups())
    assert start<=observed<=end,'Florida House member service dates exclude retrieval date'
   rows.append(row(source,st,chamber,normal_name(names[0].text()),match.group(2),match.group(1),links[0].attrs['href']))
  return finish(rows,100,120)
 if st=='FL':
  tables=tree.find(lambda n:n.attrs.get('id')=='Senators');assert len(tables)==1
  source['effectivePeriod']=FL_TERM+' Senate (members take office upon election, Fla. Const. art. III s. 15(d)); former senators excluded by directory link structure'
  for tr in tables[0].find(lambda n:n.tag=='tr'):
   c=cells(tr)
   if not c or c[0].text()=='Senator':continue
   assert len(c)==5
   a=c[0].find(lambda n:n.tag=='a' and re.fullmatch(r'/Senators/'+FL_TERM+r'/S\d+',n.attrs.get('href','')))
   # Former senators have an additional person-ID path component.
   if not a:continue
   assert len(a)==1
   if a[0].text()=='Vacant':continue
   imgs=a[0].find(lambda n:n.tag=='img')
   rows.append(row(source,st,'upper',normal_name(a[0].text()),c[1].text(),c[2].text(),a[0].attrs['href'],**contact(source['url'],photo=imgs[0].attrs.get('src') if imgs else None)))
  return finish(rows,30,40)
 if st=='KS':
  assert '/b2025_26/' in source['url']
  source['effectivePeriod']='2025-2026 biennium'
  titles=tree.find(lambda n:has_class(n,'leg-hero-title'))
  badges=tree.find(lambda n:has_class(n,'leg-chamber-badge'))
  parties=tree.find(lambda n:has_class(n,'leg-hero-party'))
  assert len(titles)==len(badges)==len(parties)==1,'Member profile structure changed'
  match=re.fullmatch(r'(House|Senate) — District (\d+), .+',badges[0].text());assert match
  assert match.group(1)==('House' if chamber=='lower' else 'Senate')
  if 'vacant' in titles[0].text().lower():return []
  # Emails are Cloudflare-obfuscated and not decoded; the fallback image is a placeholder.
  photos=tree.find(lambda n:n.tag=='img' and has_class(n,'leg-hero-photo'))
  photo=photos[0].attrs.get('src') if len(photos)==1 and 'fallback' not in photos[0].attrs.get('src','') else None
  cards=[c for c in tree.find(lambda n:has_class(n,'leg-card')) if c.find(lambda n:has_class(n,'leg-card-heading') and n.text()=='Contact & Info')]
  phones=[r for c in cards[:1] for r in c.find(lambda n:has_class(n,'detail-row')) if r.text().startswith('Phone ')]
  r=row(source,st,chamber,titles[0].text(),match.group(2),parties[0].text(),source['url'],**contact(source['url'],phone=phones[0].text().removeprefix('Phone ') if len(phones)==1 else None,photo=photo))
  r['ids']={key:source['url'].rstrip('/').rsplit('/',1)[1]}
  return [r]
 raise ValueError('Unsupported government roster '+key)


def family(name):
 return re.sub(r',?\s+(?:Jr|Sr|II|III|IV)\.?$','',name).split()[-1].lower()


def house_parties(raw):
 """District -> (published name, party) from the Arkansas House member cards."""
 tree=HTML(raw).root;assert 'Members of the 95th General Assembly' in tree.text(),'Assembly changed'
 result={}
 for card in tree.find(lambda n:n.tag=='a' and 'rep-card' in n.attrs.get('class','').split()):
  field=lambda cls:[x.text() for x in card.find(lambda n:has_class(n,cls))]
  name,party,meta=field('rep-card__name'),field('rep-card__party'),field('rep-card__meta')
  district=re.fullmatch(r'District (\d+)',meta[0]) if len(meta)==1 else None
  assert len(name)==1 and district and district.group(1) not in result,'House member card changed'
  # The card's CSS class is not used: some say party-independent beside a Republican label.
  result[district.group(1)]=(name[0],party[0] if len(party)==1 and party[0] in {'Republican','Democrat','Independent'} else None)
 assert 95<=len(result)<=100
 return result


def arkansas_house_party(fetch,offline,rows):
 # Joined by single-member House district; the family name must agree, else party stays empty.
 key,(publisher,url)=next(iter(AUX.items()))
 raw,source=fetch(key,publisher,url,offline)
 source['effectivePeriod']='95th General Assembly current House member list'
 cards=house_parties(raw)
 for r in rows:
  if r['state']!='AR' or 'House' not in r['body'] or r.get('party'):continue
  name,party=cards.get(r['district'],(None,None))
  if not party or family(name)!=family(r['name']):continue
  # Normalized here so the evidence value matches the published field.
  r['party']=party_name(party);r['sources'].append(source)
  r.setdefault('fieldEvidence',{})['party']={'value':r['party'],'sourceIds':[key]}
 return [source]


def senate_party(raw,name):
 """Party from an arkleg member page title, only if it names the same senator."""
 tree=HTML(raw).root;assert '95th General Assembly - Fiscal Session, 2026' in tree.text(),'Session changed'
 titles=tree.find(lambda n:n.tag=='title');assert len(titles)==1,'Member page changed'
 match=re.fullmatch(r'Senator (.+) \(([RDI])\) - Arkansas State Legislature',titles[0].text())
 return party_name(match.group(2)) if match and match.group(1)==name else None


def arkansas_senate_party(fetch,offline,rows):
 # Neither Senate list publishes party; each roster row's own arkleg member link does, in its title.
 senators=[r for r in rows if r['state']=='AR' and 'Senate' in r['body'] and not r.get('party')]
 def page(r):
  member=query(r['website'],'member');assert member and r['website'].startswith('https://www.arkleg.state.ar.us/Legislators/Detail?')
  key='ar-member-'+re.sub(r'[^a-z0-9]+','-',member.lower()).strip('-')
  raw,source=fetch(key,'Arkansas General Assembly',r['website'],offline)
  source['effectivePeriod']='95th General Assembly, 2026 fiscal session member page'
  return r,key,source,senate_party(raw,r['name'])
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(page,senators))
 assert len({key for _,key,_,_ in results})==len(results),'Ambiguous Arkansas member page id'
 for r,key,source,party in results:
  if not party:continue
  r['party']=party;r['sources'].append(source)
  r.setdefault('fieldEvidence',{})['party']={'value':party,'sourceIds':[key]}
 return [source for _,_,source,_ in results]


def collect(fetch,offline=False):
 rows=[]; sources=[]; profiles=[]
 for key,(publisher,url) in SOURCES.items():
  if key in AUX or key in TERM_BEGUN:continue
  if key.startswith('de-'):
   raw,source=fetch(key,publisher,url,offline,method='POST',data='page=1&pageSize=100&sort=DistrictNumber-asc')
  else:raw,source=fetch(key,publisher,url,offline)
  sources.append(source)
  if key.startswith('ks-'):
   tree=HTML(raw).root
   seen_pages={url}; chamber_profiles=[]
   while True:
    trs=tree.find(lambda n:n.tag=='tr' and n.attrs.get('data-href','').startswith('/b2025_26/legislators/'))
    assert trs,'Missing Kansas directory rows'
    for tr in trs:
     path=tr.attrs['data-href'];pid=path.strip('/').split('/')[-1]
     chamber_profiles.append((key+'-'+pid,publisher,urljoin(url,path)))
    nexts=tree.find(lambda n:n.tag=='a' and n.text()=='Next' and 'page=' in n.attrs.get('href',''))
    if not nexts:break
    next_url=urljoin(url,nexts[0].attrs['href']);assert next_url not in seen_pages,'Pagination loop'
    seen_pages.add(next_url)
    page_raw,page_source=fetch(key+'-page-'+str(len(seen_pages)),publisher,next_url,offline)
    sources.append(page_source);tree=HTML(page_raw).root
   assert (110<=len(chamber_profiles)<=125 if key.endswith('lower') else 35<=len(chamber_profiles)<=40)
   profiles.extend(chamber_profiles)
  else:rows.extend(parse(key,raw,source))
 if any(r['state']=='AR' for r in rows):
  # The Arkansas House member list (AUX) returned an access block in November 2026; House party stays empty.
  sources.extend(arkansas_senate_party(fetch,offline,rows))
 def profile(item):
  key,publisher,url=item;raw,source=fetch(key,publisher,url,offline)
  return parse('-'.join(key.split('-')[:2]),raw,source),source
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  for records,source in pool.map(profile,profiles):rows.extend(records);sources.append(source)
 for st,status in COVERAGE.items():
  for ch in ['upper','lower']:
   if status[ch]=='collected':assert any(r['state']==st and ('Senate' in r['body'])==(ch=='upper') for r in rows),'Missing collected chamber'
 finish(rows,1,2500)
 return rows,sources
