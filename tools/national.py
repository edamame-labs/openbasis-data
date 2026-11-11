"""Officeholders with no state: the President, the Vice President, and the
non-voting House members for the District of Columbia and the territories.

These rows are published in data/national.json rather than officials.json,
whose rows all belong to one of the 50 states.
"""
import html
import json
import re
from urllib.parse import urljoin, urlparse

PUBLISHER = 'The White House'
URL = 'https://www.whitehouse.gov/administration/'
# Party for the two executive offices, each from a federal source that states it.
FEC_PUBLISHER = 'Federal Election Commission'
FEC_CANDIDATE = 'P80001571'
FEC_URL = 'https://api.open.fec.gov/v1/candidate/' + FEC_CANDIDATE + '/?api_key=DEMO_KEY'
SENATE_PUBLISHER = 'United States Senate'
SENATE_VP_URL = 'https://www.senate.gov/about/officers-staff/vice-president/vice-presidents.htm'
SOURCES = {
    'us-executive': (PUBLISHER, URL),
    'us-president-fec': (FEC_PUBLISHER, FEC_URL),
    'us-vice-presidents': (SENATE_PUBLISHER, SENATE_VP_URL),
}
BODY = 'U.S. Executive'
# id, office, and the heading the administration page gives each officeholder.
OFFICES = [
    ('us-president', 'President', 'president', r'(?<!Vice )President'),
    ('us-vice-president', 'Vice President', 'vicePresident', r'Vice President'),
]
# Non-voting House members, as the Clerk's MemberData.xml titles them (tools/build.py parse_house).
TERRITORIES = {'DC', 'PR', 'GU', 'VI', 'AS', 'MP'}
DELEGATE_OFFICES = {'Delegate', 'Resident Commissioner'}
FEC_PARTIES = {'REP': 'Republican', 'DEM': 'Democratic'}
N = r"(?P<name>[A-Z][A-Za-z.'\- ]+?)"
USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'


def parse(raw, source):
    page = ' '.join(html.unescape(raw.decode('utf-8', 'replace')).split())
    rows = []
    for id, office, _, title in OFFICES:
        # <h2 ...><a href="/administration/<slug>/">President Donald J. Trump</a></h2>
        pattern = r'<h2[^>]*>\s*<a href="(?P<href>/administration/[a-z0-9-]+/)">\s*' + title + r' ' + N + r'\s*</a>\s*</h2>'
        found = {(' '.join(m.group('name').split()), m.group('href')) for m in re.finditer(pattern, page)}
        assert len(found) == 1, (office, 'Expected exactly one officeholder heading', sorted(found))
        name, href = found.pop()
        assert 2 <= len(name.split()) <= 5 and not re.search(r'\b(?:President|Vice|Cabinet|Administration|First|Second|Lady)\b', name), (office, name)
        row = dict(id=id, name=name, level='federal', jurisdiction='United States', body=BODY, office=office,
                   website=urljoin(URL, href), sources=[source])
        # The portrait linked to the same page, when the page publishes exactly one.
        photos = set(re.findall(r'<a href="' + re.escape(href) + r'">\s*<img [^>]*?src="(https://www\.whitehouse\.gov/[^"]+)"[^>]*alt="[^"]*Official Portrait"', page))
        if len(photos) == 1: row['photo'] = photos.pop()
        rows.append(row)
    return rows


def letters(text):
    return re.sub(r'[^a-z]', '', text.casefold())


def same_person(given_family, other):
    """'Given ... Family' and another spelling agree on family name and first given name (initials' dots ignored)."""
    a, b = given_family.split(), other.split()
    return letters(a[-1]) == letters(b[-1]) and letters(a[0]) == letters(b[0])


def fec_party(raw, president):
    """Party of the President's FEC presidential candidate record, which must name the same person."""
    results = json.loads(raw)['results']
    assert len(results) == 1, 'Expected one FEC candidate record'
    r = results[0]
    assert r['candidate_id'] == FEC_CANDIDATE and r['office'] == 'P' and 2024 in r['election_years'], 'FEC candidate record changed'
    family, given = r['name'].split(',', 1)
    assert same_person(given.strip() + ' ' + family.strip(), president), ('FEC candidate is not the President', r['name'], president)
    assert r['party'] in FEC_PARTIES, ('Unmapped FEC party code', r['party'], r['party_full'])
    return FEC_PARTIES[r['party']]


def senate_vp_party(raw, vice_president, president):
    """Party of the serving Vice President from the Senate's list of Vice Presidents (term ending "present")."""
    page = html.unescape(raw.decode('utf-8', 'replace'))
    tables = re.findall(r'<table[^>]*id="SortableData_table".*?</table>', page, re.S)
    assert len(tables) == 1, 'Vice President table missing'
    cells = lambda tr: [' '.join(re.sub(r'<sup>.*?</sup>|<[^>]+>', ' ', c).split()) for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
    current = [c for c in map(cells, re.findall(r'<tr[^>]*>(.*?)</tr>', tables[0], re.S)) if c and re.search(r'\bpresent$', c[-1])]
    assert len(current) == 1 and len(current[0]) == 4, ('Expected one serving Vice President', current)
    name, party, presidency, _ = current[0]
    assert same_person(name, vice_president), ('Senate list names a different Vice President', name, vice_president)
    assert same_person(presidency, president), ('Senate list names a different President', presidency, president)
    assert party in {'Republican', 'Democratic'}, ('Unexpected party label', party)
    return party


def add_party(row, party, source):
    row['party'] = party
    row['sources'] = row['sources'] + [source]
    row['fieldEvidence'] = dict(party=dict(value=party, sourceIds=[source['id']]))


def collect(acquire, offline, delegates=()):
    sources = {key: acquire(key, publisher, url, offline, user_agent=USER_AGENT) for key, (publisher, url) in SOURCES.items()}
    president, vice_president = parse(*sources['us-executive'])
    raw, source = sources['us-president-fec']
    add_party(president, fec_party(raw, president['name']), source)
    raw, source = sources['us-vice-presidents']
    add_party(vice_president, senate_vp_party(raw, vice_president['name'], president['name']), source)
    return [president, vice_president] + sorted(delegates, key=lambda r: r['territory']), [s for _, s in sources.values()]


def coverage(rows):
    """Coverage for each national office; an executive office is collected with exactly one record.

    Releases built before the non-voting House members were added have no delegate rows and no `delegates` key.
    """
    out = {}
    for id, office, field, _ in OFFICES:
        n = sum(r['id'] == id for r in rows)
        assert n == 1, (office, n)
        out[field] = dict(status='collected', records=n)
    delegates = sum(r.get('territory') is not None for r in rows)
    if delegates: out['delegates'] = dict(status='collected', records=delegates)
    return out


EXECUTIVE_FIELDS = {'id', 'name', 'level', 'jurisdiction', 'body', 'office', 'party', 'website', 'photo', 'sources', 'fieldEvidence'}
DELEGATE_FIELDS = {'id', 'name', 'level', 'jurisdiction', 'body', 'office', 'territory', 'party', 'phone', 'address', 'website', 'photo', 'ids', 'sources', 'fieldEvidence'}


def validate(rows, allowed):
    executive, delegates = rows[:len(OFFICES)], rows[len(OFFICES):]
    assert [r['id'] for r in executive] == [id for id, *_ in OFFICES], 'Unexpected national offices'
    for r, (id, office, *_ ) in zip(executive, OFFICES):
        assert r['body'] == BODY and r['office'] == office
        assert set(r) <= EXECUTIVE_FIELDS, sorted(r)
        for key in ('website', 'photo'):
            assert not r.get(key) or r[key].startswith('https://www.whitehouse.gov/'), r[key]
    assert [r['territory'] for r in delegates] == sorted({r['territory'] for r in delegates}), 'Delegates must be unique and ordered by territory'
    for r in delegates:
        assert r['id'] == 'us-house-' + r['ids']['bioguide'] and r['body'] == 'U.S. House' and r['office'] in DELEGATE_OFFICES
        assert r['territory'] in TERRITORIES and (r['office'] == 'Resident Commissioner') == (r['territory'] == 'PR'), (r['territory'], r['office'])
        assert set(r) <= DELEGATE_FIELDS, sorted(r)
        if r.get('website'):
            host = urlparse(r['website']).hostname or ''
            assert urlparse(r['website']).scheme in {'http', 'https'} and (host == 'house.gov' or host.endswith('.house.gov')), r['website']
        assert not r.get('address') or r['address'] == ' '.join(r['address'].split()), r['address']
        assert not r.get('photo') or r['photo'] == 'https://clerk.house.gov/images/members/' + r['ids']['bioguide'] + '.jpg', r['photo']
        assert not r.get('phone') or re.fullmatch(r'\d{3}-\d{3}-\d{4}', r['phone']), r['phone']
    for r in rows:
        assert r['level'] == 'federal' and r['jurisdiction'] == 'United States'
        assert 'state' not in r and 'district' not in r and r['name'] and r['sources']
        assert len({src['id'] for src in r['sources']}) == len(r['sources']), 'Duplicate record references'
        for src in r['sources']:
            assert allowed(src) and len(src['sha256']) == 64
        for field, proof in r.get('fieldEvidence', {}).items():
            assert field in {'party', 'website', 'address', 'photo'}, 'Unsupported field evidence: ' + field
            assert proof['value'] == r.get(field) and proof['sourceIds'] and set(proof['sourceIds']) <= {src['id'] for src in r['sources']}
