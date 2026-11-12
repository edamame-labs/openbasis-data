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
import time
import unicodedata
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
# Postal codes of the District of Columbia and the territories with a non-voting House member.
TERRITORIES = {'DC','PR','GU','VI','AS','MP'}
# Second House sources: the house.gov directory (room-code key and member websites)
# and each member's Clerk page (photo, and the office address it states).
HOUSE_DIRECTORY = ('U.S. House of Representatives', 'https://www.house.gov/representatives')
CLERK_MEMBER = 'https://clerk.house.gov/members/'
CLERK_MEMBER_URL = re.compile(r'https://clerk\.house\.gov/members/[A-Z]\d{6}')
USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'
# curl exit codes for transport failures worth one retry: could not resolve host (6),
# could not connect (7), timeout (28), TLS handshake (35), empty reply (52), receive error (56).
# HTTP errors (--fail, exit 22) are answers from the publisher and are never retried.
TRANSIENT_CURL = {6, 7, 28, 35, 52, 56}
RETRY_DELAY = 5


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run_curl(command):
    """Run curl, retrying once after RETRY_DELAY seconds on a transient transport error."""
    try:
        return subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        if error.returncode not in TRANSIENT_CURL: raise
    time.sleep(RETRY_DELAY)
    return subprocess.run(command, check=True, capture_output=True)


def fetch(key, publisher, url, offline=False, *, method="GET", data=None, browser_snapshots=False, user_agent=None):
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
        if user_agent: command.extend(['--user-agent',user_agent])
        if method=='POST': command.extend(['--request','POST','--data-raw',data])
        result = run_curl(command+[url])
        raw, final = result.stdout.rsplit(b'\n', 1)
        final_url = final.decode()
        assert urlparse(final_url).hostname.removeprefix('www.') == urlparse(url).hostname.removeprefix('www.'), 'Unexpected publisher redirect'
        file = digest(raw) + '.raw'
        (cache / file).write_bytes(raw)
        item = dict(url=url, retrievedAt=dt.datetime.now(dt.timezone.utc).isoformat(), sha256=digest(raw), file=file, finalUrl=final_url, requestMethod=method, requestBody=data)
        if user_agent:item['acquisition']=dict(method='http-get' if method=='GET' else 'http-post',requestHeaders={'User-Agent':user_agent})
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
FIELDS = {'id','name','state','level','jurisdiction','body','office','district','party','website','email','phone','address','photo','ids','sources','fieldEvidence'}
EVIDENCED = {'district','party','website','email','phone','address','photo'}
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


CSV_COLUMNS = ['id','name','level','state','jurisdiction','body','office','district','party','website','email','phone','address','photo','ids','sources','fieldEvidence']
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


def folded(text):
    """Letters only, without accents or case, to compare one person's name across two official lists."""
    text = unicodedata.normalize('NFKD', text)
    return re.sub(r'[^a-z]', '', ''.join(c for c in text if not unicodedata.combining(c)).casefold())


def same_member(a, b):
    """Two 'Family, Given' names agree: the same family name and the same first given name."""
    parts = [n.split(',') for n in (a, b)]
    assert all(len(p) == 2 and p[0].strip() and p[1].split() for p in parts), ('Expected "Family, Given" names', a, b)
    (fa, ga), (fb, gb) = parts
    return folded(fa) == folded(fb) and folded(ga.split()[0]) == folded(gb.split()[0])


DIRECTORY_COLUMNS = ['District', 'Name', 'Party', 'Office Room', 'Phone', 'Committee Assignment']


def parse_house_directory(raw, expected_tables=len(STATE_CODES) + len(TERRITORIES), size=(400, 441)):
    """Room-code key {code: building} and seats {(state name, district label): ('Family, Given', website)} from house.gov."""
    tree = HTML(raw).root
    boxes = [n for n in tree.find(lambda n: n.tag == 'div')
             if any(isinstance(c, Node) and c.tag == 'h2' and c.text() == 'Key to Room Codes' for c in n.children)]
    assert len(boxes) == 1, 'Room-code key missing'
    buildings = {}
    for li in boxes[0].find(lambda n: n.tag == 'li'):
        match = re.fullmatch(r'([A-Z]{2,5}): ([A-Z][a-z]+ House Office Building)', li.text())
        if match:
            assert match[1] not in buildings, 'Duplicate room code: '+match[1]
            buildings[match[1]] = match[2]
    assert len(buildings) >= 3, 'Room-code key changed'
    seats = {}
    tables = tree.find(lambda n: n.tag == 'table' and n.attrs.get('id', '').startswith('housegov_reps_by_state-'))
    assert len(tables) == expected_tables, 'Unexpected number of state and territory tables'
    for table in tables:
        captions = table.find(lambda n: n.tag == 'caption')
        assert len(captions) == 1 and captions[0].text(), 'Directory caption missing'
        assert [n.text() for n in table.find(lambda n: n.tag == 'th')] == DIRECTORY_COLUMNS, 'Directory columns changed'
        for tr in table.find(lambda n: n.tag == 'tr'):
            cells = [c for c in tr.children if isinstance(c, Node) and c.tag == 'td']
            if not cells: continue
            assert len(cells) == len(DIRECTORY_COLUMNS), 'Directory row changed'
            # A vacant seat keeps the former member's name, labeled "- Vacancy"; it names no current member.
            if cells[1].text().endswith(' - Vacancy'): continue
            links = cells[1].find(lambda n: n.tag == 'a' and 'href' in n.attrs)
            assert len(links) == 1 and links[0].text() == cells[1].text(), 'Directory name link changed'
            seat = (captions[0].text(), cells[0].text())
            assert seat not in seats, ('Duplicate directory seat', seat)
            seats[seat] = (cells[1].text(), links[0].attrs['href'].strip())
    assert size[0] <= len(seats) <= size[1], 'Unexpected directory size'
    return buildings, seats


def parse_house(raw, source, buildings):
    """(rows for the 50 states, rows for DC and the territories, {id: (seat, 'Family, Given', address)}) from MemberData.xml."""
    root = ET.fromstring(raw)
    source['publishedAt'] = root.attrib.get('publish-date')
    source['congress'] = root.findtext('title-info/congress-num')
    assert source['congress'] == '119', 'Congress changed; review applicability before rebuilding'
    rows, delegates, details = [], [], {}
    for m in root.findall('members/member'):
        info = m.find('member-info')
        st = info.find('state').attrib['postal-code']
        assert st in STATE_CODES or st in TERRITORIES, 'Unknown House state code: '+st
        bio = info.findtext('bioguideID')
        if not bio: continue  # An absent person is not an inferred vacancy record.
        building = info.findtext('office-building')
        assert building in buildings, 'Unknown House office building code: '+str(building)
        room, zip5, plus4 = (' '.join((info.findtext(k) or '').split()) for k in ('office-room', 'office-zip', 'office-zip-suffix'))
        assert re.fullmatch(r'\d+[A-Z]?', room) and zip5 == '20515' and re.fullmatch(r'\d{4}', plus4), ('House office address changed', bio)
        fields = dict(party=info.findtext('party'), ids={'bioguide':bio}, **contact(source['url'], phone=info.findtext('phone')))
        if st in TERRITORIES:
            # <district> holds the title of a non-voting seat.
            office = info.findtext('district')
            assert office in {'Delegate', 'Resident Commissioner'}, ('Unexpected non-voting House office', st, office)
            row = dict(id='us-house-'+bio, name=info.findtext('official-name'), level='federal', jurisdiction='United States',
                       body='U.S. House', office=office, territory=st, sources=[source], **{k:v for k,v in fields.items() if v})
            assert row['name'], 'Missing House member name'
            delegates.append(row)
        else:
            row = record(source, 'us-house-'+bio, info.findtext('official-name'), st, 'federal', 'U.S. House', m.findtext('statedistrict')[2:], **fields)
            rows.append(row)
        assert row['id'] not in details, 'Duplicate House Bioguide ID'
        details[row['id']] = ((info.findtext('state/state-fullname'), info.findtext('district')), info.findtext('namelist'),
                              f'{room} {buildings[building]}, Washington, DC {zip5}-{plus4}')
    assert rows and 1 <= len(delegates) <= len(TERRITORIES) and len({r['territory'] for r in delegates}) == len(delegates), 'Unexpected House roster'
    return rows, delegates, details


SENATE_ADDRESS = re.compile(r'(\d+[A-Z]?) (Russell|Hart|Dirksen) Senate Office Building Washington DC (20510)')


def parse_federal(key, raw, source, buildings=None):
    if key == 'house':
        rows = parse_house(raw, source, buildings)[0]
    else:
        rows = []
        for m in ET.fromstring(raw).findall('member'):
            st = m.findtext('state')
            if st not in STATE_CODES: continue
            # <email> holds a contact-form URL, not an address.
            website = m.findtext('website')
            text = ' '.join((m.findtext('address') or '').split())
            office = SENATE_ADDRESS.fullmatch(text)
            assert office, 'Senate office address changed: '+text
            rows.append(record(source, 'us-senate-'+m.findtext('bioguide_id'), m.findtext('first_name')+' '+m.findtext('last_name'), st, 'federal', 'U.S. Senate', party=m.findtext('party'), ids={'bioguide':m.findtext('bioguide_id')}, website=website if website and urlparse(website).hostname.endswith('.senate.gov') else None,
                               address=f'{office[1]} {office[2]} Senate Office Building, Washington, DC {office[3]}', **contact(source['url'], phone=m.findtext('phone'))))
    assert rows, 'Empty federal roster'
    return rows


def parse_clerk_member(raw, bio, name):
    """(photo URL or None, the office address stated) from a member's Clerk page, clerk.house.gov/members/<bioguide>."""
    tree = HTML(raw).root
    photo = 'https://clerk.house.gov/images/members/'+bio+'.jpg'
    images = [n for n in tree.find(lambda n: n.tag == 'img') if urljoin(CLERK_MEMBER, n.attrs.get('src', '').strip()) == photo]
    assert len(images) <= 1, ('Several member photos', bio)
    if images: assert images[0].attrs.get('alt') == 'Photo of '+name, ('Member photo names someone else', bio, images[0].attrs.get('alt'))
    boxes = [n for n in tree.find(lambda n: n.tag == 'div' and has_class(n, 'member'))
             if any(isinstance(c, Node) and c.tag == 'h3' and c.text() == 'Contact' for c in n.children)]
    assert len(boxes) == 1, ('Clerk contact block missing', bio)
    rooms = [n.text() for n in boxes[0].children if isinstance(n, Node) and n.tag == 'span' and re.fullmatch(r'\d+[A-Z]? [A-Z][a-z]+ House Office Building', n.text())]
    cities = [n.text() for n in boxes[0].children if isinstance(n, Node) and n.tag == 'span' and has_class(n, 'address')]
    assert len(rooms) == 1 and len(cities) == 1, ('Clerk contact address changed', bio)
    city = re.fullmatch(r'(Washington), (DC), (\d{5}-\d{4})', cities[0])
    assert city, ('Clerk contact address changed', bio, cities[0])
    return (photo if images else None), f'{rooms[0]}, {city[1]}, {city[2]} {city[3]}'


def add_house_fields(row, detail, seats, directory, page_raw, page_source):
    """Website from the house.gov directory and photo from the member's Clerk page, each with field evidence.

    The address combines MemberData's room, building code and ZIP with the directory's room-code key,
    and must equal the address the member's Clerk page states.
    """
    seat, listed_name, address = detail
    assert seat in seats, ('Member missing from the house.gov directory', row['id'], seat)
    name, website = seats[seat]
    assert same_member(name, listed_name), ('house.gov directory names a different member', seat, name, listed_name)
    host = urlparse(website).hostname or ''
    # Published as the directory gives it (a few links use http://).
    assert urlparse(website).scheme in {'http', 'https'} and (host == 'house.gov' or host.endswith('.house.gov')), ('Member website outside house.gov', website)
    photo, stated = parse_clerk_member(page_raw, row['ids']['bioguide'], row['name'])
    assert stated == address, ('Clerk page and MemberData disagree on the office address', row['id'], stated, address)
    row['sources'] = row['sources'] + [directory, page_source]
    evidence = row.setdefault('fieldEvidence', {})
    row['website'] = website
    evidence['website'] = dict(value=website, sourceIds=[directory['id']])
    row['address'] = address
    evidence['address'] = dict(value=address, sourceIds=[row['sources'][0]['id'], directory['id'], page_source['id']])
    if photo:
        row['photo'] = photo
        evidence['photo'] = dict(value=photo, sourceIds=[page_source['id']])
    return row


def collect_federal(acquire, offline):
    """(U.S. House and Senate rows for the 50 states, non-voting House members, sources)."""
    from concurrent.futures import ThreadPoolExecutor
    sources = []
    def get(key, publisher, url, **options):
        raw, source = acquire(key, publisher, url, offline, **options)
        sources.append(source)
        return raw, source
    house_raw, house = get('house', *SOURCES['house'])
    directory_raw, directory = get('house-directory', *HOUSE_DIRECTORY, user_agent=USER_AGENT)
    buildings, seats = parse_house_directory(directory_raw)
    rows, delegates, details = parse_house(house_raw, house, buildings)
    def page(row):
        bio = row['ids']['bioguide']
        return row, *acquire('house-member-'+bio, SOURCES['house'][0], CLERK_MEMBER+bio, offline, user_agent=USER_AGENT)
    # One request per member page, a few at a time.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for row, page_raw, page_source in pool.map(page, rows + delegates):
            add_house_fields(row, details[row['id']], seats, directory, page_raw, page_source)
            sources.append(page_source)
    senate_raw, senate = get('senate', *SOURCES['senate'])
    return rows + parse_federal('senate', senate_raw, senate), delegates, sources


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
    # Statewide-office and high-court modules are discovered by filename (tools/statewide.py documents them).
    extra = sorted(p.stem for pattern in ('statewide_*.py', 'courts_*.py') for p in (Path(__file__).parent/'regions').glob(pattern))
    return [importlib.import_module('regions.' + name)
            for name in ['region_a','region_b','region_c','region_d','executive', *extra]]


def declared_statewide():
    """(statewide offices, courts) declared by the regional modules, by state."""
    statewide, courts = {}, {}
    for module in region_modules():
        for name, target in (('STATEWIDE', statewide), ('COURTS', courts)):
            for st, item in getattr(module, name, {}).items():
                assert st not in target, 'Two modules declare '+name+' for '+st
                target[st] = item
    import statewide as vocabulary
    vocabulary.check_declarations(statewide, courts, STATE_CODES)
    return statewide, courts


def is_court(row, courts=None):
    courts = declared_statewide()[1] if courts is None else courts
    return row['level'] == 'state' and row['body'] in {k for k in courts.get(row['state'], {}) if k != 'blockers'}


def source_allowed(source):
    url = source['url']
    if urlparse(url).scheme != 'https': return False
    if url.startswith('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/') or url.startswith(CENSUS): return True
    import geography_exceptions
    if url in {url for _,url in geography_exceptions.SOURCES.values()}: return True
    import district_sources
    if url in {rule['url'] for rules in district_sources.WITHHELD.values() for rule in rules.values()}: return True
    if url in {url for _,url in SOURCES.values()} or url == HOUSE_DIRECTORY[1] or CLERK_MEMBER_URL.fullmatch(url): return True
    import committees
    if url == committees.HOUSE[1] or committees.allowed(url): return True
    import national
    if url in {url for _,url in national.SOURCES.values()}: return True
    for module in region_modules():
        if url in {url for _,url in module.SOURCES.values()}: return True
        if url in {url for _,url in getattr(module, 'PARTY_SOURCES', {}).values()}: return True
        if urlparse(url).hostname in getattr(module, 'SOURCE_HOSTS', set()): return True
    return False


def legislative_chamber(row):
    assert row['level'] == 'state'
    if row['state'] == 'NE': return 'unicameral'
    body = row['body'].lower()
    if 'senate' in body: return 'upper'
    if 'house' in body or 'assembly' in body: return 'lower'
    raise ValueError('Unrecognized legislative body: ' + row['body'])


def is_executive(row):
    return row['level'] == 'state' and row['body'].endswith(' Executive')


def executive_coverage(st, declared, governors):
    assert (declared['governor'] == 'collected') == (governors == 1), 'Executive coverage disagrees with parsed rows: '+st
    return dict(offices=dict(governor=dict(status=declared['governor'], records=governors)),
                notCollected=['lieutenantGovernor','secretaryOfState','attorneyGeneral','otherStatewideOffices'],
                blockers=declared['blockers'])


# A state no statewide module declares (as opposed to one declared with no further elected offices).
UNDECLARED = object()


def state_executive(st, declared, governors, legacy, statewide=None, rows=()):
    """Coverage value for a state's executive offices; releases without executive rows keep their published value.

    statewide is None for a release with no statewide-office rows (published before tools/regions/statewide_*.py),
    which keeps the governor-only format. Otherwise it is the state's STATEWIDE declaration (possibly {}).
    """
    if legacy: return 'not-collected'
    base = executive_coverage(st, declared, governors)
    if statewide is None: return base
    if statewide is UNDECLARED: statewide_decl = {}
    else: statewide_decl = statewide
    import statewide as vocabulary
    offices = vocabulary.executive_offices(st, statewide_decl, [r for r in rows if r['office'] != 'Governor'])
    base['offices'].update(offices)
    base['notCollected'] = [k for k, v in offices.items() if v['status'] == 'not-collected'] + (['otherStatewideOffices'] if statewide is UNDECLARED else [])
    base['blockers'] = base['blockers'] + statewide_decl.get('blockers', [])
    return base


def court_coverage_for(st, courts, rows):
    import statewide as vocabulary
    if st not in courts: return 'not-collected'
    return vocabulary.court_coverage(st, courts[st], [r for r in rows if r['state'] == st and is_court(r, courts)])


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
    executive = next(m for m in region_modules() if m.__name__.endswith('.executive'))
    statewide, courts = declared_statewide()
    observed = collections.Counter((r['state'],legislative_chamber(r)) for r in rows if r['level']=='state' and not is_executive(r) and not is_court(r, courts))
    # Releases built before the statewide-office and court modules keep their published coverage format.
    legacy_statewide = not any(is_executive(r) and r['office'] != 'Governor' for r in rows)
    legacy_courts = not any(is_court(r, courts) for r in rows)
    governors = collections.Counter(r['state'] for r in rows if is_executive(r) and r['office']=='Governor')
    # A release built before tools/regions/executive.py existed has no executive rows; describe it as it was published.
    # A new build cannot reach this state: every governor source must parse to exactly one row or the build stops.
    legacy = not any(is_executive(r) for r in rows)
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
            stateExecutive=state_executive(st, executive.EXECUTIVE[st], governors[st], legacy,
                                           None if legacy_statewide else statewide.get(st, UNDECLARED),
                                           [r for r in rows if r['state'] == st and is_executive(r)]),
            **({} if legacy_courts else dict(stateCourts=court_coverage_for(st, courts, rows))),
            countyOfficials='not-collected'))
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
        assert not r.get('address') or (isinstance(r['address'], str) and r['address'] == ' '.join(r['address'].split())), r['address']
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
    import national
    if (folder/'national.json').exists():
        national_rows = json.loads((folder/'national.json').read_text())['officials']
        national.validate(national_rows, source_allowed)
        for r in national_rows:
            for src in r['sources']:
                assert src == source_index[src['id']]
        assert coverage['national'] == national.coverage(national_rows), 'National coverage disagrees with national.json'
    else:
        assert 'national' not in coverage, 'National coverage without national.json'
    with (folder/'officials.csv').open(newline='') as f:
        exported = list(csv.DictReader(f))
    assert [r['id'] for r in exported] == [r['id'] for r in rows]
    for item, r in zip(exported, rows):
        for key, value in item.items():
            assert (json.loads(value) if key in JSON_COLUMNS and value else value) == r.get(key, '')
    if (folder/'geography-report.json').exists():
        from verify_geography import verify as verify_geography
        verify_geography(folder,rows,sources)
    if (folder/'committees.json').exists():
        import committees
        committees.verify(folder,rows,source_index)
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
        federal_rows, delegates, federal_sources = collect_federal(acquire, offline)
        rows.extend(federal_rows)
        sources.extend(federal_sources)
        for key, (publisher, url) in SOURCES.items():
            if key in {'house','senate'}: continue
            raw, source = acquire(key, publisher, url, offline)
            rows.extend(parse_state(key, raw, source))
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
        import national
        national_rows,national_sources=national.collect(acquire,offline,delegates)
        sources.extend(national_sources)
        for row in rows+national_rows:
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
        import committees
        committee_data,committee_sources=committees.collect(acquire,offline,rows)
        (stage/'committees.json').write_text(json.dumps(committee_data,ensure_ascii=False,indent=2)+'\n')
        sources.extend(committee_sources)
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
        (stage/'national.json').write_text(json.dumps(dict(schemaVersion=2,generatedAt=now,officials=national_rows),ensure_ascii=False,indent=2)+'\n')
        coverage['national'] = national.coverage(national_rows)
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
