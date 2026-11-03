#!/usr/bin/env python3
"""Build an allowlisted government-source snapshot. Python 3.9+, curl."""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import importlib
from functools import partial
import sys
from html.parser import HTMLParser
import html
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import unquote, urlencode, urljoin, urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'house': ('Office of the Clerk, U.S. House of Representatives', 'https://clerk.house.gov/xml/lists/MemberData.xml'),
    'senate': ('United States Senate', 'https://www.senate.gov/general/contact_information/senators_cfm.xml'),
    'ca-upper': ('California State Senate', 'https://www.senate.ca.gov/senators'),
    'ca-lower': ('California State Assembly', 'https://www.assembly.ca.gov/assemblymembers'),
    'nc-upper': ('North Carolina General Assembly', 'https://www.ncleg.gov/Members/MemberTable/S'),
    'nc-lower': ('North Carolina General Assembly', 'https://www.ncleg.gov/Members/MemberTable/H'),
}
CENSUS = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/'
# Excludes DC and territories; identifiers are checked against the Census response.
STATE_CODES = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(key, publisher, url, offline=False, *, method="GET", data=None, browser_snapshots=False):
    cache = ROOT / '.source-cache'
    cache.mkdir(exist_ok=True)
    assert method in {'GET','POST'} and ((method=='GET' and data is None) or (method=='POST' and isinstance(data,str) and data)), 'Unsupported source request'
    request_key = url if method=='GET' else url+'\nPOST\n'+data
    path = cache / (digest(request_key.encode()) + '.json')
    browser_evidence = path.exists() and json.loads(path.read_text()).get('representation')=='browser-dom'
    if not offline and browser_evidence and not browser_snapshots:
        raise RuntimeError('Source requires a fresh browser DOM capture; import evidence and use --browser-snapshots: '+url)
    if offline or (browser_snapshots and browser_evidence):
        item = json.loads(path.read_text())
        raw = (cache / item['file']).read_bytes()
        assert item['url'] == url and item['sha256'] == digest(raw), 'Snapshot checksum mismatch'
        if not offline:
            age=dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(item['retrievedAt'])
            assert dt.timedelta(0)<=age<=dt.timedelta(hours=24), 'Browser observation older than 24 hours; capture it again'
    else:
        command = ['curl', '--fail', '--silent', '--show-error', '--location', '--max-time', '120', '--proto', '=https', '--proto-redir', '=https', '--write-out', '\n%{url_effective}']
        if method=='POST': command.extend(['--request','POST','--data-raw',data])
        result = subprocess.run(command+[url], check=True, capture_output=True)
        raw, final = result.stdout.rsplit(b'\n', 1)
        final_url = final.decode()
        assert urlparse(final_url).hostname.removeprefix('www.') == urlparse(url).hostname.removeprefix('www.'), 'Unexpected publisher redirect'
        file = digest(raw) + '.raw'
        (cache / file).write_bytes(raw)
        item = dict(url=url, retrievedAt=dt.datetime.now(dt.timezone.utc).isoformat(), sha256=digest(raw), file=file, finalUrl=final_url, requestMethod=method, requestBody=data)
        path.write_text(json.dumps(item, indent=2) + '\n')
    return raw, dict(id=key, name=publisher, url=url, retrievedAt=item['retrievedAt'], sha256=item['sha256'], finalUrl=item.get('finalUrl',url), publishedAt=None, representation=item.get('representation','http-response-body'), requestMethod=item.get('requestMethod','GET'), requestBody=item.get('requestBody'), **({'acquisition':item['acquisition']} if 'acquisition' in item else {}))


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ' '.join(' '.join(c.text() if isinstance(c, Node) else c for c in self.children).split())

    def find(self, predicate):
        result = []
        for c in self.children:
            if isinstance(c, Node):
                if predicate(c): result.append(c)
                result.extend(c.find(predicate))
        return result


class HTML(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(raw.decode('utf-8-sig'))

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def has_class(node, token):
    return token in node.attrs.get('class', '').split()


def record(source, id, name, state, level, body, district=None, **extra):
    assert name and state in STATE_CODES
    row = dict(id=id, name=name, state=state, level=level, jurisdiction=state if level == 'state' else 'United States', body=body, office=body, sources=[source])
    if district is not None:
        text = ' '.join(str(district).split())
        assert text, 'Empty district'
        row['district'] = str(int(text)) if text.isdecimal() else text
    row.update({k:v for k,v in extra.items() if v})
    return row


# Contact fields copied from the same official roster as the record (or, with
# fieldEvidence, from another allowlisted official page about that member).
FIELDS = {'id','name','state','level','jurisdiction','body','office','district','party','website','email','phone','photo','ids','sources','fieldEvidence'}
EVIDENCED = {'district','party','website','email','phone','photo'}
EMAIL = re.compile(r'[a-z0-9._%+\'-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}')
PHONE = re.compile(r'\d{3}-\d{3}-\d{4}')


def contact(base_url, email=None, phone=None, photo=None):
    """Normalize contact details from an official page. Unparseable values are omitted, not guessed."""
    out = {}
    if email:
        text = unquote(email.strip()).removeprefix('mailto:').split('?')[0].strip().lower()
        if EMAIL.fullmatch(text): out['email'] = text
    if phone:
        digits = re.sub(r'\D', '', phone.strip().removeprefix('tel:').split('x')[0].split('ext')[0])
        if len(digits) == 11 and digits[0] == '1': digits = digits[1:]
        if len(digits) == 10: out['phone'] = digits[:3]+'-'+digits[3:6]+'-'+digits[6:]
    if photo:
        url = urljoin(base_url, photo.strip())
        if urlparse(url).scheme == 'https': out['photo'] = url
    return out


CSV_COLUMNS = ['id','name','level','state','jurisdiction','body','office','district','party','website','email','phone','photo','ids','sources','fieldEvidence']
JSON_COLUMNS = {'ids','sources','fieldEvidence'}


def drop_shared_contacts(rows):
    """A mailbox or number published for several members of one body is an office line, not theirs."""
    for key, limit in [('email', 1), ('phone', 3)]:
        seen = collections.Counter((r['body'], r[key]) for r in rows if r.get(key))
        for r in rows:
            if r.get(key) and seen[(r['body'], r[key])] > limit:
                del r[key]
                r.get('fieldEvidence', {}).pop(key, None)
        for r in rows:
            if r.get('fieldEvidence') == {}: del r['fieldEvidence']
    return rows


def without_retrieval_times(value):
    if isinstance(value, dict): return {k:without_retrieval_times(v) for k,v in value.items() if k != 'retrievedAt'}
    if isinstance(value, list): return [without_retrieval_times(v) for v in value]
    return value


def keep_unchanged_geography(stage, published):
    """A refetch of identical geometry keeps the published bytes, so refreshes do not rewrite every layer."""
    from geo_io import read_json
    kept = 0
    for path in (stage/'geography').rglob('*'):
        old = published/path.relative_to(stage)
        if path.is_file() and old.is_file() and path.read_bytes() != old.read_bytes() \
                and without_retrieval_times(read_json(path)) == without_retrieval_times(read_json(old)):
            shutil.copyfile(old, path)
            kept += 1
    return kept


# Trailing academic/professional credentials some rosters append ("Jane Doe, Ph.D.").
# Only after the name: leading initials such as "J.D. Ford" are given names.
CREDENTIALS = re.compile(r'(?:,?\s+(?:Ph\.?\s?D|M\.?\s?D|Esq|D\.?D\.?S|Ed\.?\s?D|J\.?D|D\.?V\.?M|Pharm\.?\s?D|CPA|MBA|DNP|RN)\.?)+$')
NOT_A_PERSON = re.compile(r'[*\d<>]|&\w+;|\b(?:vacant|constituent|services|office|district)\b', re.I)


def person_name(name):
    """Normalize a roster's display name; fail closed on text that isn't a person."""
    text = ' '.join(html.unescape(name).split())  # some rosters double-encode entities
    text = CREDENTIALS.sub('', text)
    text = re.sub(r'\b(l{2,3})$', lambda m: 'I'*len(m[1]), text)  # "Bucy lll" typed with lowercase L
    assert text and not NOT_A_PERSON.search(text), 'Not a person name: '+name
    return text


# Unambiguous party abbreviations used by rosters. State-specific codes
# (e.g. "U" is Unenrolled in Maine but Unaffiliated in North Carolina) stay as published.
PARTY_CODES = {'R':'Republican','D':'Democratic','I':'Independent','DEMOCRAT':'Democratic','DFL':'Democratic-Farmer-Labor','WF':'Working Families','C':'Conservative','IP':'Independence'}


def party_name(party):
    """Spell out party abbreviations; fusion lists ("D, WF") and "/" pairs keep their order."""
    if not party: return party
    def one(token):
        token = token.strip()
        return PARTY_CODES.get(token.upper(), token)
    return '/'.join(', '.join(one(t) for t in part.split(',')) for part in party.split('/'))


def parse_federal(key, raw, source):
    root = ET.fromstring(raw)
    rows = []
    if key == 'house':
        source['publishedAt'] = root.attrib.get('publish-date')
        source['congress'] = root.findtext('title-info/congress-num')
        assert source['congress'] == '119', 'Congress changed; review applicability before rebuilding'
        for m in root.findall('members/member'):
            info = m.find('member-info')
            st = info.find('state').attrib['postal-code']
            if st not in STATE_CODES: continue
            bio = info.findtext('bioguideID')
            if not bio: continue  # An absent person is not an inferred vacancy record.
            code = m.findtext('statedistrict')
            rows.append(record(source, 'us-house-'+bio, info.findtext('official-name'), st, 'federal', 'U.S. House', code[2:], party=info.findtext('party'), ids={'bioguide':bio}, **contact(source['url'], phone=info.findtext('phone'))))
    else:
        for m in root.findall('member'):
            st = m.findtext('state')
            if st not in STATE_CODES: continue
            # <email> holds a contact-form URL, not an address.
            website = m.findtext('website')
            rows.append(record(source, 'us-senate-'+m.findtext('bioguide_id'), m.findtext('first_name')+' '+m.findtext('last_name'), st, 'federal', 'U.S. Senate', party=m.findtext('party'), ids={'bioguide':m.findtext('bioguide_id')}, website=website if website and urlparse(website).hostname.endswith('.senate.gov') else None, **contact(source['url'], phone=m.findtext('phone'))))
    assert rows, 'Empty federal roster'
    return rows


def parse_state(key, raw, source):
    tree = HTML(raw).root
    st, chamber = key.split('-')
    body = {'ca-upper':'California State Senate','ca-lower':'California State Assembly','nc-upper':'North Carolina Senate','nc-lower':'North Carolina House of Representatives'}[key]
    rows = []
    if st == 'ca':
        token = 'page-members__member' if chamber == 'upper' else 'members-list__member'
        name_token = 'member__name' if chamber == 'upper' else 'members-list__name'
        for n in tree.find(lambda n: has_class(n, token)):
            names = n.find(lambda n: has_class(n, name_token))
            if not names: raise ValueError('Missing member name')
            name = names[0].text()
            if 'vacant' in name.lower(): continue
            # Assembly source uses "Family, Given"; retain punctuation within each part.
            if chamber == 'lower' and ',' in name:
                last, first = name.split(',', 1)
                name = first.strip()+' '+last.strip()
            district = str(int(n.attrs['data-district']))
            links = n.find(lambda n: n.tag == 'a' and 'href' in n.attrs)
            link = next((n.attrs['href'] for n in links if (n.text() == 'Homepage' if chamber == 'upper' else 'View Details' in n.text())), None)
            imgs = n.find(lambda n: n.tag == 'img')
            photo = (imgs[0].attrs.get('data-src') or imgs[0].attrs.get('src')) if imgs else None
            capitol = n.find(lambda n: has_class(n, '--capitol'))
            phone = re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', capitol[0].text()) if capitol else None
            details = contact(source['url'], phone=phone and phone[0], photo=photo if photo and not photo.startswith('data:') else None)
            rows.append(record(source, key+'-'+district, name, st.upper(), 'state', body, district, party=n.attrs.get('data-party'), website=urljoin(source['url'], link) if link else None, **details))
    else:
        assert '2025-2026 Session' in tree.text(), 'Session label changed'
        source['effectivePeriod'] = '2025-2026 session'
        tables = tree.find(lambda n: n.attrs.get('id') == 'memberTable')
        assert len(tables) == 1, 'Roster table missing'
        for tr in tables[0].find(lambda n: n.tag == 'tr'):
            cells = [n for n in tr.children if isinstance(n, Node) and n.tag == 'td']
            if not cells: continue
            assert len(cells) == 6, 'Roster columns changed'
            # The official session table includes former members, explicitly labeled.
            if '(Resigned ' in cells[4].text() or '(Deceased ' in cells[4].text(): continue
            links = cells[4].find(lambda n: n.tag == 'a' and n.attrs.get('href','').startswith('/Members/Biography/'))
            assert len(links) == 1, 'Missing official biography link'
            district = str(int(cells[1].text()))
            rows.append(record(source, key+'-'+district, links[0].text(), st.upper(), 'state', body, district, party=cells[0].text(), website=urljoin(source['url'], links[0].attrs['href'])))
    # Bounds detect gross selector failure, not a claim of complete occupied seats.
    maximum = {'ca-upper':40,'ca-lower':80,'nc-upper':50,'nc-lower':120}[key]
    assert maximum * .8 <= len(rows) <= maximum, 'Unexpected roster size'
    assert len({r['district'] for r in rows}) == len(rows), 'Duplicate districts'
    return rows


def region_modules():
    # Register this executable as `build` so adapters share the same fetch cache
    # and helpers rather than importing a second copy of the program.
    if __name__ == '__main__':
        sys.modules['build'] = sys.modules[__name__]
    return [importlib.import_module('regions.' + name)
            for name in ['region_a','region_b','region_c','region_d']]


def source_allowed(source):
    url = source['url']
    if urlparse(url).scheme != 'https': return False
    if url.startswith('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/') or url.startswith(CENSUS): return True
    import geography_exceptions
    if url in {url for _,url in geography_exceptions.SOURCES.values()}: return True
    if url in {url for _,url in SOURCES.values()}: return True
    for module in region_modules():
        if url in {url for _,url in module.SOURCES.values()}: return True
        if urlparse(url).hostname in getattr(module, 'SOURCE_HOSTS', set()): return True
    return False


def legislative_chamber(row):
    assert row['level'] == 'state'
    if row['state'] == 'NE': return 'unicameral'
    body = row['body'].lower()
    if 'senate' in body: return 'upper'
    if 'house' in body or 'assembly' in body: return 'lower'
    raise ValueError('Unrecognized legislative body: ' + row['body'])


def legislative_coverage(rows):
    declared = {'CA':{'upper':'collected','lower':'collected','blockers':[]},
                'NC':{'upper':'collected','lower':'collected','blockers':[]}}
    for module in region_modules():
        for st, item in getattr(module, 'COVERAGE', {}).items():
            assert st in STATE_CODES and st not in declared, 'Overlapping regional state ownership'
            declared[st] = item
    for module in region_modules():
        for st, updates in getattr(module, 'COVERAGE_OVERRIDES', {}).items():
            assert st in declared and all(declared[st].get(ch)=='not-collected' for ch in updates if ch!='blockers'), 'Coverage override must only resolve a previously uncollected chamber'
            declared[st] = {**declared[st], **updates}
    observed = collections.Counter((r['state'],legislative_chamber(r)) for r in rows if r['level']=='state')
    result = []
    for st in sorted(STATE_CODES):
        expected = ['unicameral'] if st == 'NE' else ['upper','lower']
        item = declared.get(st, {})
        chambers = {}
        for chamber in expected:
            status = item.get(chamber, 'not-collected')
            assert status in {'collected','not-collected'}, 'Invalid chamber status'
            count = observed[(st,chamber)]
            assert (status == 'collected') == (count > 0), 'Coverage disagrees with parsed rows: '+st+' '+chamber
            chambers[chamber] = dict(status=status, records=count)
        collected = sum(c['status']=='collected' for c in chambers.values())
        result.append(dict(state=st, federal='collected',
            stateLegislature='collected' if collected==len(expected) else 'partial' if collected else 'not-collected',
            legislativeChambers=chambers, blockers=item.get('blockers', []),
            stateExecutive='not-collected', countyOfficials='not-collected'))
    return result


def validate(folder, fresh=False):
    dataset = json.loads((folder/'officials.json').read_text())
    rows = dataset['officials']
    assert rows and len({r['id'] for r in rows}) == len(rows)
    for r in rows:
        assert r['level'] in {'federal','state','county'} and r['state'] in STATE_CODES
        assert r['name'] and r['body'] and r['sources']
        assert len({src['id'] for src in r['sources']}) == len(r['sources']), 'Duplicate record references'
        for src in r['sources']:
            assert source_allowed(src), 'Source is outside the government allowlist'
            assert len(src['sha256']) == 64
        assert set(r) <= FIELDS, sorted(set(r)-FIELDS)
        assert not r.get('email') or EMAIL.fullmatch(r['email']), r['email']
        assert not r.get('phone') or PHONE.fullmatch(r['phone']), r['phone']
        assert not r.get('photo') or urlparse(r['photo']).scheme == 'https', r['photo']
        assert not r.get('ids') or all(isinstance(k,str) and isinstance(v,str) and v for k,v in r['ids'].items())
        for field, proof in r.get('fieldEvidence', {}).items():
            assert field in EVIDENCED, 'Unsupported field evidence: '+field
            assert proof['value']==r.get(field) and proof['sourceIds'] and set(proof['sourceIds'])<={src['id'] for src in r['sources']}
    for name in ['states','counties']:
        geo = json.loads((folder/'geography'/(name+'.geojson')).read_text())
        assert geo['features'] and geo['source']['name'] == 'U.S. Census Bureau'
        ids = [f['properties']['GEOID'] for f in geo['features']]
        assert len(set(ids)) == len(ids)
        assert all(f['geometry']['type'] in {'Polygon','MultiPolygon'} for f in geo['features'])
    assert len(json.loads((folder/'geography/states.geojson').read_text())['features']) == 50
    sources = json.loads((folder/'sources.json').read_text())
    source_index = {s['id']:s for s in sources}
    assert len(source_index) == len(sources), 'Duplicate source IDs'
    assert all(source_allowed(s) or s['url'].startswith(CENSUS) for s in sources), 'Unexpected source publisher'
    for r in rows:
        for src in r['sources']:
            assert src == source_index[src['id']]
    coverage = json.loads((folder/'coverage.json').read_text())
    assert coverage['counts'] == dict(collections.Counter(r['level'] for r in rows))
    assert coverage['states'] == legislative_coverage(rows), 'Coverage does not describe the current rows and adapters'
    with (folder/'officials.csv').open(newline='') as f:
        exported = list(csv.DictReader(f))
    assert [r['id'] for r in exported] == [r['id'] for r in rows]
    for item, r in zip(exported, rows):
        for key, value in item.items():
            assert (json.loads(value) if key in JSON_COLUMNS and value else value) == r.get(key, '')
    if (folder/'geography-report.json').exists():
        from verify_geography import verify as verify_geography
        verify_geography(folder,rows,sources)
    manifest = json.loads((folder/'manifest.json').read_text())
    actual = {str(p.relative_to(folder)):digest(p.read_bytes()) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    assert manifest == actual, 'Published files differ from validated manifest'
    if fresh:
        now = dt.datetime.now(dt.timezone.utc)
        for s in sources:
            for evidence in [s] + ([s['metadata']] if 'metadata' in s else []):
                age = now - dt.datetime.fromisoformat(evidence['retrievedAt'])
                assert dt.timedelta(0) <= age <= dt.timedelta(hours=24), 'Source retrieval older than 24 hours; rebuild online'

    print('Validated', len(rows), 'officials; official-source provenance and unique geography IDs')


def build(offline=False, browser_snapshots=False, require_fresh=False):
    # Import analytical dependencies before downloading anything.
    import district_sources
    import geography_exceptions
    from geography import write as write_geography
    acquire=partial(fetch,browser_snapshots=browser_snapshots)
    stage = Path(tempfile.mkdtemp(prefix='primary-data-', dir=ROOT))
    try:
        sources, rows = [], []
        for key, (publisher, url) in SOURCES.items():
            raw, source = acquire(key, publisher, url, offline)
            rows.extend(parse_federal(key, raw, source) if key in {'house','senate'} else parse_state(key, raw, source))
            sources.append(source)
        for module in region_modules():
            if hasattr(module, 'collect'):
                collected, evidence = module.collect(acquire, offline)
                rows.extend(collected)
                sources.extend(evidence)
            else:
                for key, (publisher, url) in module.SOURCES.items():
                    raw, source = acquire(key, publisher, url, offline)
                    rows.extend(module.parse(key, raw, source))
                    sources.append(source)
        for row in rows:
            row['name']=person_name(row['name'])
            if row.get('party'):
                row['party']=party_name(row['party'])
                if 'party' in row.get('fieldEvidence',{}): row['fieldEvidence']['party']['value']=row['party']
        drop_shared_contacts(rows)
        exception_data,exception_sources=geography_exceptions.collect(acquire,offline)
        rows=geography_exceptions.apply_roster(rows,exception_data)
        sources.extend(exception_sources)
        (stage/'geography').mkdir()
        states = None
        for key, layer, fields in [('states',0,'GEOID,STATE,STUSAB,NAME'), ('counties',1,'GEOID,STATE,COUNTY,NAME')]:
            meta_raw, meta_source = acquire(key+'-metadata','U.S. Census Bureau',CENSUS+str(layer)+'?f=pjson',offline)
            meta = json.loads(meta_raw)
            assert 'January 1, 2026' in meta['description'], 'Geographic vintage changed; review before updating'
            url = CENSUS+str(layer)+'/query?'+urlencode(dict(where='1=1',outFields=fields,outSR='4326',maxAllowableOffset='0.001',f='geojson'))
            raw, source = acquire(key, 'U.S. Census Bureau', url, offline)
            geo = json.loads(raw)
            assert not geo.get('exceededTransferLimit') and 'features' in geo, 'Incomplete Census response'
            if key == 'states':
                geo['features'] = [f for f in geo['features'] if f['properties']['STUSAB'] in STATE_CODES]
                states = {f['properties']['STATE']:f['properties']['STUSAB'] for f in geo['features']}
                assert len(states) == 50
            else:
                geo['features'] = [f for f in geo['features'] if f['properties']['STATE'] in states]
                assert len(geo['features']) > 3000
            source.update(vintage='2026-01-01',metadata=meta_source,description=meta['description'],generalization='Census server maxAllowableOffset=0.001 degrees; display only')
            geo['source'] = source
            (stage/'geography'/(key+'.geojson')).write_text(json.dumps(geo,ensure_ascii=False,separators=(',',':'))+'\n')
            sources.append(source)
        analytical_report,analytical_sources=write_geography(stage,rows,district_sources.iter_collect(acquire,offline),exception_data)
        sources.extend(analytical_sources)
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        rows.sort(key=lambda r:r['id'])
        (stage/'officials.json').write_text(json.dumps(dict(schemaVersion=2,generatedAt=now,officials=rows),ensure_ascii=False,indent=2)+'\n')
        with (stage/'officials.csv').open('w',newline='') as f:
            writer = csv.DictWriter(f,fieldnames=CSV_COLUMNS,lineterminator="\n")
            writer.writeheader()
            writer.writerows({**r, **{k:json.dumps(r[k],ensure_ascii=False) for k in JSON_COLUMNS if r.get(k)}} for r in rows)
        coverage = dict(schemaVersion=2,generatedAt=now,policy='government-primary-only; federal/state/county',counts=dict(collections.Counter(r['level'] for r in rows)),rosters=[dict(source=s['id'],records=sum(any(ref['id']==s['id'] for ref in r['sources']) for r in rows)) for s in sources if any(any(ref['id']==s['id'] for ref in r['sources']) for r in rows)],states=legislative_coverage(rows),geography=dict(states=50,counties=len(geo['features']),vintage='2026-01-01'),limitations=['Official publication is evidence of what the publisher reports; retrieval does not establish an independent factual check.','Roster omission is not classified as a vacancy.','Contact details (email, phone, photo) appear only where an official roster publishes them; mailboxes or numbers shared across members are omitted.','No city/town records, secondary-source records, population estimates or population-weighted overlaps.','County and county-equivalent geography does not establish county governing structures or officeholder districts.'])
        coverage['geography'].update(analyticalDistricts=analytical_report['analyticalCounts'],areaIntersectionPairs=analytical_report['intersectionPairs'],officialGeometryLinks=analytical_report['linkage'])
        (stage/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
        (stage/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
        print('Unchanged geography files kept', keep_unchanged_geography(stage, ROOT/'data'))
        (stage/'manifest.json').write_text(json.dumps({str(p.relative_to(stage)):digest(p.read_bytes()) for p in stage.rglob('*') if p.is_file()},indent=2)+'\n')
        validate(stage, fresh=not offline or require_fresh)
        # Only replace the published tree after every fetch and check succeeds.
        target = ROOT/'data'
        old = ROOT/'.data-previous'
        if old.exists(): shutil.rmtree(old)
        target.rename(old)
        try: stage.rename(target)
        except BaseException:
            old.rename(target)
            raise
        shutil.rmtree(old)
        print(json.dumps(coverage['counts']))
    finally:
        if stage.exists(): shutil.rmtree(stage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Rebuild from checksum-verified raw government snapshots')
    parser.add_argument('--verify',action='store_true',help='Validate published data without networking')
    parser.add_argument('--fresh',action='store_true',help='Require every official source retrieval within 24 hours (not a publication-date guarantee)')
    parser.add_argument('--browser-snapshots',action='store_true',help='Explicitly use imported browser DOM observations within 24 hours while fetching all HTTP sources live')
    args = parser.parse_args()
    validate(ROOT/'data',args.fresh) if args.verify else build(args.offline,args.browser_snapshots,args.fresh)
