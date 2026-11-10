"""President and Vice President from the White House administration page.

These two offices have no state, so they are published in data/national.json
rather than officials.json, whose rows all belong to one of the 50 states.
"""
import html
import re
from urllib.parse import urljoin

PUBLISHER = 'The White House'
URL = 'https://www.whitehouse.gov/administration/'
SOURCES = {'us-executive': (PUBLISHER, URL)}
BODY = 'U.S. Executive'
# id, office, and the heading the administration page gives each officeholder.
OFFICES = [
    ('us-president', 'President', 'president', r'(?<!Vice )President'),
    ('us-vice-president', 'Vice President', 'vicePresident', r'Vice President'),
]
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


def collect(acquire, offline):
    key, (publisher, url) = next(iter(SOURCES.items()))
    raw, source = acquire(key, publisher, url, offline, user_agent=USER_AGENT)
    return parse(raw, source), [source]


def coverage(rows):
    """Coverage for each national office; collected means exactly one record."""
    out = {}
    for id, office, field, _ in OFFICES:
        n = sum(r['id'] == id for r in rows)
        assert n == 1, (office, n)
        out[field] = dict(status='collected', records=n)
    return out


def validate(rows, allowed):
    assert [r['id'] for r in rows] == [id for id, *_ in OFFICES], 'Unexpected national offices'
    for r, (id, office, *_ ) in zip(rows, OFFICES):
        assert r['level'] == 'federal' and r['jurisdiction'] == 'United States' and r['body'] == BODY and r['office'] == office
        assert 'state' not in r and r['name'] and r['sources']
        assert set(r) <= {'id', 'name', 'level', 'jurisdiction', 'body', 'office', 'website', 'photo', 'sources'}, sorted(r)
        for key in ('website', 'photo'):
            assert not r.get(key) or r[key].startswith('https://www.whitehouse.gov/'), r[key]
        for src in r['sources']:
            assert allowed(src) and len(src['sha256']) == 64
