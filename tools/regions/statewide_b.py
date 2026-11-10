"""Elected statewide executive officers other than the governor for ID, IL, IN, IA, KS, KY, LA, ME, MD, MA, MI and MN.

Sources are official state pages only: a state page that lists every statewide
elected officer where one exists (Idaho, Kansas), otherwise each office's own
website, or the Minnesota Legislative Reference Library's officer lists where the
office's site refuses retrieval. Each rule names one element that identifies the
officeholder, with a pattern that must match at least once and yield exactly one
distinct name (a multi-member board: exactly its HOLDERS count of distinct
names). A missing or ambiguous match stops the build. Offices whose
official site refused plain HTTP retrieval with USER_AGENT are recorded as
not-collected with a blocker and are never filled from another publisher.

Offices that voters do not elect statewide are not declared: officers chosen by
the legislature (Maine's Secretary of State, Treasurer, Attorney General and
Auditor; Maryland's Treasurer), appointed officers (Maryland's Secretary of
State, Indiana's Secretary of Education), and boards elected from districts
(Kansas and Louisiana boards of education, Louisiana Public Service Commission,
Massachusetts Governor's Council). See docs/STATEWIDE-B.md.
"""
import datetime as dt
import html
import re
from build import record

NAMES = dict(ID='Idaho', IL='Illinois', IN='Indiana', IA='Iowa', KS='Kansas', KY='Kentucky', LA='Louisiana',
             ME='Maine', MD='Maryland', MA='Massachusetts', MI='Michigan', MN='Minnesota')
BODY = '{} Executive'
USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'

# source key: (publisher, url)
SOURCES = {
    'sw-id-officials': ('Idaho Secretary of State', 'https://voteidaho.gov/idaho-elected-officials/'),
    'sw-il-ltgov': ('Office of the Lieutenant Governor of Illinois', 'https://ltgov.illinois.gov/'),
    'sw-il-ag': ('Office of the Illinois Attorney General', 'https://illinoisattorneygeneral.gov/'),
    'sw-il-comptroller': ('Office of the Illinois Comptroller', 'https://illinoiscomptroller.gov/'),
    'sw-il-treasurer': ('Office of the Illinois State Treasurer', 'https://illinoistreasurer.gov/'),
    'sw-in-ltgov': ('Office of the Lieutenant Governor of Indiana', 'https://www.in.gov/lg/'),
    'sw-in-sos': ('Indiana Secretary of State', 'https://www.in.gov/sos/'),
    'sw-in-ag': ('Office of the Indiana Attorney General', 'https://www.in.gov/attorneygeneral/'),
    'sw-in-comptroller': ('Office of the Indiana State Comptroller', 'https://www.in.gov/comptroller/'),
    'sw-in-treasurer': ('Office of the Indiana Treasurer of State', 'https://www.in.gov/tos/'),
    'sw-ia-governor': ('Office of the Governor of Iowa', 'https://governor.iowa.gov/'),
    'sw-ia-ag': ('Office of the Iowa Attorney General', 'https://www.iowaattorneygeneral.gov/'),
    'sw-ia-auditor': ('Office of the Auditor of State of Iowa', 'https://www.auditor.iowa.gov/'),
    'sw-ia-treasurer': ('Office of the Treasurer of State of Iowa', 'https://www.iowatreasurer.gov/'),
    'sw-ia-agriculture': ('Iowa Department of Agriculture and Land Stewardship', 'https://iowaagriculture.gov/'),
    'sw-ks-officials': ('State of Kansas', 'https://portal.kansas.gov/government/'),
    'sw-ky-governor': ('Office of the Governor of Kentucky', 'https://governor.ky.gov/'),
    'sw-ky-sos': ('Kentucky Secretary of State', 'https://www.sos.ky.gov/Pages/default.aspx'),
    'sw-ky-ag': ('Office of the Kentucky Attorney General', 'https://www.ag.ky.gov/Pages/default.aspx'),
    'sw-ky-auditor': ('Kentucky Auditor of Public Accounts', 'https://www.auditor.ky.gov/Pages/index.aspx'),
    'sw-ky-treasurer': ('Kentucky State Treasury', 'https://treasury.ky.gov/Pages/index.aspx'),
    'sw-ky-agriculture': ('Kentucky Department of Agriculture', 'https://www.kyagr.com/'),
    'sw-la-ltgov': ('Office of the Lieutenant Governor of Louisiana', 'https://www.crt.state.la.us/lt-governor/'),
    'sw-la-sos': ('Louisiana Secretary of State', 'https://www.sos.la.gov/'),
    'sw-la-ag': ('Louisiana Department of Justice', 'https://www.ag.state.la.us/'),
    'sw-la-treasurer': ('Louisiana Department of the Treasury', 'https://www.treasury.la.gov/'),
    'sw-la-agriculture': ('Louisiana Department of Agriculture and Forestry', 'https://www.ldaf.la.gov/'),
    'sw-md-ltgov': ('Office of the Governor of Maryland', 'https://governor.maryland.gov/leadership/lt-governor'),
    'sw-md-ag': ('Office of the Attorney General of Maryland', 'https://oag.maryland.gov/Pages/oag.aspx'),
    'sw-md-comptroller': ('Comptroller of Maryland', 'https://www.marylandcomptroller.gov/'),
    'sw-ma-governor': ('Commonwealth of Massachusetts', 'https://www.mass.gov/orgs/office-of-the-governor'),
    'sw-ma-ag': ('Commonwealth of Massachusetts', 'https://www.mass.gov/orgs/office-of-the-attorney-general'),
    'sw-ma-treasurer': ('Commonwealth of Massachusetts', 'https://www.mass.gov/orgs/office-of-the-treasurer-and-receiver-general'),
    'sw-ma-auditor': ('Commonwealth of Massachusetts', 'https://www.mass.gov/orgs/office-of-the-state-auditor'),
    'sw-mi-msu': ('Michigan State University Board of Trustees', 'https://trustees.msu.edu/about/meet-the-trustees'),
    'sw-mi-wsu': ('Wayne State University Board of Governors', 'https://bog.wayne.edu/members'),
    'sw-mn-ltgov': ('Minnesota Legislative Reference Library', 'https://www.lrl.mn.gov/mngov/ltgov'),
    'sw-mn-sos': ('Minnesota Legislative Reference Library', 'https://www.lrl.mn.gov/mngov/secstate'),
    'sw-mn-ag': ('Office of the Minnesota Attorney General', 'https://www.ag.state.mn.us/'),
    'sw-mn-auditor': ('Office of the Minnesota State Auditor', 'https://www.osa.state.mn.us/'),
}

N = r"(?P<name>[A-Z][A-Za-z.'’À-ſ\- ]+?)"
TITLE = r'<title[^>]*>\s*'
# Idaho Secretary of State officials list: a bold office label followed by an <h3> "Name (P)" and the office's website link.
ID = (r'<p><strong>{}</strong></p>(?:(?!<strong>).){{0,900}}?<h3 class="elementor-heading-title elementor-size-default">'
      + N + r' \((?P<party>[A-Z])\)</h3>(?:(?!<strong>).){{0,3000}}?<a class="link--external" href="(?P<website>https://[^"]+)" rel="noopener noreferrer" target="_blank">')
# Kansas portal "Elected State Officials" cards: link to the office, name, then office description.
KS = (r'<a class="elementor-cta" href="(?P<website>https://[^"]+)" target="_blank" rel="nofollow">(?:(?!</a>).){{0,800}}?'
      r'<div class="elementor-cta__title elementor-cta__content-item elementor-content-item"> ' + N +
      r' </div> <div class="elementor-cta__description elementor-cta__content-item elementor-content-item"> {} </div>')
# Mass.gov organization page header: leadership link to the person's page, then the title it carries.
MA = (r'<li class="ma__page-header__link"> <span class="ma__decorative-link ma__decorative-link--inverse"> '
      r'<a href="https://www\.mass\.gov/person/[a-z0-9-]+" class="js-clickable-link" > <span> ' + N +
      r'</span> <svg [^>]*><use [^>]*></use></svg></a> </span> <div class="ma__page-header-legacy__description"> {} </div>')
# Minnesota LRL officer lists: the first row of the state table (the only one with a <colgroup>) is the most recent holder.
MN_LG = (r'</colgroup> <thead> <tr> <th>ASSUMED OFFICE</th> <th>NAME</th> <th>PARTY</th> <th>RESIDENCE</th> <th>OCCUPATION</th> </tr> </thead> '
         r'<tbody> <tr> <td>(?P<date>\d{1,2}/\d{1,2}/\d{4})</td> <td>' + N + r'</td> <td>(?P<party>[A-Za-z-]+)</td>')
MN_SOS = (r'</colgroup> <thead> <tr> <th>ASSUMED OFFICE</th> <th>SECRETARY OF STATE</th> <th>RESIDENCE</th> </tr> </thead> '
          r'<tbody> <tr> <td>(?P<date>\d{4} [A-Z][a-z]+ \d{1,2})</td> <td>(?P<last>[A-Z][A-Za-z.\'\- ]+), (?P<first>[A-Z][A-Za-z.\'\- ]+)</td>')

# (state, office key, source key, pattern). Patterns run on the HTML-unescaped page with zero-width characters
# removed and whitespace collapsed.
RULES = [
    ('ID', 'lieutenantGovernor', 'sw-id-officials', ID.format('Lieutenant Governor')),
    ('ID', 'secretaryOfState', 'sw-id-officials', ID.format('Secretary of State')),
    ('ID', 'attorneyGeneral', 'sw-id-officials', ID.format('Attorney General')),
    ('ID', 'controller', 'sw-id-officials', ID.format('State Controller')),
    ('ID', 'treasurer', 'sw-id-officials', ID.format('State Treasurer')),
    ('ID', 'superintendentOfPublicInstruction', 'sw-id-officials', ID.format('Superintendent of <br />Public Instruction')),

    ('IL', 'lieutenantGovernor', 'sw-il-ltgov', r'<h1 class="cmp-title__text"> Lieutenant Governor ' + N + r'</h1>'),
    ('IL', 'attorneyGeneral', 'sw-il-ag', TITLE + r'Office of the Illinois Attorney General ' + N + r'\s*</title>'),
    ('IL', 'comptroller', 'sw-il-comptroller', TITLE + N + r' – Illinois State Comptroller - The Illinois Office of Comptroller\s*</title>'),
    ('IL', 'treasurer', 'sw-il-treasurer', TITLE + r'Illinois State Treasurer ' + N + r': '),

    ('IN', 'lieutenantGovernor', 'sw-in-ltgov', TITLE + r'Lieutenant Governor ' + N + r': Home\s*</title>'),
    ('IN', 'secretaryOfState', 'sw-in-sos', r'<h1>Welcome to the Office of Secretary of State ' + N + r'</h1>'),
    ('IN', 'attorneyGeneral', 'sw-in-ag', r'<h1>Attorney General ' + N + r'</h1>'),
    ('IN', 'comptroller', 'sw-in-comptroller', r'<h1 >Indiana State Comptroller ' + N + r'</h1>'),
    ('IN', 'treasurer', 'sw-in-treasurer', r'<h2>Welcome to the Office of Treasurer ' + N + r'</h2>'),

    ('IA', 'lieutenantGovernor', 'sw-ia-governor', r'alt="Lt\. Governor ' + N + r' headshot"'),
    ('IA', 'attorneyGeneral', 'sw-ia-ag', r'<h2>' + N + r'</h2> <p>Iowa Attorney General</p>'),
    ('IA', 'auditor', 'sw-ia-auditor', r'<div class="logo-text">IOWA AUDITOR OF STATE<br>' + N + r'</div>'),
    ('IA', 'treasurer', 'sw-ia-treasurer', r'<p>Hi – I’m ' + N + r', Iowa’s State Treasurer\.'),
    # Iowa titles the office Secretary of Agriculture; it is the elected head of the state agriculture department.
    ('IA', 'agricultureCommissioner', 'sw-ia-agriculture', r'href="https://iowaagriculture\.gov/[a-z-]+" target=""> Secretary of Agriculture ' + N + r' </a>'),

    ('KS', 'lieutenantGovernor', 'sw-ks-officials', KS.format(r'Lt\. Governor')),
    ('KS', 'secretaryOfState', 'sw-ks-officials', KS.format('Secretary of State')),
    ('KS', 'treasurer', 'sw-ks-officials', KS.format('State Treasurer')),
    ('KS', 'attorneyGeneral', 'sw-ks-officials', KS.format('Attorney General')),
    ('KS', 'insuranceCommissioner', 'sw-ks-officials', KS.format('Insurance Commissioner')),

    ('KY', 'lieutenantGovernor', 'sw-ky-governor', r'<h2 class="bottom"><small>LIEUTENANT GOVERNOR</small>' + N + r'</h2>'),
    ('KY', 'secretaryOfState', 'sw-ky-sos', r'<meta name="description" content="Secretary of State ' + N + r'" />'),
    ('KY', 'attorneyGeneral', 'sw-ky-ag', r'<span class="header-title">Attorney General<br><span class="header-title-name">' + N + r'</span></span>'),
    ('KY', 'auditor', 'sw-ky-auditor', r'<span class="header-title">AUDITOR OF PUBLIC ACCOUNTS<br><span class="header-title-name">' + N + r'</span></span>'),
    ('KY', 'treasurer', 'sw-ky-treasurer', r'<h2 class="agencyElement-H2-Fancy">A Message from Treasurer ' + N + r'</h2>'),
    ('KY', 'agricultureCommissioner', 'sw-ky-agriculture', r'<a href="https://www\.kyagr\.com/commissioner/"><img src="[^"]+" alt="Commissioner ' + N + r'" title="Commissioner [^"]+"></a>'),

    ('LA', 'lieutenantGovernor', 'sw-la-ltgov', TITLE + r'Lt\. Governor ' + N + r' \| State of Louisiana\s*</title>'),
    ('LA', 'secretaryOfState', 'sw-la-sos', r"<p>Learn about Louisiana's Secretary of State " + N + r"'s background and role\.</p>"),
    ('LA', 'attorneyGeneral', 'sw-la-ag', r'<h1>Meet ' + N + r'</h1>'),
    ('LA', 'treasurer', 'sw-la-treasurer', TITLE + N + r', MD Treasurer \| Louisiana State Treasurer \| Louisiana\s*</title>'),
    ('LA', 'agricultureCommissioner', 'sw-la-agriculture', r'<a href="/about/commissioner" class="usa-link">Commissioner ' + N + r'</a>'),

    ('MD', 'lieutenantGovernor', 'sw-md-ltgov', r'<h1 id="page-hero" class="maryland-hero__title"><span>The Office of Lieutenant Governor ' + N + r'</span> </h1>'),
    ('MD', 'attorneyGeneral', 'sw-md-ag', r'<span>Attorney General of Maryland</span></span> <span class="mdgov-agency__name"><span>' + N + r'</span></span>'),
    ('MD', 'comptroller', 'sw-md-comptroller', r'<meta name="description" content="Office of the Comptroller of Maryland, led by Comptroller ' + N + r'\. Working towards '),

    ('MA', 'lieutenantGovernor', 'sw-ma-governor', MA.format('Lieutenant Governor')),
    ('MA', 'attorneyGeneral', 'sw-ma-ag', MA.format('Attorney General')),
    ('MA', 'treasurer', 'sw-ma-treasurer', r'<h1 class="ma__page-header__title"> Office of State Treasurer and Receiver General ' + N + r' </h1>'),
    ('MA', 'auditor', 'sw-ma-auditor', MA.format('State Auditor')),

    # Both boards are elected statewide (Mich. Const. art. VIII, sec. 5). The member pages list the eight elected
    # members only; the university president, an ex officio member, has no card on either page.
    ('MI', 'universityTrustee', 'sw-mi-msu', r'<h2 class="line">' + N + r'</h2><div class="mixed-content-text"><div class="ck-content"><p[^<>]*>(?:<span[^<>]*>)*(?:Chair \| |Vice Chair \| )?Term ends [A-Z][a-z]+\.? \d{1,2}, \d{4}</'),
    ('MI', 'universityGovernor', 'sw-mi-wsu', r'<div id="promo-\d+" class="my-1 font-bold text-lg [^"]*"> ' + N + r'(?:, (?:Chair|Vice Chair))? </div>'),

    ('MN', 'lieutenantGovernor', 'sw-mn-ltgov', MN_LG),
    ('MN', 'secretaryOfState', 'sw-mn-sos', MN_SOS),
    ('MN', 'attorneyGeneral', 'sw-mn-ag', r'alt="Portrait of Attorney General ' + N + r'"'),
    ('MN', 'auditor', 'sw-mn-auditor', TITLE + r'Office of the State Auditor ' + N + r' \| MN Office of the State Auditor \(OSA\)\s*</title>'),
]

# Elected statewide offices whose official sources refused retrieval with USER_AGENT (checked November 2026).
BLOCKED = {
    ('IL', 'secretaryOfState'): 'https://www.ilsos.gov/ reset every HTTP/2 stream and timed out over HTTP/1.1',
    ('IA', 'secretaryOfState'): 'https://sos.iowa.gov/ returned a Cloudflare challenge (HTTP 403)',
    ('LA', 'insuranceCommissioner'): 'https://www.ldi.la.gov/ returned a bot challenge (HTTP 403)',
    ('MA', 'secretaryOfState'): 'https://www.sec.state.ma.us/ redirected to itself until the redirect limit (it requires a cookie session)',
    ('MI', 'lieutenantGovernor'): 'https://www.michigan.gov/ returned Access Denied (HTTP 403) for every office page',
    ('MI', 'secretaryOfState'): 'https://www.michigan.gov/sos returned Access Denied (HTTP 403)',
    ('MI', 'attorneyGeneral'): 'https://www.michigan.gov/ag returned Access Denied (HTTP 403)',
    ('MI', 'stateBoardOfEducationMember'): 'https://www.michigan.gov/mde returned Access Denied (HTTP 403)',
    ('MI', 'universityRegent'): 'https://regents.umich.edu/regents/ returned a bot challenge (HTTP 403)',
}
# Multi-member boards: (state, office key) -> number of elected members the source must list.
HOLDERS = {('MI', 'universityTrustee'): 8, ('MI', 'universityGovernor'): 8}
assert len({(st, office) for st, office, _, _ in RULES}) == len(RULES)
assert set(HOLDERS) <= {(st, office) for st, office, _, _ in RULES}
assert not {(st, office) for st, office, _, _ in RULES} & set(BLOCKED)
assert {key for _, _, key, _ in RULES} == set(SOURCES)

STATEWIDE = {st: {} for st in NAMES}
for st, office, _, _ in RULES: STATEWIDE[st][office] = 'collected'
for (st, office), why in BLOCKED.items():
    STATEWIDE[st][office] = 'not-collected'
    STATEWIDE[st].setdefault('blockers', []).append(f'{office}: the official source refused automated retrieval: {why}')
# Maine elects no statewide officer other than the governor (its constitutional officers and auditor are chosen by
# the Legislature). An explicit empty blocker list records that the declaration is complete, not missing.
STATEWIDE['ME'] = {'blockers': []}
for item in STATEWIDE.values(): item.setdefault('blockers', [])

PARTIES = {'R': 'Republican', 'D': 'Democratic'}
NOT_A_NAME = re.compile(r'\b(?:Office|Governor|Home|Welcome|State|Attorney|General|Secretary|Treasurer|Auditor|Comptroller|Commissioner|Department)\b')


def normalize(raw):
    text = html.unescape(raw.decode('utf-8', 'replace'))
    return ' '.join(re.sub('[​‌‍﻿]', '', text).split())


def lrl_date(text):
    for fmt in ('%m/%d/%Y', '%Y %B %d'):
        try: return dt.datetime.strptime(text, fmt).date()
        except ValueError: pass
    raise AssertionError(('Unparseable assumed-office date', text))


def extract(st, office, pattern, page, retrieved, holders=1):
    """The officeholders [(name, party, website), ...] that the rule's pattern yields on the page: exactly `holders`."""
    found = []  # distinct (name, party, website) in page order
    for m in re.finditer(pattern, page):
        g = m.groupdict()
        name = f"{g['first']} {g['last']}" if g.get('last') else g['name']
        name = ' '.join(name.split())
        if g.get('date'):
            # A list row dated after retrieval would be an officeholder-elect, not the incumbent.
            assert lrl_date(g['date']) <= retrieved, (st, office, 'Assumed-office date is after retrieval', g['date'])
        party = g.get('party')
        item = (name, PARTIES.get(party, party), g.get('website'))
        if item not in found: found.append(item)
    assert len(found) == holders, (st, office, f'Expected exactly {holders} officeholder(s)', sorted(found))
    assert len({name for name, _, _ in found}) == holders, (st, office, 'Conflicting details for one officeholder', sorted(found))
    for name, _, _ in found:
        assert 2 <= len(name.split()) <= 5 and not NOT_A_NAME.search(name), (st, office, name)
    return found


def parse(key, raw, source):
    import statewide as vocabulary
    page = normalize(raw)
    retrieved = dt.datetime.fromisoformat(source['retrievedAt']).date()
    rows = []
    for st, office, src, pattern in RULES:
        if src != key: continue
        holders = HOLDERS.get((st, office), 1)
        found = extract(st, office, pattern, page, retrieved, holders)
        for i, (name, party, website) in enumerate(found, 1):
            id = f'{st.lower()}-{office}' + (f'-{i}' if office in vocabulary.MULTI else '')
            rows.append(record(source, id, name, st, 'state', BODY.format(NAMES[st]),
                               office=vocabulary.OFFICES[office][0], party=party, website=website or source['url']))
    assert rows, ('No statewide rules for source', key)
    return rows


def collect(acquire, offline):
    rows, sources = [], []
    for key, (publisher, url) in SOURCES.items():
        raw, source = acquire(key, publisher, url, offline, user_agent=USER_AGENT)
        rows.extend(parse(key, raw, source))
        sources.append(source)
    return rows, sources
