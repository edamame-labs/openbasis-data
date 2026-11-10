"""First-party legislative rosters: Louisiana through North Dakota.

Only government publisher responses are inputs. Source snapshots are managed by
build.fetch; display duplicates are reconciled only when every published field agrees.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse, parse_qs
from build import HTML, Node, contact, has_class, party_name, record

SOURCES = {
 'la-lower': ('Louisiana House of Representatives','https://house.louisiana.gov/H_Reps/H_Reps_FullInfo'),
 'la-upper': ('Louisiana State Senate','https://senate.la.gov/Senators_FullInfo.aspx'),
 'me-lower': ('Maine House of Representatives','https://legislature.maine.gov/house/MemberProfiles/List?sort=alpha'),
 'me-upper': ('Maine Senate','https://legislature.maine.gov/senate/senators/9536'),
 'md-lower': ('Maryland General Assembly','https://mgaleg.maryland.gov/mgawebsite/Members/Index/house'),
 'md-upper': ('Maryland General Assembly','https://mgaleg.maryland.gov/mgawebsite/Members/Index/senate'),
 'ma-lower': ('Massachusetts General Court','https://malegislature.gov/Legislators/Members/House'),
 'ma-upper': ('Massachusetts General Court','https://malegislature.gov/Legislators/Members/Senate'),
 'mi-lower': ('Michigan House of Representatives','https://www.house.mi.gov/AllRepresentatives'),
 'mi-upper': ('Michigan Senate','https://senate.michigan.gov/senators/all-senators/'),
 'mn-lower': ('Minnesota House of Representatives','https://www.house.mn.gov/members/list'),
 'mn-upper': ('Minnesota Senate','https://www.mnsenate.gov/api/members'),
 'mn-period': ('Minnesota Senate','https://www.mnsenate.gov/api/bienniumYears'),
 'ms-lower': ('Mississippi Legislature','https://www.legislature.ms.gov/member/?fiscalyear=26&chamber=H'),
 'ms-upper': ('Mississippi Legislature','https://www.legislature.ms.gov/member/?fiscalyear=26&chamber=S'),
 'ms-lower-index': ('Mississippi Legislature','https://billstatus.ls.state.ms.us/members/hr_membs.xml'),
 'ms-upper-index': ('Mississippi Legislature','https://billstatus.ls.state.ms.us/members/ss_membs.xml'),
 'mo-lower': ('Missouri House of Representatives','https://house.mo.gov/listmembers.aspx?year=2026&code=R'),
 'mo-lower-grid': ('Missouri House of Representatives','https://house.mo.gov/MemberGridCluster.aspx?year=2026&code=R'),
 'mo-upper': ('Missouri Senate','https://www.senate.mo.gov/Senators'),
 'mo-upper-directory': ('Missouri Senate','https://www.senate.mo.gov/Senators/SenatorDirectory/'),
 'mt-roster': ('Montana Legislature','https://www.legmt.gov/wp-json/legmt/v1/people/legislators'),
 'ne-unicameral': ('Nebraska Legislature','https://nebraskalegislature.gov/senators/senator_list.php'),
 'nv-lower': ('Nevada Legislature','https://www.leg.state.nv.us/App/Legislator/A/Assembly/Current'),
 'nv-upper': ('Nevada Legislature','https://www.leg.state.nv.us/App/Legislator/A/Senate/Current'),
 'nh-index': ('New Hampshire General Court','https://gc.nh.gov/house/members/'),
 'nh-roster': ('New Hampshire General Court','https://gc.nh.gov/downloads/members.txt'),
 'nj-roster': ('New Jersey Legislature','https://www.njleg.state.nj.us/legislative-roster'),
 'nm-lower': ('New Mexico Legislature','https://www.nmlegis.gov/Members/Legislator_List?T=R'),
 'nm-upper': ('New Mexico Legislature','https://www.nmlegis.gov/Members/Legislator_List?T=S'),
 'ny-lower': ('New York State Assembly','https://nyassembly.gov/mem/'),
 'ny-upper': ('New York State Senate','https://www.nysenate.gov/senators-committees'),
 'nd-roster': ('North Dakota Legislative Assembly','https://ndlegis.gov/assembly/69-2025/special-2/members'),
}
SOURCE_HOSTS = {urlparse(url).hostname for _,url in SOURCES.values()}
NAMES = {'LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','ND':'North Dakota'}
COVERAGE = {st: ({'unicameral':'collected'} if st=='NE' else {'upper':'collected','lower':'collected'}) | {'blockers':[]} for st in NAMES}
MN_SENATE_PHOTOS = 'https://www.mnsenate.gov/img/member_thumbnails/'
MAXIMUM = {'LA':(105,39),'ME':(151,35),'MD':(141,47),'MA':(160,40),'MI':(110,38),'MN':(134,67),'MS':(122,52),'MO':(163,34),'MT':(100,50),'NE':(0,49),'NV':(42,21),'NH':(400,24),'NJ':(80,40),'NM':(70,42),'NY':(150,63),'ND':(94,47)}


def children(n, tag):
    return [x for x in n.children if isinstance(x,Node) and x.tag==tag]


def reverse_comma(name):
    if ',' not in name: return name.strip()
    parts=[p.strip() for p in name.split(',')]
    suffixes={'Jr.','Sr.','II','III','IV','V'}
    suffix=[p for p in parts[1:] if p in suffixes]
    given=[p for p in parts[1:] if p not in suffixes]
    return ' '.join(given+[parts[0]]+suffix)


def make(source, state, chamber, name, district, party=None, website=None, identifier=None):
    body = NAMES[state]+' '+('Legislature' if state=='NE' else 'Senate' if chamber=='upper' else 'General Assembly' if state=='NJ' else 'State Assembly' if state in {'NV','NY'} else 'House of Delegates' if state=='MD' else 'House of Representatives')
    # Person-distinct even in multimember districts; no synthetic seat assignments.
    identity = str(identifier) if identifier else hashlib.sha256((str(district)+'\0'+name).encode()).hexdigest()[:16]
    return record(source,state.lower()+'-'+chamber+'-'+identity,name,state,'state',body,district,party=party,website=website)


# Generic stand-ins published when a member has no portrait.
PLACEHOLDER = re.compile(r'(?i)no_?photo|notavail|default\.png|placeholder|silhouette')


def enrich(row, source, ident=None, email=None, phone=None, photo=None, namespace=None):
    """Copy contact fields and the publisher's person identifier from the record's own source."""
    if photo and PLACEHOLDER.search(photo): photo=None
    row.update(contact(source['url'], email=email, phone=phone, photo=photo))
    if ident: row['ids']={namespace or source['id']:str(ident)}
    return row


def enclosing(tree, outer, inner):
    """Map each inner node to its innermost enclosing outer node (Node has no parent link)."""
    return {id(i):o for o in tree.find(outer) for i in o.find(inner)}


def first(node, predicate, attr=None):
    found=node.find(predicate) if node else []
    return (found[0].attrs.get(attr) if attr else found[0]) if found else None


def mailto(node):
    return first(node, lambda n:n.tag=='a' and n.attrs.get('href','').lower().startswith('mailto:'), 'href')


def img(node):
    return first(node, lambda n:n.tag=='img' and n.attrs.get('src'), 'src')


def match(pattern, text):
    m = re.fullmatch(pattern,text)
    assert m, 'Roster field structure changed: '+text[:150]
    return m


def check(rows, states=None, floor=.85, floors=None):
    assert rows, 'Empty legislative roster'
    ids = [r['id'] for r in rows]
    assert len(ids)==len(set(ids)), 'Duplicate person identifiers'
    assert all(r['name'] and r.get('district') and 'vacant' not in r['name'].lower() for r in rows)
    # Only use these bounds when parsing a complete, unpaginated source.
    for state,chamber in {(r['state'],r['id'].split('-')[1]) for r in rows}:
        count = sum(r['state']==state and r['id'].split('-')[1]==chamber for r in rows)
        maximum = MAXIMUM[state][1 if chamber in {'upper','unicameral'} else 0]
        assert max(1,maximum*(floors or {}).get(state,floor)) <= count <= maximum, ('Unexpected roster size',state,chamber,count,maximum)
        if not (chamber=='lower' and state in {'MD','NJ','NH','ND'}):
            districts=[r['district'] for r in rows if r['state']==state and r['id'].split('-')[1]==chamber]
            assert len(districts)==len(set(districts)), ('Conflicting district occupants',state,chamber)
    return rows


def parse(key, raw, source):
    st, chamber = key.split('-',1)
    state=st.upper()
    rows=[]
    if key=='mn-period':
        assert json.loads(raw)['biennium']=='2025 - 2026', 'Minnesota Senate biennium changed'
        source['effectivePeriod']='2025-2026 biennium'
        return []
    if key=='mn-upper':
        for m in json.loads(raw)['members']:
            # The Senate's memberList script renders portraits as /img/member_thumbnails/ + mem_bio_pic.
            rows.append(enrich(make(source,state,chamber,m['preferred_full_name'],m['dist'],m['party'],identifier=m['mem_id']),source,m['mem_id'],
              email=m.get('email'),phone=m.get('full_phone_number'),photo=m.get('mem_bio_pic') and urljoin(MN_SENATE_PHOTOS,m['mem_bio_pic'])))
        source['effectivePeriod']='2025-2026 biennium; independently checked against official bienniumYears endpoint'
        return check(rows)
    if key=='mt-roster':
        # The feed explicitly flags inactive former members and reports term dates.
        today=dt.date.fromisoformat(source['retrievedAt'][:10])
        payload=json.loads(raw)
        assert payload['recordCount']==len(payload['content']) and payload['pageable']['paged'] is False, 'Incomplete Montana roster'
        future=[]
        for m in payload['content']:
            assert m['type']=='LEGISLATOR'
            if m['isActive'] is not True: continue
            start,end=dt.date.fromisoformat(m['startDate']),dt.date.fromisoformat(m['endDate'])
            assert end>=today, 'Active flag/term date conflict'
            # After a general election the feed reports some sitting legislators only by their next term
            # (MCA 5-2-102: terms begin the first Monday of January). That record does not establish the
            # seat held now, so the person is excluded rather than placed in the future term's seat.
            if start>today:
                assert (m['termOfOffice']['startDate'],m['termOfOffice']['endDate'])==(m['startDate'],m['endDate']), 'Montana term fields disagree'
                future.append(m);continue
            c={'House':'lower','Senate':'upper'}[m['chamber']]
            d=match(r'(?:HOUSE|SENATE) DISTRICT (\d+)',m['district'])[1]
            name=' '.join(str(m[x]).strip() for x in ['firstName','middleName','lastName','nameSuffix'] if m.get(x))
            rows.append(enrich(make(source,state,c,name,d,m['politicalParty'],m['links']['profileUrl'],m['id']),source,m['id'],
              email=m.get('emailAddress'),phone=m.get('phoneNumber'),photo=(m.get('photo') or {}).get('url')))
        source['effectivePeriod']='Active members with source term dates containing retrieval date'
        if future:
            starts=sorted({m['startDate'] for m in future})
            source['excludedEntries']=[{'count':len(future),'termStart':start,'reason':'Active record reports only a term beginning after retrieval; the seat currently held is not reported'} for start in starts]
        # While future-term records displace current ones, only the upper bounds remain structural.
        return check(rows,floor=0 if future else .85)
    if key=='nh-roster':
        data=list(csv.DictReader(io.StringIO(raw.decode('cp1252')),delimiter='\t'))
        assert data and {'LastName','FirstName','LegislativeBody','electedStatus','District','County'} <= set(data[0])
        assert '_currentHouseMembers' in source, 'NH membership eligibility requires official current House index'
        eligible=source.pop('_currentHouseMembers')
        matched=set()
        for m in data:
            c={'S':'upper','H':'lower'}[m['LegislativeBody']]
            pid=None
            if c=='lower':
                norm=lambda text:re.sub(r'[^a-z0-9]','',text.lower())
                matches=[(pid,last,first) for pid,last,first in eligible if norm(last)==norm(m['LastName']) and norm(first).startswith(norm(m['FirstName']))]
                assert len(matches)<=1, 'Ambiguous NH membership identity'
                if not matches:continue
                pid=matches[0][0]
                assert pid not in matched, 'Repeated NH membership identity'
                matched.add(pid)
            name=' '.join(m[x].strip() for x in ['FirstName','MiddleName','LastName'] if m[x].strip())
            # House district numbers repeat between counties; preserve county qualification.
            d=m['District'].strip() if c=='upper' else m['County'].strip()+' '+m['District'].strip()
            row=enrich(make(source,state,c,name,d,m['party'],identifier=pid),source,email=m.get('WorkEmail'),phone=m.get('Phone'))
            if pid: row['ids']={'nh-index':pid}  # Member value from the official current House selection.
            rows.append(row)
        assert matched=={pid for pid,_,_ in eligible}, 'Current NH House members missing from downloadable file'
        source['effectivePeriod']='House members joined to official current House roster; Senate from current membership download'
        return check(rows)
    if key in JOINS or key in MS_INDEX: return []  # Field supplements joined in collect(); never membership.
    tree=HTML(raw).root
    if key=='nh-index':
        assert tree.find(lambda n:n.attrs.get('id')=='pageBody_ddlReps'), 'NH House index missing'
        source['effectivePeriod']='Official current House member selection'
        return []
    elif key=='nj-roster':
        scripts=tree.find(lambda n:n.tag=='script' and n.attrs.get('id')=='__NEXT_DATA__')
        assert len(scripts)==1
        data=json.loads(scripts[0].text())
        assert data['page']=='/legislative-roster'
        groups=data['props']['pageProps']['legrosterData']
        for m in groups[0]:
            if m.get('VacantSort'):continue
            c={'S':'upper','A':'lower'}[m['RosterHouseCode']]
            assert m['BioLink'].startswith('/legislative-roster/')
            name=' '.join(m[x].strip() for x in ['First_Name','Middle_Name','Last_Name','Suffix'] if m.get(x))
            pid=m['BioLink'].split('/')[2]
            rows.append(enrich(make(source,state,c,name,m['Roster_District'],m['Party'],urljoin(source['url'],m['BioLink']),pid),source,pid))
    elif key=='mi-upper':
        tags=tree.find(lambda n:n.tag=='senator-list')
        assert len(tags)==1
        for m in json.loads(tags[0].attrs['senatorinfo']):
            name=' '.join(str(m[x]).strip() for x in ['firstName','middleInitial','lastName','suffix'] if m.get(x))
            rows.append(enrich(make(source,state,chamber,name,m['district'],m['party'],identifier=m['id']),source,m['id'],email=m.get('email'),phone=m.get('phone'),photo=m.get('image')))
    elif state=='LA':
        # Portraits sit in the card around the body; profile IDs are district numbers, not person IDs.
        cards=enclosing(tree,lambda n:has_class(n,'card'),lambda n:has_class(n,'card-body'))
        for n in tree.find(lambda n:has_class(n,'card-body')):
            names=n.find(lambda n:n.tag=='h1')
            if not names:continue
            name=names[0].text()
            if 'vacant' in name.lower():continue
            d=re.search(r'\bDistrict\s+(\d+)\b',n.text())
            assert d, 'Louisiana district missing'
            a=names[0].find(lambda n:n.tag=='a')
            party=next((p for p in ['Republican','Democrat','Independent','No Party'] if re.search(r'\b'+p+r'\b',n.text())),None)
            phone=first(n,lambda n:n.tag=='span' and 'DISTRICTOFFICEPHONE' in n.attrs.get('id',''))
            rows.append(enrich(make(source,state,chamber,reverse_comma(name),d[1],party,urljoin(source['url'],a[0].attrs['href'])),source,
              email=mailto(n),phone=phone.text() if phone else None,photo=img(cards.get(id(n)))))
    elif key=='me-lower':
        for n in tree.find(lambda n:n.tag=='tr'):
            cells=children(n,'td')
            if len(cells)!=8:continue
            if any(word in n.text() for word in [' Resigned',' Deceased']):continue
            a=cells[1].find(lambda n:n.tag=='a' and n.text())
            if not a:continue
            d=cells[3].text()
            # Non-voting tribal representatives have no numbered district; outside this roster scope.
            if not d.isdigit():continue
            if 'vacant' in a[0].text().lower():continue
            href=a[0].attrs['href']
            rows.append(enrich(make(source,state,chamber,a[0].text(),d,cells[2].text(),urljoin(source['url'],href)),source,
              match(r'/house/MemberProfiles/Details/(\d+)',href)[1],email=mailto(cells[5]),photo=img(cells[0])))
    elif key=='me-upper':
        district_link=lambda n:n.tag=='a' and re.fullmatch(r'/district\d+',n.attrs.get('href',''),re.I)
        paragraphs=enclosing(tree,lambda n:n.tag=='p',district_link)
        for a in tree.find(district_link):
            d=re.search(r'\d+$',a.attrs['href'])[0]
            # Each listing line reads "Name (P-County)"; party is the published letter.
            p=paragraphs.get(id(a))
            m=p and len(p.find(district_link))==1 and re.fullmatch(re.escape(a.text())+r' \(([DRI])-[A-Za-z. ]+\)',p.text())
            rows.append(make(source,state,chamber,a.text(),d,m[1] if m else None,urljoin(source['url'],a.attrs['href'])))
    elif state=='MD':
        for n in tree.find(lambda n:has_class(n,'member-index-cell')):
            a=n.find(lambda n:n.tag=='a' and n.text() and '/Members/Details/' in n.attrs.get('href','') and n.attrs.get('aria-hidden')!='true')
            assert len(a)==1
            m=re.search(r'\bDistrict\s+(\d+[A-Z]?)\b',n.text())
            assert m
            party=next((p for p in ['Democrat','Republican','Independent'] if p in n.text()),None)
            pid=a[0].attrs['href'].split('/')[-1]
            rows.append(enrich(make(source,state,chamber,reverse_comma(a[0].text()),m[1],party,urljoin(source['url'],a[0].attrs['href']),pid),source,pid,photo=img(n)))
        # Maryland repeats leadership profiles in the ordinary member directory.
        rows=deduplicate(rows)
    elif state=='MA':
        for tr in tree.find(lambda n:n.tag=='tr'):
            cells=children(tr,'td')
            if not cells:continue
            assert len(cells)==9
            if 'vacant' in (cells[2].text()+' '+cells[3].text()).lower():continue
            links=cells[2].find(lambda n:n.tag=='a')
            assert len(links)==1 and '/Legislators/Profile/' in links[0].attrs['href']
            pid=links[0].attrs['href'].split('/')[-1]
            rows.append(enrich(make(source,state,chamber,cells[2].text()+' '+cells[3].text(),cells[4].text(),cells[5].text(),urljoin(source['url'],links[0].attrs['href']),pid),source,pid,
              email=mailto(cells[8]),phone=cells[7].text(),photo=img(cells[1])))
    elif key=='mi-lower':
        assert 'current term expiring on December 31, 2026' in tree.text()
        source['effectivePeriod']='Current term ending 2026-12-31'
        # Members without a party profile link are listed as a plain <div>.
        target=lambda n:n.tag in {'a','div'} and has_class(n,'page-search-target')
        items=enclosing(tree,lambda n:n.tag=='li' and has_class(n,'page-search-container'),target)
        for a in tree.find(target):
            m=match(r'(.+), Rep\. (.+?)(?:\s+\(([^)]+)\))? District-(\d+)',' '.join(a.text().split()))
            li=items.get(id(a))
            rows.append(enrich(make(source,state,chamber,m[2]+' '+m[1],m[4],m[3]),source,email=mailto(li),
              phone=first(li,lambda n:n.tag=='a' and n.attrs.get('href','').startswith('tel:'),'href')))
        rows=deduplicate(rows)
    elif key=='mn-lower':
        assert 'House Member Information 2025 - 2026' in tree.text()
        source['effectivePeriod']='2025-2026 biennium'
        alpha=tree.find(lambda n:n.attrs.get('id')=='Alpha')
        assert len(alpha)==1
        profile=lambda n:n.tag=='a' and re.fullmatch(r'/members/profile/\d+',n.attrs.get('href','')) and n.text()
        media=enclosing(alpha[0],lambda n:has_class(n,'media'),profile)
        for a in alpha[0].find(profile):
            m=match(r'(.+) \((\d+[AB]), ([^)]+)\)',a.text())
            box=media.get(id(a))
            phones=re.findall(r'\b\d{3}-\d{3}-\d{4}\b',box.text()) if box else []
            pid=a.attrs['href'].split('/')[-1]
            rows.append(enrich(make(source,state,chamber,m[1],m[2],m[3],urljoin(source['url'],a.attrs['href']),pid),source,pid,
              email=mailto(box),phone=phones[0] if len(phones)==1 else None,photo=img(box)))
        rows=deduplicate(rows)
    elif state=='MS':
        assert '2026 Regular Session' in tree.text()
        source['effectivePeriod']='2026 Regular Session; active-member cards only'
        for n in tree.find(lambda n:has_class(n,'active-member')):
            assert n.attrs['data-chamber']==('H' if chamber=='lower' else 'S') and n.attrs['data-fiscal_year']=='26'
            names=n.find(lambda n:has_class(n,'flex-grow-1'))
            assert len(names)==1
            name=names[0].text()
            if chamber=='upper' and int(n.attrs['data-district'])==53:
                assert n.attrs.get('data-customurl')=='https://ltgovhosemann.ms.gov/' and 'President of the Senate' in n.text()
                continue  # Presiding lieutenant governor is not a district senator.
            if 'vacant' in name.lower():continue
            # data-mem_name is the publisher's member key (U_MEM_NAM in its member XML).
            rows.append(enrich(make(source,state,chamber,name,n.attrs['data-district'].strip()),source,n.attrs['data-mem_name'].strip(),photo=img(n)))
        rows=deduplicate(rows)
    elif key=='mo-lower':
        for a in tree.find(lambda n:n.tag=='a' and 'memberdetails.aspx?' in n.attrs.get('href','').lower()):
            q=parse_qs(urlparse(a.attrs['href']).query)
            assert q['year']==['2026'] and q['code']==['R']
            if 'vacant' in a.text().lower():continue
            rows.append(make(source,state,chamber,a.text(),q['district'][0],website=urljoin(source['url'],a.attrs['href'])))
        source['effectivePeriod']='2026 regular-session membership directory'
    elif key=='mo-upper':
        for a in tree.find(lambda n:n.tag=='a' and '/Senators/Member?id=' in n.attrs.get('href','')):
            m=match(r'Senator (.+) District (\d+)',a.text())
            pid=parse_qs(urlparse(a.attrs['href']).query)['id'][0]
            rows.append(enrich(make(source,state,chamber,m[1],m[2],website=a.attrs['href'],identifier=pid),source,pid,photo=img(a)))
    elif state=='NE':
        periods=tree.find(lambda n:n.tag=='select' and n.attrs.get('id')=='Legislature')
        assert len(periods)==1
        options=children(periods[0],'option')
        selected=[n for n in options if 'selected' in n.attrs]
        current=selected[0] if len(selected)==1 else options[0] if not selected else None
        assert current and current.attrs.get('value')=='109' and current.attrs.get('label')=='109th Legislature (2025-2026)', 'Nebraska current legislature changed'
        source['effectivePeriod']='109th Legislature, 2025-2026'
        for n in tree.find(lambda n:has_class(n,'sen-list-item')):
            aa=n.find(lambda n:n.tag=='a')
            assert len(aa)==1
            spans=aa[0].find(lambda n:n.tag=='span')
            assert len(spans)==2
            rows.append(make(source,state,'unicameral',reverse_comma(spans[0].text()),spans[1].text(),website=urljoin(source['url'],aa[0].attrs['href'])))
        rows=deduplicate(rows)
    elif state=='NV':
        assert ('Current Assembly Legislators' if chamber=='lower' else 'Current Senators') in tree.text()
        # Each listRow is followed by a detail row holding room and phone fields.
        details={}
        for body in tree.find(lambda n:n.tag=='tbody'):
            trs=children(body,'tr')
            for tr,nxt in zip(trs,trs[1:]+[None]):
                if has_class(tr,'listRow') and nxt is not None and not has_class(nxt,'listRow'): details[id(tr)]=nxt
        for tr in tree.find(lambda n:n.tag=='tr' and has_class(n,'listRow')):
            cells=children(tr,'td')
            assert len(cells)==5
            name=cells[1].attrs['data-order']
            if 'vacant' in name.lower():continue
            district=match(r'No\. (\d+)',cells[3].attrs['data-order'])[1]
            a=cells[1].find(lambda n:n.tag=='a')
            labels={}
            for div in (details[id(tr)].find(lambda n:n.tag=='div') if id(tr) in details else []):
                names,values=[[x for x in div.find(lambda n:has_class(n,k))] for k in ['fieldName','field']]
                if len(names)==len(values)==1: labels[names[0].text()]=values[0].text()
            phone=labels.get('Carson City Phone:')
            # Profile paths carry the district number, not a person identifier; obfuscated emails are omitted.
            rows.append(enrich(make(source,state,chamber,reverse_comma(name),district,cells[2].attrs['data-order'],urljoin(source['url'],a[0].attrs['href'])),source,
              phone=phone,photo=img(cells[0])))
    elif state=='NM':
        for a in tree.find(lambda n:n.tag=='a' and re.fullmatch(r'Legislator\?SponCode=[A-Z]+',n.attrs.get('href',''))):
            m=match(r'(.+) - \(([^)]+)\) District: (\d+)',a.text())
            pid=parse_qs(urlparse(a.attrs['href']).query)['SponCode'][0]
            rows.append(enrich(make(source,state,chamber,m[1],m[3],m[2],urljoin(source['url'],a.attrs['href']),pid),source,pid,photo=img(a)))
    elif key=='ny-lower':
        heading=lambda n:n.tag=='h3' and has_class(n,'mem-name')
        items=enclosing(tree,lambda n:n.tag=='section' and has_class(n,'mem-item'),heading)
        for n in tree.find(heading):
            a=n.find(lambda n:n.tag=='a')
            assert len(a)==1
            m=match(r'(.+) District (\d+)',a[0].text())
            item=items.get(id(n))
            # Prefer the Albany office line (LOB 12248 / Capitol 12247), not fax or district lines.
            albany=[re.findall(r'\b\d{3}-\d{3}-\d{4}\b',re.sub(r'Fax: ?[\d-]+','',x.text())) for x in (item.find(lambda n:has_class(n,'full-addr')) if item else []) if re.search(r'Albany, NY 1224[78]\b',x.text())]
            pid=a[0].attrs['href'].split('/')[-1]
            rows.append(enrich(make(source,state,chamber,m[1],m[2],website=urljoin(source['url'],a[0].attrs['href']),identifier=pid),source,pid,
              email=mailto(first(item,lambda n:has_class(n,'mem-email'))),phone=albany[0][0] if len(albany)==1 and len(albany[0])==1 else None,
              photo=img(first(item,lambda n:has_class(n,'mem-pic')))))
    elif key=='ny-upper':
        for a in tree.find(lambda n:n.tag=='a' and re.fullmatch(r'https://www.nysenate.gov/senators/[^/]+',n.attrs.get('href',''))):
            m=match(r'(.+) \(([^)]+)\) (\d+)(?:st|nd|rd|th) District',a.text())
            pid=a.attrs['href'].split('/')[-1]
            rows.append(enrich(make(source,state,chamber,m[1],m[3],m[2],a.attrs['href'],pid),source,pid,photo=img(a)))
    elif key.startswith('nd-'):
        assert '69th Legislative Assembly' in tree.text() and 'Special Session - Sep 2026' in tree.text()
        source['effectivePeriod']='69th Legislative Assembly, September 2026 special-session membership'
        for n in tree.find(lambda n:n.tag=='li' and has_class(n,'member-item')):
            name=n.find(lambda n:has_class(n,'member-name'))
            c=n.find(lambda n:has_class(n,'member-chamber'))
            d=n.find(lambda n:has_class(n,'district'))
            assert len(name)==len(c)==len(d)==1
            assert 'Effective' not in n.text(), 'Review dated North Dakota membership transition'
            district=re.search(r'District (\d+[AB]?)\b',d[0].text())
            assert district
            a=n.find(lambda n:n.tag=='a' and n.attrs.get('href','').startswith('/biography/'))
            party=n.find(lambda n:n.tag=='figure' and has_class(n,'hidden'))
            pid=a[0].attrs['href'].split('/')[-1]
            rows.append(enrich(make(source,state,{'Representative':'lower','Senator':'upper'}[c[0].text()],name[0].text(),district[1],party[0].text() if party else None,urljoin(source['url'],a[0].attrs['href']),pid),source,pid,photo=img(a[0]),namespace='nd-roster'))
        assert rows, 'Empty North Dakota page'
        return rows
    else:
        raise ValueError('Unknown region B roster '+key)
    return check(rows)


def mo_lower_grid(raw):
    """House member grid: party and capitol phone by district, with the published name."""
    tables=HTML(raw).root.find(lambda n:n.tag=='table' and n.attrs.get('id')=='theTable')
    assert len(tables)==1, 'Missouri House member grid missing'
    out={}
    for tr in tables[0].find(lambda n:n.tag=='tr'):
        cells=children(tr,'td')
        if not cells:continue
        assert len(cells)==8, 'Missouri House grid columns changed'
        d=str(int(cells[3].text()))
        assert d not in out, 'Repeated Missouri House district'
        out[d]=dict(name=cells[2].text()+' '+cells[1].text(),party=cells[4].text(),phone=cells[6].text())
    return out


def mo_upper_directory(raw):
    """Senator directory cards: party and capitol phone by Senate member id."""
    out={}
    for card in HTML(raw).root.find(lambda n:has_class(n,'card') and any(has_class(c,'card__header--gradient') for c in children(n,'div'))):
        a=card.find(lambda n:n.tag=='a' and re.search(r'/Senators/member\?id=\d+$',n.attrs.get('href',''),re.I))
        if not a:continue  # vacant-district card
        fields={}
        for item in card.find(lambda n:has_class(n,'detail-grid__item')):
            label,value=[item.find(lambda n:has_class(n,k)) for k in ['detail-grid__label','detail-grid__value']]
            fields[label[0].text()]=value[0].text()
        pid=parse_qs(urlparse(a[0].attrs['href']).query)['id'][0]
        assert pid not in out, 'Repeated Missouri Senate id'
        out[pid]=dict(name=a[0].text(),district=match(r'District (\d+)',fields['District'])[1],party=fields.get('Party'),phone=fields.get('Capitol Phone'))
    assert out, 'Missouri Senate directory missing'
    return out


# key -> (roster key, table parser, row join key). A field is joined only when the
# publisher's own id or district matches and the published name is identical.
JOINS = {
 'mo-lower-grid': ('mo-lower', mo_lower_grid, lambda r:r['district']),
 'mo-upper-directory': ('mo-upper', mo_upper_directory, lambda r:r['ids']['mo-upper']),
}


def join(rows, roster, table, key, source):
    for row in rows:
        if row['sources'][0]['id']!=roster:continue
        m=table.get(key(row))
        if not m or m['name']!=row['name'] or m.get('district',row['district'])!=row['district']:continue
        added={'party':m['party']} if m.get('party') and not row.get('party') else {}
        added.update({k:v for k,v in contact(source['url'],phone=m.get('phone')).items() if not row.get(k)})
        if not added:continue
        row.update(added)
        if source not in row['sources']: row['sources'].append(source)
        for field,value in added.items():
            row.setdefault('fieldEvidence',{})[field]={'value':value,'sourceIds':[source['id']]}
    return rows


MS_INDEX = {'ms-lower-index':('lower','house/'),'ms-upper-index':('upper','senate/')}


def ms_member_links(key, raw):
    """Member XML links from an official chamber list; empty slots and external (presiding officer) links are skipped."""
    chamber,prefix=MS_INDEX[key]
    root=ET.fromstring(raw)
    assert root.tag=='LEGISLATURE', 'Mississippi member list changed'
    links=[e.text.strip() for e in root.iter() if e.tag.endswith('_LINK') and e.text and e.text.strip()]
    links=[x for x in links if re.fullmatch(re.escape(prefix)+r'[A-Za-z0-9_().\-]+\.xml',x)]
    # Officer slots repeat a member's link, sometimes with different letter case.
    links=list({x.lower():x for x in reversed(links)}.values())[::-1]
    out=[('ms-'+chamber+'-member-'+re.sub(r'[^a-z0-9]+','-',x[len(prefix):-4].lower()).strip('-'),x) for x in links]
    assert out and len({k for k,_ in out})==len(out), 'Mississippi member links missing or ambiguous'
    return out


def ms_member(raw):
    m=ET.fromstring(raw)
    assert m.tag=='MEMBINFO', 'Mississippi member file changed'
    return {k:(m.findtext(k) or '').strip() for k in ['U_MEM_NAM','DISTRICT','DISP_NAME','PARTY']}


def ms_party(rows, chamber, members):
    """Join member-file party by district plus the publisher key (data-mem_name = U_MEM_NAM) or
    the identical display name. Anything else (stale file for a predecessor, ambiguity) stays empty."""
    for row in rows:
        if row['sources'][0]['id']!='ms-'+chamber or row.get('party'):continue
        key=row['ids']['ms-'+chamber]
        found=[(s,m) for s,m in members if m['DISTRICT']==row['district'] and (m['U_MEM_NAM']==key or m['DISP_NAME']==row['name'])]
        if len(found)!=1 or not found[0][1]['PARTY']:continue
        source,m=found[0]
        row['party']=party_name(m['PARTY'])
        row['sources'].append(source)
        row.setdefault('fieldEvidence',{})['party']={'value':row['party'],'sourceIds':[source['id']]}
    return rows


def deduplicate(rows):
    by_id={}
    for row in rows:
        assert row['id'] not in by_id or by_id[row['id']]==row, 'Conflicting duplicate display profile'
        by_id[row['id']]=row
    return list(by_id.values())


def collect(fetch, offline=False):
    rows,sources=[],[]
    nh_index=None
    for key,(publisher,url) in SOURCES.items():
        raw,source=fetch(key,publisher,url,offline)
        sources.append(source)
        if key=='nh-index':
            tree=HTML(raw).root
            selects=tree.find(lambda n:n.attrs.get('id')=='pageBody_ddlReps')
            assert len(selects)==1
            nh_index=[]
            for option in children(selects[0],'option'):
                pid=option.attrs.get('value','')
                if pid.isdigit() and int(pid)>0:
                    last,first=option.text().split(',',1)
                    nh_index.append((pid,last.strip(),first.strip()))
            assert 340<=len(nh_index)<=400
            nh_proof=source
        if key=='nh-roster':
            assert nh_index
            source['_currentHouseMembers']=nh_index
        parsed=parse(key,raw,source)
        if key=='nh-roster':
            for row in parsed:
                if row['id'].startswith('nh-lower-'):
                    row['sources'].append(nh_proof)
        rows.extend(parsed)
        if key in JOINS:
            roster,parser,field=JOINS[key]
            join(rows,roster,parser(raw),field,source)
        if key in MS_INDEX:
            members=[]
            for child_key,link in ms_member_links(key,raw):
                child,proof=fetch(child_key,publisher,urljoin(url,link),offline)
                sources.append(proof)
                members.append((proof,ms_member(child)))
            ms_party(rows,MS_INDEX[key][0],members)
        if key=='nd-roster':
            tree=HTML(raw).root
            last=tree.find(lambda n:n.tag=='a' and n.attrs.get('title')=='Go to last page')
            assert len(last)==1, 'North Dakota pagination missing'
            end=int(parse_qs(urlparse(last[0].attrs['href']).query)['page'][0])
            assert 1<=end<=12
            for page in range(1,end+1):
                pageurl=urljoin(url,last[0].attrs['href'].split('?')[0])+'?page='+str(page)
                child,proof=fetch('nd-roster-page-'+str(page),publisher,pageurl,offline)
                sources.append(proof)
                rows.extend(parse('nd-page',child,proof))
    # Montana's feed may report future terms only for some sitting members (see parse); keep its upper bounds only.
    return check(rows,floors={'MT':0} if any(s['id']=='mt-roster' and s.get('excludedEntries') for s in sources) else None),sources
