#!/usr/bin/env python3
"""Congressional committee rosters from the House Clerk and U.S. Senate official XML.

Run alone to refresh data/committees.json in place against the published
officials (no roster rebuild); build.py also calls collect() during a full build.
"""
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

HOUSE = ('Office of the Clerk, U.S. House of Representatives', 'https://clerk.house.gov/xml/lists/MemberData.xml')
SENATE_INDEX = ('United States Senate', 'https://www.senate.gov/committees/index.htm')
SENATE_XML = 'https://www.senate.gov/general/committee_membership/committee_memberships_{}.xml'
SENATE_XML_PATH = re.compile(r'/general/committee_membership/committee_memberships_[A-Z]{4}\.xml')
# Joint committees list members of both chambers under one code; out of scope here.
COMMITTEE_TYPES = {'standing', 'select', 'special'}
ROLES = {'chair': 'Chair', 'chairman': 'Chair', 'vice chair': 'Vice Chair', 'vice chairman': 'Vice Chair', 'ranking': 'Ranking Member', 'ex officio': 'Ex Officio'}


def allowed(url):
    """Committee sources outside build.SOURCES: the Senate index and per-committee XML."""
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname == 'www.senate.gov' and (url == SENATE_INDEX[1] or bool(SENATE_XML_PATH.fullmatch(p.path)))


def fold(name):
    """Lowercase without accents: the committee XML writes "Lujan" for "Luján"."""
    return ''.join(ch for ch in unicodedata.normalize('NFKD', name) if not unicodedata.combining(ch)).lower()


def role(raw):
    return ROLES.get((raw or '').strip().lower())


def parse_house(raw, source, official_ids, minimum=20):
    root = ET.fromstring(raw)
    assert root.findtext('title-info/congress-num') == '119', 'Congress changed; review applicability before rebuilding'
    committees = {}
    for c in root.findall('committees/committee'):
        if c.attrib.get('type') not in COMMITTEE_TYPES: continue
        code = c.attrib['comcode']
        committees[code] = dict(id='house-'+code, chamber='house', code=code, name=' '.join(c.findtext('committee-fullname').split()), type=c.attrib['type'], members=[], sourceIds=[source['id']])
    for m in root.findall('members/member'):
        info = m.find('member-info')
        bio = info.findtext('bioguideID')
        if not bio or 'us-house-'+bio not in official_ids: continue
        for a in m.findall('committee-assignments/committee'):
            c = committees.get(a.attrib.get('comcode'))
            if c: c['members'].append(dict(officialId='us-house-'+bio, party=info.findtext('party'), rank=int(a.attrib['rank']), role=role(a.attrib.get('leadership'))))
    for c in committees.values():
        # The Clerk ranks members within party; the minority's first is the ranking member.
        chair = next((m for m in c['members'] if m['role'] == 'Chair'), None)
        for m in c['members']:
            if chair and not m['role'] and m['rank'] == 1 and m['party'] != chair['party']: m['role'] = 'Ranking Member'
        c['members'].sort(key=lambda m: (m['party'] != (chair or m)['party'], m['rank']))
        for m in c['members']: del m['party']
    out = [c for c in committees.values() if c['members']]
    assert len(out) >= minimum, 'House committee assignments missing'
    return out


def senate_codes(raw):
    codes = sorted(set(re.findall(rb'committee_memberships_(S[A-Z]{3})\.htm', raw)))
    assert len(codes) >= 15, 'Senate committee index changed'
    return [c.decode() for c in codes]


def parse_senate(raw, source, senators):
    root = ET.fromstring(raw)
    c = root.find('committees')
    code = c.findtext('committee_code')[:4]
    name = ' '.join(c.findtext('committee_name').split())
    members = []
    for m in c.findall('members/member'):
        st, first, last = m.findtext('state'), m.findtext('name/first').strip(), m.findtext('name/last').strip()
        # The Senate XML carries no member id; two senators per state, so state + surname identifies one.
        hits = [o for o in senators if o['state'] == st and fold(o['name']).split()[-1] == fold(last).split()[-1]]
        if len(hits) > 1: hits = [o for o in hits if fold(o['name']).startswith(fold(first))]
        assert len(hits) == 1, 'Unmatched senator %s %s (%s) on %s' % (first, last, st, code)
        members.append(dict(officialId=hits[0]['id'], rank=len(members)+1, role=role(m.findtext('position'))))
    assert members, 'Empty Senate committee '+code
    kind = 'select' if 'select' in name.lower() else 'special' if 'special' in name.lower() else 'standing'
    return dict(id='senate-'+code, chamber='senate', code=code, name=name, type=kind, members=members, sourceIds=[source['id']])


def collect(acquire, offline, rows):
    """Committees for the given officials, and the source evidence used."""
    official_ids = {r['id'] for r in rows}
    raw, house_source = acquire('house-committees', *HOUSE, offline)
    house_source['congress'] = '119'
    committees = parse_house(raw, house_source, official_ids)
    sources = [house_source]
    index_raw, index_source = acquire('senate-committees', *SENATE_INDEX, offline)
    sources.append(index_source)
    senators = [r for r in rows if r['body'] == 'U.S. Senate']
    for code in senate_codes(index_raw):
        raw, source = acquire('senate-committee-'+code, SENATE_INDEX[0], SENATE_XML.format(code), offline)
        committees.append(parse_senate(raw, source, senators))
        sources.append(source)
    committees.sort(key=lambda c: (c['chamber'], c['name']))
    return dict(schemaVersion=1, congress='119', committees=committees), sources


def verify(folder, rows, source_index):
    doc = json.loads((folder/'committees.json').read_text())
    ids = {r['id']: r for r in rows}
    seen = set()
    for c in doc['committees']:
        assert c['id'] not in seen and c['chamber'] in {'house', 'senate'} and c['name'] and c['members'], c['id']
        seen.add(c['id'])
        assert c['sourceIds'] and all(s in source_index for s in c['sourceIds']), 'Committee source missing: '+c['id']
        body = 'U.S. House' if c['chamber'] == 'house' else 'U.S. Senate'
        assert len({m['officialId'] for m in c['members']}) == len(c['members']), 'Duplicate committee member: '+c['id']
        for m in c['members']:
            assert m['officialId'] in ids and ids[m['officialId']]['body'] == body, m['officialId']
            assert m['role'] in {None, *ROLES.values()}


def refresh(offline=False):
    """Rewrite data/committees.json (and its sources and manifest entries) against the published officials."""
    import build
    folder = build.ROOT/'data'
    rows = json.loads((folder/'officials.json').read_text())['officials']
    doc, new_sources = collect(build.fetch, offline, rows)
    (folder/'committees.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n')
    new_ids = {s['id'] for s in new_sources}
    sources = [s for s in json.loads((folder/'sources.json').read_text()) if s['id'] not in new_ids and not s['id'].startswith('senate-committee')] + new_sources
    (folder/'sources.json').write_text(json.dumps(sources, indent=2)+'\n')
    manifest = json.loads((folder/'manifest.json').read_text())
    for name in ['committees.json', 'sources.json']: manifest[name] = build.digest((folder/name).read_bytes())
    (folder/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    # Check what this refresh wrote; build.py --verify covers the rest of the tree.
    verify(folder, rows, {s['id']: s for s in sources})
    assert all(build.source_allowed(s) for s in new_sources), 'Committee source outside the allowlist'
    print(json.dumps(dict(committees=len(doc['committees']), memberships=sum(len(c['members']) for c in doc['committees']))))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Use checksum-verified cached snapshots')
    refresh(parser.parse_args().offline)
