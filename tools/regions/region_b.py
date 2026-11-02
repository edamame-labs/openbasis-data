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
from urllib.parse import urljoin, urlparse, parse_qs
from build import HTML, Node, has_class, record

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
 'mo-lower': ('Missouri House of Representatives','https://house.mo.gov/listmembers.aspx?year=2026&code=R'),
 'mo-upper': ('Missouri Senate','https://www.senate.mo.gov/Senators'),
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


def match(pattern, text):
    m = re.fullmatch(pattern,text)
    assert m, 'Roster field structure changed: '+text[:150]
    return m


def check(rows, states=None):
    assert rows, 'Empty legislative roster'
    ids = [r['id'] for r in rows]
    assert len(ids)==len(set(ids)), 'Duplicate person identifiers'
    assert all(r['name'] and r.get('district') and 'vacant' not in r['name'].lower() for r in rows)
    # Only use these bounds when parsing a complete, unpaginated source.
    for state,chamber in {(r['state'],r['id'].split('-')[1]) for r in rows}:
        count = sum(r['state']==state and r['id'].split('-')[1]==chamber for r in rows)
        maximum = MAXIMUM[state][1 if chamber in {'upper','unicameral'} else 0]
        assert maximum*.85 <= count <= maximum, ('Unexpected roster size',state,chamber,count,maximum)
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
            rows.append(make(source,state,chamber,m['preferred_full_name'],m['dist'],m['party'],identifier=m['mem_id']))
        source['effectivePeriod']='2025-2026 biennium; independently checked against official bienniumYears endpoint'
        return check(rows)
    if key=='mt-roster':
        # The feed explicitly flags inactive former members and reports term dates.
        today=dt.date.fromisoformat(source['retrievedAt'][:10])
        payload=json.loads(raw)
        assert payload['recordCount']==len(payload['content']) and payload['pageable']['paged'] is False, 'Incomplete Montana roster'
        for m in payload['content']:
            assert m['type']=='LEGISLATOR'
            if m['isActive'] is not True: continue
            assert dt.date.fromisoformat(m['startDate'])<=today<=dt.date.fromisoformat(m['endDate']), 'Active flag/term date conflict'
            c={'House':'lower','Senate':'upper'}[m['chamber']]
            d=match(r'(?:HOUSE|SENATE) DISTRICT (\d+)',m['district'])[1]
            name=' '.join(str(m[x]).strip() for x in ['firstName','middleName','lastName','nameSuffix'] if m.get(x))
            rows.append(make(source,state,c,name,d,m['politicalParty'],m['links']['profileUrl'],m['id']))
        source['effectivePeriod']='Active members with source term dates containing retrieval date'
        return check(rows)
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
            rows.append(make(source,state,c,name,d,m['party'],identifier=pid))
        assert matched=={pid for pid,_,_ in eligible}, 'Current NH House members missing from downloadable file'
        source['effectivePeriod']='House members joined to official current House roster; Senate from current membership download'
        return check(rows)
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
            rows.append(make(source,state,c,name,m['Roster_District'],m['Party'],urljoin(source['url'],m['BioLink']),m['BioLink'].split('/')[2]))
    elif key=='mi-upper':
        tags=tree.find(lambda n:n.tag=='senator-list')
        assert len(tags)==1
        for m in json.loads(tags[0].attrs['senatorinfo']):
            name=' '.join(str(m[x]).strip() for x in ['firstName','middleInitial','lastName','suffix'] if m.get(x))
            rows.append(make(source,state,chamber,name,m['district'],m['party'],identifier=m['id']))
    elif state=='LA':
        for n in tree.find(lambda n:has_class(n,'card-body')):
            names=n.find(lambda n:n.tag=='h1')
            if not names:continue
            name=names[0].text()
            if 'vacant' in name.lower():continue
            d=re.search(r'\bDistrict\s+(\d+)\b',n.text())
            assert d, 'Louisiana district missing'
            a=names[0].find(lambda n:n.tag=='a')
            party=next((p for p in ['Republican','Democrat','Independent','No Party'] if re.search(r'\b'+p+r'\b',n.text())),None)
            rows.append(make(source,state,chamber,reverse_comma(name),d[1],party,urljoin(source['url'],a[0].attrs['href'])))
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
            rows.append(make(source,state,chamber,a[0].text(),d,cells[2].text(),urljoin(source['url'],a[0].attrs['href'])))
    elif key=='me-upper':
        for a in tree.find(lambda n:n.tag=='a' and re.fullmatch(r'/district\d+',n.attrs.get('href',''),re.I)):
            d=re.search(r'\d+$',a.attrs['href'])[0]
            rows.append(make(source,state,chamber,a.text(),d,website=urljoin(source['url'],a.attrs['href'])))
    elif state=='MD':
        for n in tree.find(lambda n:has_class(n,'member-index-cell')):
            a=n.find(lambda n:n.tag=='a' and n.text() and '/Members/Details/' in n.attrs.get('href','') and n.attrs.get('aria-hidden')!='true')
            assert len(a)==1
            m=re.search(r'\bDistrict\s+(\d+[A-Z]?)\b',n.text())
            assert m
            party=next((p for p in ['Democrat','Republican','Independent'] if p in n.text()),None)
            rows.append(make(source,state,chamber,reverse_comma(a[0].text()),m[1],party,urljoin(source['url'],a[0].attrs['href']),a[0].attrs['href'].split('/')[-1]))
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
            rows.append(make(source,state,chamber,cells[2].text()+' '+cells[3].text(),cells[4].text(),cells[5].text(),urljoin(source['url'],links[0].attrs['href']),links[0].attrs['href'].split('/')[-1]))
    elif key=='mi-lower':
        assert 'current term expiring on December 31, 2026' in tree.text()
        source['effectivePeriod']='Current term ending 2026-12-31'
        for a in tree.find(lambda n:n.tag=='a' and has_class(n,'page-search-target')):
            m=match(r'(.+), Rep\. (.+?)\s+\(([^)]+)\) District-(\d+)',a.text())
            rows.append(make(source,state,chamber,m[2]+' '+m[1],m[4],m[3]))
        rows=deduplicate(rows)
    elif key=='mn-lower':
        assert 'House Member Information 2025 - 2026' in tree.text()
        source['effectivePeriod']='2025-2026 biennium'
        alpha=tree.find(lambda n:n.attrs.get('id')=='Alpha')
        assert len(alpha)==1
        for a in alpha[0].find(lambda n:n.tag=='a' and re.fullmatch(r'/members/profile/\d+',n.attrs.get('href','')) and n.text()):
            m=match(r'(.+) \((\d+[AB]), ([^)]+)\)',a.text())
            rows.append(make(source,state,chamber,m[1],m[2],m[3],urljoin(source['url'],a.attrs['href']),a.attrs['href'].split('/')[-1]))
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
            rows.append(make(source,state,chamber,name,n.attrs['data-district'].strip()))
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
            rows.append(make(source,state,chamber,m[1],m[2],website=a.attrs['href'],identifier=parse_qs(urlparse(a.attrs['href']).query)['id'][0]))
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
        for tr in tree.find(lambda n:n.tag=='tr' and has_class(n,'listRow')):
            cells=children(tr,'td')
            assert len(cells)==5
            name=cells[1].attrs['data-order']
            if 'vacant' in name.lower():continue
            district=match(r'No\. (\d+)',cells[3].attrs['data-order'])[1]
            a=cells[1].find(lambda n:n.tag=='a')
            rows.append(make(source,state,chamber,reverse_comma(name),district,cells[2].attrs['data-order'],urljoin(source['url'],a[0].attrs['href'])))
    elif state=='NM':
        for a in tree.find(lambda n:n.tag=='a' and re.fullmatch(r'Legislator\?SponCode=[A-Z]+',n.attrs.get('href',''))):
            m=match(r'(.+) - \(([^)]+)\) District: (\d+)',a.text())
            rows.append(make(source,state,chamber,m[1],m[3],m[2],urljoin(source['url'],a.attrs['href']),parse_qs(urlparse(a.attrs['href']).query)['SponCode'][0]))
    elif key=='ny-lower':
        for n in tree.find(lambda n:n.tag=='h3' and has_class(n,'mem-name')):
            a=n.find(lambda n:n.tag=='a')
            assert len(a)==1
            m=match(r'(.+) District (\d+)',a[0].text())
            rows.append(make(source,state,chamber,m[1],m[2],website=urljoin(source['url'],a[0].attrs['href']),identifier=a[0].attrs['href'].split('/')[-1]))
    elif key=='ny-upper':
        for a in tree.find(lambda n:n.tag=='a' and re.fullmatch(r'https://www.nysenate.gov/senators/[^/]+',n.attrs.get('href',''))):
            m=match(r'(.+) \(([^)]+)\) (\d+)(?:st|nd|rd|th) District',a.text())
            rows.append(make(source,state,chamber,m[1],m[3],m[2],a.attrs['href'],a.attrs['href'].split('/')[-1]))
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
            rows.append(make(source,state,{'Representative':'lower','Senator':'upper'}[c[0].text()],name[0].text(),district[1],party[0].text() if party else None,urljoin(source['url'],a[0].attrs['href']),a[0].attrs['href'].split('/')[-1]))
        assert rows, 'Empty North Dakota page'
        return rows
    else:
        raise ValueError('Unknown region B roster '+key)
    return check(rows)


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
    return check(rows),sources
