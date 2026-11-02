"""Government-published rosters for the western/southern region.

Each parser reads only its publisher's current directory or explicit 2025-26
session. Downloaded contacts and historical entries are deliberately excluded.
"""
import collections
import csv
import hashlib
import io
import json
import re
from urllib.parse import urljoin, urlparse
from build import HTML, Node, has_class

NAMES = dict(OK='Oklahoma', OR='Oregon', RI='Rhode Island', SC='South Carolina',
             SD='South Dakota', TN='Tennessee', TX='Texas', UT='Utah', VT='Vermont',
             VA='Virginia', WA='Washington', WV='West Virginia', WI='Wisconsin', WY='Wyoming')
SOURCES = {
    'ok-lower': ('Oklahoma House of Representatives', 'https://www.okhouse.gov/representatives'),
    'or-upper': ('Oregon Legislative Assembly', 'https://www.oregonlegislature.gov/senate/Documents/senate.csv'),
    'or-lower': ('Oregon Legislative Assembly', 'https://www.oregonlegislature.gov/house/Documents/house.csv'),
    'ri-roster': ('Rhode Island General Assembly', 'https://www.rilegislature.gov/Lists/legislationInformation/AllItems.aspx'),
    'sc-upper': ('South Carolina Legislature', 'https://www.scstatehouse.gov/member.php?chamber=S'),
    'sc-lower': ('South Carolina Legislature', 'https://www.scstatehouse.gov/member.php?chamber=H'),
    'sd-session': ('South Dakota Legislative Research Council', 'https://sdlegislature.gov/api/Sessions'),
    'sd-roster': ('South Dakota Legislative Research Council', 'https://sdlegislature.gov/api/SessionMembers/71.csv'),
    'tn-upper': ('Tennessee General Assembly', 'https://wapp.capitol.tn.gov/apps/LegislatorInfo/Directory?chamber=S&ga=114'),
    'tn-lower': ('Tennessee General Assembly', 'https://wapp.capitol.tn.gov/apps/LegislatorInfo/Directory?chamber=H&ga=114'),
    'tx-upper': ('Texas Senate', 'https://senate.texas.gov/members.php'),
    'tx-lower': ('Texas House of Representatives', 'https://house.texas.gov/members'),
    'ut-roster': ('Utah State Legislature', 'https://le.utah.gov/data/legislators.json'),
    'vt-upper': ('Vermont General Assembly', 'https://legislature.vermont.gov/people/loadAll/2026/Senate'),
    'vt-lower': ('Vermont General Assembly', 'https://legislature.vermont.gov/people/loadAll/2026/House'),
    'va-upper': ('Senate of Virginia', 'https://apps.senate.virginia.gov/Senator/index.php'),
    'va-lower': ('Virginia House of Delegates', 'https://house.vga.virginia.gov/members'),
    'wa-roster': ('Washington State Legislature', 'https://leg.wa.gov/legislators/?chamber=senate'),
    'wv-upper': ('West Virginia Legislature', 'https://www.wvlegislature.gov/Senate1/roster.cfm'),
    'wv-lower': ('West Virginia Legislature', 'https://www.wvlegislature.gov/House/roster.cfm'),
    'wi-upper': ('Wisconsin Legislature', 'https://docs.legis.wisconsin.gov/2025/legislators/senate'),
    'wi-lower': ('Wisconsin Legislature', 'https://docs.legis.wisconsin.gov/2025/legislators/assembly'),
    'wy-upper': ('Wyoming Legislature', 'https://api.wyoleg.gov/v1/Legislator/2026/S'),
    'wy-lower': ('Wyoming Legislature', 'https://api.wyoleg.gov/v1/Legislator/2026/H'),
}
SOURCE_HOSTS = {'www.rilegislature.gov'}
COVERAGE = {s: {'upper':'collected', 'lower':'collected', 'blockers':[]} for s in NAMES}
COVERAGE['OK']['upper'] = 'not-collected'
COVERAGE['OK']['blockers'] = ['https://oksenate.gov/senators and https://www.oksenate.gov/senators return an HTTP 307 JavaScript challenge instead of a roster. No Senate records are imported.']
# Structural bounds are parser guards, not vacancy estimates or completeness claims.
LIMITS = {'OK':(48,101), 'OR':(30,60), 'RI':(38,75), 'SC':(46,124),
          'SD':(35,70), 'TN':(33,99), 'TX':(31,150), 'UT':(29,75),
          'VT':(30,150), 'VA':(40,100), 'WA':(49,98), 'WV':(34,100),
          'WI':(33,99), 'WY':(31,62)}


def clean(text):
    return ' '.join(str(text).split())


def given_first(text):
    """The publisher explicitly formats these names as family, given."""
    text = clean(text)
    if ',' in text:
        family, given = text.split(',',1)
        suffix=re.search(r',\s*(Jr\.?|Sr\.?|II|III|IV)$',given,re.I)
        if suffix:
            return given[:suffix.start()].strip()+' '+family.strip()+', '+suffix.group(1)
        return given.strip()+' '+family.strip()
    return text


def make(source, st, chamber, name, district, person, party=None, website=None):
    assert chamber in {'upper','lower'} and st in NAMES
    name, district = clean(name), clean(district)
    assert name and district and person and not re.search(r'\bvacant\b',name,re.I)
    # Person identifiers are explicit source IDs/links; never district-only IDs.
    suffix = hashlib.sha256(str(person).encode()).hexdigest()[:20]
    body = NAMES[st] + (' State Senate' if chamber=='upper' else ' House of Representatives')
    if st=='WI' and chamber=='lower': body='Wisconsin State Assembly'
    if st=='VA' and chamber=='lower': body='Virginia House of Delegates'
    row = dict(id=st.lower()+'-'+chamber+'-'+suffix, name=name, state=st,
               level='state', jurisdiction=st, body=body, office=body,
               district=district, sources=[source])
    if party: row['party']=clean(party)
    if website:
        website=urljoin(source['url'],website.strip())
        # Keep only profiles hosted by government. Never propagate campaign sites.
        host=urlparse(website).hostname or ''
        if host.endswith('.gov'): row['website']=website
    return row


def checked(rows, st, chamber=None):
    chambers=[chamber] if chamber else ['upper','lower']
    for ch in chambers:
        subset=[r for r in rows if '-'+ch+'-' in r['id']]
        maximum=LIMITS[st][0 if ch=='upper' else 1]
        assert maximum*.8 <= len(subset) <= maximum, (st,ch,'Unexpected roster size',len(subset))
        assert len({r['id'] for r in subset})==len(subset), 'Duplicate person IDs'
        assert len({(r['district'],r['name']) for r in subset})==len(subset), 'Duplicate person/district'
        multimember={('SD','lower'),('VT','upper'),('VT','lower'),('WA','lower'),('WV','upper')}
        if (st,ch) not in multimember:
            assert len({r['district'] for r in subset})==len(subset), 'Conflicting occupants of single-member district'
    return rows


def parse(key, raw, source):
    st=key[:2].upper()
    chamber=key.split('-')[1]
    rows=[]
    if st=='SD':
        if key=='sd-session':
            current=[s for s in json.loads(raw) if s['CurrentSession'] and not s['SpecialSession']]
            assert len(current)==1 and current[0]['SessionId']==71 and current[0]['Year']=='2026', 'Current South Dakota session changed'
            source['effectivePeriod']='2026, One Hundred-First Session'
            return []
        source['effectivePeriod']='2026, One Hundred-First Session (SessionId 71)'
        source['applicabilityReference']=SOURCES['sd-session'][1]
        for m in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
            ch={'S':'upper','H':'lower'}[m['Body']]
            name=' '.join(clean(m[f]) for f in ['FirstName','Initial','LastName'] if clean(m[f]))
            district=m['District'].lstrip('0') or '0'
            rows.append(make(source,st,ch,name,district,'|'.join(m[f] for f in ['Body','District','FirstName','Initial','LastName']),m['Politics']))
    elif st=='UT':
        source['effectivePeriod']='Current legislator directory; 2026GS legislation links'
        for m in json.loads(raw)['legislators']:
            assert 'sess=2026GS' in m['legislation'], 'Utah legislative session changed'
            ch={'S':'upper','H':'lower'}[m['house']]
            rows.append(make(source,st,ch,m['formatName'],m['district'],m['id'],m['party']))
    elif st=='VT':
        source['effectivePeriod']='2025-2026 session'
        for m in json.loads(raw)['data']:
            if m['TerminationReason'].strip(): continue
            assert m['PersonTypeID']==('S' if chamber=='upper' else 'H'), 'Unexpected Vermont chamber'
            name=' '.join(clean(m[f]) for f in ['FirstName','LastName','NameSuffix'] if clean(m[f]))
            rows.append(make(source,st,chamber,name,m['District'],m['PersonID'],m['Party'], '/people/single/2026/'+m['PersonID']))
    elif st=='WY':
        source['effectivePeriod']='2026 legislative roster'
        for m in json.loads(raw):
            assert m['chamber']==('S' if chamber=='upper' else 'H')
            if m['legStatus']!='C': continue
            assert re.fullmatch('[SH][0-9]+',m['district'])
            rows.append(make(source,st,chamber,m['name'],str(int(m['district'][1:])),m['legID'],m['party']))
    elif st=='OR':
        source['effectivePeriod']='Current chamber directory contact CSV'
        for m in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
            if not clean(m['Last Name']):continue
            name=clean(m['First Name'])+' '+clean(m['Last Name'])
            rows.append(make(source,st,chamber,name,m['District Number'],m['Website Address'],website=m['Website Address']))
    else:
        tree=HTML(raw).root
        if st=='OK':
            entries=tree.find(lambda n:n.attrs.get('id')=='__NEXT_DATA__')
            assert len(entries)==1
            page=json.loads(entries[0].text())['props']['pageProps']
            assert page['isCurrent'] and page['selectedLegislature']['current']
            assert page['selectedLegislature']['attributes']['title']=='60th Legislature', 'Oklahoma legislature changed'
            source['effectivePeriod']='60th Legislature; official page isCurrent=true'
            for m in page['members']['legislatureMembers']:
                a=m['attributes']
                if 'vacant' in (a['firstName']+' '+a['lastName']).lower():continue
                district=a['district']['data']['attributes']['number']
                name=' '.join(a[x] for x in ['firstName','lastName','suffix'] if a.get(x))
                rows.append(make(source,st,chamber,name,district,m['id'],a['party']['data']['attributes']['name']))
        elif st=='RI':
            source['effectivePeriod']='Live roster list; ActiveFlag=Yes entries'
            # Anonymous SharePoint list view exposes current and inactive entries.
            # Its explicit ActiveFlag, not mere presence, establishes inclusion.
            headers=[n.attrs['name'] for n in tree.find(lambda n:'displayname' in n.attrs and 'name' in n.attrs)]
            assert len(headers)==17 and 'ActiveFlag' in headers and 'legislator_name' in headers
            for tr in tree.find(lambda n:n.tag=='tr' and 'iid' in n.attrs):
                cells=[n.text() for n in tr.children if isinstance(n,Node) and n.tag=='td']
                assert len(cells)==18
                m=dict(zip(headers,cells[1:]))
                assert m['ActiveFlag'] in {'Yes','No'}, 'Unknown Rhode Island active flag'
                if m['ActiveFlag']!='Yes':continue
                ch={'Senate':'upper','House':'lower'}[m['chamber']]
                rows.append(make(source,st,ch,m['legislator_name'],m['district'],m['ID'],m['political_party'],m['legislator_bioURL']))
            assert tree.find(lambda n:n.tag=='tr'and'iid'in n.attrs), 'Rhode Island list rows missing'
            return rows  # The complete paginated list is checked in collect().
        elif st=='SC':
            assert 'Current Session By Last Name' in tree.text()
            source['effectivePeriod']='Current session member directory'
            for n in tree.find(lambda n:has_class(n,'memberOutline')):
                links=n.find(lambda n:has_class(n,'membername'))
                assert len(links)==1
                a=links[0];name=re.sub(r'^(Senator|Representative)\s+','',a.text())
                if name.lower()=='vacant':continue
                district=re.search(r'District (\d+)',n.text()).group(1)
                party=re.search(r'\(([RD])\)',n.text())
                rows.append(make(source,st,chamber,name,district,a.attrs['href'],party.group(1) if party else None,a.attrs['href']))
        elif st=='TN':
            assert 'ga=114' in raw.decode() and 'ga=115' not in raw.decode(), 'Tennessee session changed'
            source['effectivePeriod']='114th General Assembly (2025-2026)'
            for tr in tree.find(lambda n:n.tag=='tr'):
                links=tr.find(lambda n:n.tag=='a'and'/LegislatorInfo/Member?' in n.attrs.get('href',''))
                if not links:continue
                assert len(links)==1
                a=links[0]
                if 'vacant' in a.text().lower():continue
                cells=[n.text() for n in tr.children if isinstance(n,Node)and n.tag=='td']
                assert len(cells)==7
                district=re.search(r'District (\d+)',tr.text()).group(1)
                rows.append(make(source,st,chamber,given_first(a.text()),district,a.attrs['href'],cells[2],a.attrs['href']))
        elif st=='TX':
            if chamber=='upper':
                assert '89th Legislature' in tree.text(), 'Texas legislative session changed'
                source['effectivePeriod']='89th Legislature (2025-2026)'
                assert '* Indicates a currently vacant seat' in tree.text(), 'Texas vacancy marker changed'
                for n in tree.find(lambda n:has_class(n,'mempicdiv')):
                    links=n.find(lambda n:n.tag=='a'and n.text())
                    assert len(links)==1
                    a=links[0];district=re.search(r'District (\d+)',n.text()).group(1)
                    if a.text().strip().endswith('*'):continue  # vacant seat (e.g. "Constituent Services *")
                    rows.append(make(source,st,chamber,a.text(),district,a.attrs['href'],website=a.attrs['href']))
            else:
                source['effectivePeriod']='Current Texas House members directory; active=1 entries'
                entries=tree.find(lambda n:n.tag=='get-members')
                assert len(entries)==1
                for m in json.loads(entries[0].attrs[':members']):
                    if m['active']!=1:continue
                    rows.append(make(source,st,chamber,given_first(m['member_name']),m['id'],m['member_bill_code'],website=m['link']))
        elif st=='VA':
            source['effectivePeriod']='Current Senate directory' if chamber=='upper' else '2026 Virginia House of Delegates'
            if chamber=='lower':assert 'Members of the 2026 Virginia House of Delegates' in tree.text()
            token='senator-card' if chamber=='upper' else 'delegate-card'
            for n in tree.find(lambda n:has_class(n,token)):
                links=n.find(lambda n:n.tag=='a' and ('memberpage.php?id=' in n.attrs.get('href','') if chamber=='upper' else re.match(r'/members/H\d+',n.attrs.get('href',''))))
                a=next((a for a in links if a.text()!='View Profile'),None)
                assert a is not None
                match=re.search(r'District\s*:?\s*(\d+)',n.text());assert match
                party=re.search(r'Party:\s*(Democrat|Republican|Independent)',n.text())
                rows.append(make(source,st,chamber,given_first(a.text()) if chamber=='lower' else a.text(),match.group(1),a.attrs['href'].strip(),party.group(1) if party else None,a.attrs['href']))
        elif st=='WA':
            assert '2025-26 biennium' in tree.text(), 'Washington biennium changed'
            source['effectivePeriod']='2025-26 biennium; live legislator directory'
            for n in tree.find(lambda n:n.tag=='li'and'data-chamber'in n.attrs):
                ch={'Senate':'upper','House of Representatives':'lower'}[n.attrs['data-chamber']]
                links=n.find(lambda n:n.tag=='a'and has_class(n,'title'))
                assert len(links)==1
                a=links[0];name=re.sub(r'^(Senator|Representative)\s+','',a.text())
                rows.append(make(source,st,ch,name,n.attrs['data-district'],n.attrs['data-id'],n.attrs['data-party'],a.attrs['href']))
        elif st=='WV':
            source['effectivePeriod']='Live chamber roster'
            for tr in tree.find(lambda n:n.tag=='tr'):
                links=tr.find(lambda n:n.tag=='a'and'lawmaker.cfm?member='in n.attrs.get('href','')and n.text())
                if not links:continue
                assert len(links)==1
                cells=[n.text() for n in tr.children if isinstance(n,Node)and n.tag=='td']
                assert len(cells)==6
                a=links[0];district=re.match(r'\d+',cells[2]).group()
                rows.append(make(source,st,chamber,a.text(),str(int(district)),a.attrs['href'],cells[1],a.attrs['href']))
        elif st=='WI':
            assert '2025 Wisconsin State' in tree.text(), 'Wisconsin session changed'
            source['effectivePeriod']='2025-2026 biennium; 2025 legislators directory'
            for n in tree.find(lambda n:re.fullmatch(r'district\d+',n.attrs.get('id','')) is not None):
                named=n.find(lambda n:n.tag=='strong' and n.find(lambda a:a.tag=='a'and a.text()))
                assert named
                name=named[0].text()
                if 'vacant' in name.lower():continue
                details=n.find(lambda a:a.tag=='a'and a.text()=='Details');assert len(details)==1
                party=re.search(r'\(([RD]) -',n.text())
                rows.append(make(source,st,chamber,given_first(name),n.attrs['id'][8:],details[0].attrs['href'],party.group(1) if party else None,details[0].attrs['href']))
        else:raise ValueError('Unsupported source '+key)
    return checked(rows,st,chamber if chamber in {'upper','lower'} else None)


def collect(fetch, offline=False):
    rows,sources=[],[]
    for key,(publisher,url) in SOURCES.items():
        raw,source=fetch(key,publisher,url,offline)
        batch=parse(key,raw,source)
        rows.extend(batch);sources.append(source)
        if key=='ri-roster':
            pages=1;seen={url}
            while True:
                tree=HTML(raw).root
                links=tree.find(lambda a:a.tag=='a'and 'PageFirstRow=' in a.attrs.get('onclick','') and 'p_ID=' in a.attrs.get('onclick',''))
                # SharePoint's next-page arrow has no anchor text. Its first row
                # increases, unlike the optional previous-page link.
                next_urls=[]
                for a in links:
                    m=re.search(r'RefreshPageTo\(event,\s*"([^"]+)"',a.attrs['onclick'])
                    if m:
                        candidate=urljoin(url,m.group(1))
                        first=re.search(r'PageFirstRow=(\d+)',candidate)
                        if first and int(first.group(1))>pages*30:next_urls.append(candidate)
                if not next_urls:break
                assert len(set(next_urls))==1 and pages<40, 'Unexpected Rhode Island pagination'
                url=next_urls[0];assert url not in seen and urlparse(url).path=='/Lists/legislationInformation/AllItems.aspx'
                seen.add(url);pages+=1
                raw,source=fetch('ri-roster-page-'+str(pages),publisher,url,offline)
                rows.extend(parse('ri-roster',raw,source));sources.append(source)
            checked([r for r in rows if r['state']=='RI'],'RI')
    assert len({r['id']for r in rows})==len(rows), 'Duplicate regional official IDs'
    return rows,sources
