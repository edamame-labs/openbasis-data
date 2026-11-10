"""Elected statewide executive officers other than the governor, from official state websites.

States: MS MO MT NE NV NH NJ NM NY NC ND OH OK OR. See docs/STATEWIDE-C.md for the
official page that establishes which offices each state elects, and the element
each rule reads.

Each rule names one element of an official page that identifies the officeholder
(page title, a heading, a meta description, an image caption or a navigation
label) with a pattern that must match at least once. A single-holder office must
yield exactly one distinct name; a multi-member office must yield exactly the
declared number of distinct names. Zero, conflicting or surplus matches stop the
build. Offices whose official site refused retrieval with USER_AGENT are listed
in BLOCKED and recorded as not collected; no other publisher substitutes for them.

A page reports the officeholder its publisher currently shows. Officeholders-elect
from the November 2026 general election are not recorded until the official page
shows them in office.
"""
import html
import re
from build import record
from regions.executive import NAMES
from statewide import OFFICES, MULTI

USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'
BODY = '{} Executive'
STATES = 'MS MO MT NE NV NH NJ NM NY NC ND OH OK OR'.split()

# Names: capitalized words, with initials, apostrophes, hyphens and a parenthesized nickname.
N = r"(?P<name>[A-Z][A-Za-zÀ-ſ.'’()\- ]+?)"
TITLE = r'<title[^>]*>\s*'

# key: (publisher, url). One fetch per key; several rules may read the same page.
SOURCES = {
 # Mississippi
 'sw-ms-lg': ('Mississippi Legislature', 'https://www.legislature.ms.gov/'),
 # ago.state.ms.us redirects to this domain, which the Office of the Attorney General operates.
 'sw-ms-ag': ('Office of the Attorney General of Mississippi', 'https://attorneygenerallynnfitch.com/'),
 'sw-ms-tre': ('Mississippi State Treasury', 'https://treasury.ms.gov/'),
 'sw-ms-aud': ('Office of the State Auditor of Mississippi', 'https://www.osa.ms.gov/'),
 'sw-ms-agr': ('Mississippi Department of Agriculture and Commerce', 'https://www.mdac.ms.gov/'),
 'sw-ms-ins': ('Mississippi Insurance Department', 'https://www.mid.ms.gov/mississippi-insurance-department/about-the-mississippi-insurance-department/divisions/office-of-the-commissioner/'),
 # Missouri
 'sw-mo-lg': ('Office of the Lieutenant Governor of Missouri', 'https://ltgov.mo.gov/'),
 'sw-mo-sos': ('Missouri Secretary of State', 'https://www.sos.mo.gov/'),
 'sw-mo-aud': ('Missouri State Auditor', 'https://auditor.mo.gov/'),
 'sw-mo-tre': ('Missouri State Treasurer', 'https://treasurer.mo.gov/'),
 'sw-mo-ag': ('Missouri Attorney General', 'https://ago.mo.gov/about-us/about-ag-hanaway/'),
 # Montana
 'sw-mt-lg': ('Office of the Governor of Montana', 'https://governor.mt.gov/'),
 'sw-mt-ag': ('Montana Department of Justice', 'https://dojmt.gov/'),
 'sw-mt-aud': ('Montana Commissioner of Securities and Insurance, Office of the State Auditor', 'https://csimt.gov/meet-commissioner-brown/'),
 'sw-mt-opi': ('Montana Office of Public Instruction', 'https://opi.mt.gov/'),
 # Nebraska: one page lists all five elected constitutional officers below the governor.
 'sw-ne': ('State of Nebraska', 'https://www.nebraska.gov/government/executive-branch/'),
 # Nevada
 'sw-nv-lg': ('Office of the Lieutenant Governor of Nevada', 'https://www.ltgov.nv.gov/'),
 'sw-nv-ag': ('Office of the Nevada Attorney General', 'https://ag.nv.gov/'),
 'sw-nv-tre': ('Nevada State Treasurer', 'https://www.nevadatreasurer.nv.gov/'),
 'sw-nv-con': ('Nevada State Controller', 'https://www.controller.nv.gov/'),
 # New Jersey
 'sw-nj-lg': ('Office of the Governor of New Jersey', 'https://www.nj.gov/governor/admin/ltgovernor/'),
 # New Mexico
 'sw-nm-lg': ('Office of the Lieutenant Governor of New Mexico', 'https://www.ltgov.nm.gov/'),
 'sw-nm-sos': ('New Mexico Secretary of State', 'https://www.sos.nm.gov/'),
 'sw-nm-tre': ('New Mexico State Treasurer', 'https://www.nmsto.gov/about'),
 'sw-nm-aud': ('New Mexico Office of the State Auditor', 'https://www.osa.nm.gov/'),
 'sw-nm-slo': ('New Mexico State Land Office', 'https://www.nmstatelands.org/'),
 # New York
 'sw-ny-ag': ('New York State Attorney General', 'https://ag.ny.gov/'),
 'sw-ny-osc': ('Office of the New York State Comptroller', 'https://www.osc.ny.gov/'),
 # North Carolina: one page lists the Lieutenant Governor and the Council of State.
 'sw-nc': ('State of North Carolina', 'https://www.nc.gov/your-government/executive'),
 # North Dakota
 'sw-nd-lg': ('Office of the Governor of North Dakota', 'https://www.governor.nd.gov/lt-governor-michelle-strinden'),
 'sw-nd-ag': ('North Dakota Attorney General', 'https://attorneygeneral.nd.gov/'),
 'sw-nd-aud': ('North Dakota State Auditor', 'https://www.nd.gov/auditor/about-us'),
 'sw-nd-ins': ('North Dakota Insurance Department', 'https://www.insurance.nd.gov/'),
 'sw-nd-psc': ('North Dakota Public Service Commission', 'https://www.psc.nd.gov/commission'),
 'sw-nd-sos': ('North Dakota Secretary of State', 'https://www.sos.nd.gov/about-office'),
 'sw-nd-dpi': ('North Dakota Department of Public Instruction', 'https://www.nd.gov/dpi/state-superintendent'),
 'sw-nd-tre': ('North Dakota State Treasurer', 'https://www.treasurer.nd.gov/'),
 'sw-nd-agr': ('North Dakota Department of Agriculture', 'https://www.ndda.nd.gov/divisions/office-agriculture-commissioner'),
 'sw-nd-tax': ('North Dakota Office of State Tax Commissioner', 'https://www.tax.nd.gov/about/commissioner-bio'),
 # Ohio: one page lists every statewide elected official.
 'sw-oh': ('State of Ohio', 'https://ohio.gov/government/elected-officials'),
 # Oklahoma
 'sw-ok-lg': ('Office of the Lieutenant Governor of Oklahoma', 'https://oklahoma.gov/ltgovpinnell.html'),
 'sw-ok-ag': ('Oklahoma Attorney General', 'https://oklahoma.gov/oag.html'),
 'sw-ok-tre': ('Oklahoma State Treasurer', 'https://oklahoma.gov/treasurer/inside-the-office/staff-directory.html'),
 'sw-ok-aud': ('Oklahoma State Auditor and Inspector', 'https://www.sai.ok.gov/'),
 'sw-ok-sde': ('Oklahoma State Department of Education', 'https://oklahoma.gov/education/state-board-of-education/superintendent-.html'),
 'sw-ok-lab': ('Oklahoma Department of Labor', 'https://oklahoma.gov/labor.html'),
 'sw-ok-oid': ('Oklahoma Insurance Department', 'https://www.oid.ok.gov/'),
 'sw-ok-occ': ('Oklahoma Corporation Commission', 'https://oklahoma.gov/occ.html'),
 # Oregon
 'sw-or-sos': ('Oregon Secretary of State', 'https://sos.oregon.gov/Pages/default.aspx'),
 'sw-or-tre': ('Oregon State Treasury', 'https://www.oregon.gov/treasury/Pages/About-Treasurer-Steiner.aspx'),
 'sw-or-ag': ('Oregon Department of Justice', 'https://www.doj.state.or.us/'),
 'sw-or-boli': ('Oregon Bureau of Labor and Industries', 'https://www.oregon.gov/boli/about/Pages/default.aspx'),
}

# (source key, state, office key, pattern, holders). holders is 1 for single-holder offices and the
# exact seat count for MULTI offices. Patterns run on the HTML-unescaped page with whitespace collapsed.
RULES = [
 ('sw-ms-lg', 'MS', 'lieutenantGovernor', r'<h4>Lt\. Gov\. '+N+r'</h4>', 1),
 ('sw-ms-ag', 'MS', 'attorneyGeneral', TITLE+r'Attorney General '+N+r' - Attorney General of Mississippi\s*</title>', 1),
 ('sw-ms-tre', 'MS', 'treasurer', r'<span class="x-anchor-text-primary">Treasurer '+N+r'</span>', 1),
 ('sw-ms-aud', 'MS', 'auditor', r'<h2>Our Results for<br><span>Mississippi</span></h2><p>State Auditor '+N+r' and his office', 1),
 ('sw-ms-agr', 'MS', 'agricultureCommissioner', r'<h3 class="dtq-team-content-name">Commissioner '+N+r'</h3> <div class="dtq-team-content-bio">Mississippi’s elected Commissioner of Agriculture and Commerce\.</div>', 1),
 ('sw-ms-ins', 'MS', 'insuranceCommissioner', r'>'+N+r', Mississippi’s \d+(?:st|nd|rd|th) Commissioner of Insurance and State Fire Marshal', 1),

 ('sw-mo-lg', 'MO', 'lieutenantGovernor', r'alt="Office of Missouri Lieutenant Governor '+N+r'"', 1),
 ('sw-mo-sos', 'MO', 'secretaryOfState', r'<div id="about" class="info-box"> <h3>About '+N+r'</h3>', 1),
 ('sw-mo-aud', 'MO', 'auditor', r'<h4 class="footer-link-header">About Us</h4> <ul class="link-menu"> <li><a href="/aboutus/auditor">'+N+r'</a></li>', 1),
 ('sw-mo-tre', 'MO', 'treasurer', r'aria-label="Link to About Treasurer '+N+r'"', 1),
 ('sw-mo-ag', 'MO', 'attorneyGeneral', r'<figcaption class="wp-element-caption">'+N+r' <br>Missouri Attorney General</figcaption>', 1),

 ('sw-mt-lg', 'MT', 'lieutenantGovernor', r'<a class="dropdown-item " href="About/LieutenantGovernor">Meet Lieutenant Governor '+N+r'</a>', 1),
 ('sw-mt-ag', 'MT', 'attorneyGeneral', r'href="https://dojmt\.gov/attorney-generals-office/about-[a-z-]+/"[^>]*><span[^>]*>About '+N+r'</span>', 1),
 ('sw-mt-aud', 'MT', 'auditor', r'<meta name="description" content="COMMISSIONER [A-Z .\'-]+ On [A-Za-z]+ \d+\w*, \d{4}, '+N+r' was elected as the Treasure State’s \d+(?:st|nd|rd|th) State Auditor', 1),
 ('sw-mt-opi', 'MT', 'superintendentOfPublicInstruction', r'<span class="agency-slogan d-block">'+N+r', State Superintendent</span>', 1),

 ('sw-ne', 'NE', 'lieutenantGovernor', r'<h2 class="h3">Lieutenant Governor '+N+r'</h2>', 1),
 ('sw-ne', 'NE', 'secretaryOfState', r'<h2 class="h3">Secretary of State '+N+r'</h2>', 1),
 ('sw-ne', 'NE', 'treasurer', r'<h2 class="h3">State Treasurer '+N+r'</h2>', 1),
 ('sw-ne', 'NE', 'attorneyGeneral', r'<h2 class="h3">Attorney General '+N+r'</h2>', 1),
 ('sw-ne', 'NE', 'auditor', r'<h2 class="h3">Auditor of Public Accounts '+N+r'</h2>', 1),

 ('sw-nv-lg', 'NV', 'lieutenantGovernor', r'<h1 class="title-display[^"]*">Nevada Lieutenant Governor '+N+r'</h1>', 1),
 ('sw-nv-ag', 'NV', 'attorneyGeneral', r'alt="State of Nevada Seal" /></a> <span>Nevada Attorney General '+N+r'</span>', 1),
 ('sw-nv-tre', 'NV', 'treasurer', r'<img src="/siteassets/images/treasurer-01\.jpg"[^>]*alt="Treasurer '+N+r'"', 1),
 ('sw-nv-con', 'NV', 'controller', r'<span class="AgencyTitle[^"]*">Nevada State Controller '+N+r'</span>', 1),

 ('sw-nj-lg', 'NJ', 'lieutenantGovernor', TITLE+r'Lt\. Governor '+N+r'\s*</title>', 1),

 ('sw-nm-lg', 'NM', 'lieutenantGovernor', r'<h1><span class="hero-kicker">Lieutenant Governor</span> '+N+r'</h1>', 1),
 ('sw-nm-sos', 'NM', 'secretaryOfState', TITLE+N+r' - New Mexico Secretary of State \| New Mexico Secretary of State\s*</title>', 1),
 ('sw-nm-tre', 'NM', 'treasurer', r'<h1 class="[^"]*" data-testId="heading-tag">Meet New Mexico State Treasurer '+N+r', ', 1),
 ('sw-nm-aud', 'NM', 'auditor', r'<a href="mailto:[A-Za-z.]+@osa\.nm\.gov">Auditor '+N+r'</a>', 1),
 ('sw-nm-slo', 'NM', 'landCommissioner', TITLE+r'NM State Land Office \| Commissioner '+N+r'\s*</title>', 1),

 ('sw-ny-ag', 'NY', 'attorneyGeneral', r'<meta name="description" content="'+N+r' is the \d+(?:st|nd|rd|th) Attorney General of the state of New York\.', 1),
 ('sw-ny-osc', 'NY', 'comptroller', TITLE+r'Office of the New York State Comptroller \| '+N+r'\s*</title>', 1),

 ('sw-nc', 'NC', 'lieutenantGovernor', r'<h3 class="app-card__title"><a href="https://ltgov\.nc\.gov/">Lieutenant Governor '+N+r'</a></h3>', 1),
 ('sw-nc', 'NC', 'attorneyGeneral', r'<a href="https://ncdoj\.gov/">Attorney General: '+N+r'</a>', 1),
 ('sw-nc', 'NC', 'agricultureCommissioner', r'<a href="https://www\.ncagr\.gov/">Commissioner of Agriculture: '+N+r'</a>', 1),
 ('sw-nc', 'NC', 'insuranceCommissioner', r'<a href="https://ncdoi\.gov">Commissioner of Insurance: '+N+r'</a>', 1),
 ('sw-nc', 'NC', 'laborCommissioner', r'<a href="https://www\.labor\.nc\.gov/">Commissioner of Labor: '+N+r'</a>', 1),
 ('sw-nc', 'NC', 'secretaryOfState', r'<a href="https://www\.sosnc\.gov/">Secretary of State: '+N+r'</a>', 1),
 ('sw-nc', 'NC', 'auditor', r'<a href="https://www\.auditor\.nc\.gov/">State Auditor: '+N+r'</a>', 1),
 ('sw-nc', 'NC', 'treasurer', r'<a href="https://www\.nctreasurer\.gov/">State Treasurer: '+N+r'</a>', 1),
 ('sw-nc', 'NC', 'superintendentOfPublicInstruction', r'<a href="https://www\.dpi\.nc\.gov/">Superintendent of Public Instruction: '+N+r'</a>', 1),

 ('sw-nd-lg', 'ND', 'lieutenantGovernor', TITLE+r'Lt\. Governor '+N+r' \| North Dakota Office of the Governor\s*</title>', 1),
 ('sw-nd-ag', 'ND', 'attorneyGeneral', r'<span class="ubermenu-target-title ubermenu-target-text">Attorney General '+N+r'</span>', 1),
 ('sw-nd-aud', 'ND', 'auditor', r'<a href="https://www\.nd\.gov/auditor/about-[a-z-]+">Learn more about State Auditor '+N+r' </a>', 1),
 ('sw-nd-ins', 'ND', 'insuranceCommissioner', r'<a href="/about-us/commissioner-[a-z-]+" role="menuitem" class="nav-link">Commissioner '+N+r'</a>', 1),
 ('sw-nd-psc', 'ND', 'publicServiceCommissioner', r'<button class="nav-link[^"]*" id="tabs-inline-blockndit-tabs-[\w-]+" [^>]*data-text="'+N+r'(?: \(Current Chair\))?"', 3),
 ('sw-nd-sos', 'ND', 'secretaryOfState', r'<img class="align-right" src="/sites/www/files/documents/about/[\w-]+\.png" alt="'+N+r' Secretary of State"', 1),
 ('sw-nd-dpi', 'ND', 'superintendentOfPublicInstruction', r'alt="North Dakota State Superintendent '+N+r'"', 1),
 ('sw-nd-tre', 'ND', 'treasurer', r'<a href="/meet-treasurer-0" class="btn btn-slider" > Meet '+N+r', State Treasurer </a>', 1),
 ('sw-nd-agr', 'ND', 'agricultureCommissioner', r'alt="'+N+r', Agriculture Commissioner"', 1),
 ('sw-nd-tax', 'ND', 'taxCommissioner', r'<img class="align-left" src="/sites/www/files/documents/about/commissioner-pics/[\w-]+\.jpg" [^<>]*title="Photo of Commissioner '+N+r'">', 1),

 ('sw-oh', 'OH', 'lieutenantGovernor', r'oh-bio__name oh-clamped-txt">Lt\. Governor '+N+r'</h3>', 1),
 ('sw-oh', 'OH', 'attorneyGeneral', r'oh-bio__name oh-clamped-txt">Attorney General '+N+r'</h3>', 1),
 ('sw-oh', 'OH', 'auditor', r'oh-bio__name oh-clamped-txt">Auditor of State '+N+r'</h3>', 1),
 ('sw-oh', 'OH', 'secretaryOfState', r'oh-bio__name oh-clamped-txt">Secretary of State '+N+r'</h3>', 1),
 ('sw-oh', 'OH', 'treasurer', r'oh-bio__name oh-clamped-txt">Treasurer of State '+N+r'</h3>', 1),

 ('sw-ok-lg', 'OK', 'lieutenantGovernor', TITLE+r'Lieutenant Governor '+N+r' \(\d+\)\s*</title>', 1),
 ('sw-ok-ag', 'OK', 'attorneyGeneral', r'<p class="mm-two-description-header">Learn about Oklahoma Attorney General '+N+r' — ', 1),
 ('sw-ok-tre', 'OK', 'treasurer', r'alt="'+N+r' - Oklahoma State Treasurer"', 1),
 ('sw-ok-aud', 'OK', 'auditor', r'<h1>Oklahoma State <br> Auditor & Inspector</h1> <p><p><strong>'+N+r'(?:, CPA)?</strong></p>', 1),
 ('sw-ok-sde', 'OK', 'superintendentOfPublicInstruction', r'alt="Photo of Superintendent '+N+r'"', 1),
 ('sw-ok-lab', 'OK', 'laborCommissioner', r'alt="Commissioner '+N+r', Oklahoma Department of Labor"', 1),
 ('sw-ok-oid', 'OK', 'insuranceCommissioner', r'>Meet Insurance Commissioner '+N+r'</a>', 1),
 ('sw-ok-occ', 'OK', 'corporationCommissioner', r'<div class="cmp-card__heading"> <p>(?:CHAIRMAN|VICE CHAIRMAN|COMMISSIONER)</p> <h2>'+N+r'</h2>', 3),

 ('sw-or-sos', 'OR', 'secretaryOfState', r'alt="Oregon Secretary of State, '+N+r'"', 1),
 ('sw-or-tre', 'OR', 'treasurer', r'<h1>About Treasurer [A-Za-z\'-]+</h1> <i[^>]*>'+N+r' is Oregon’s \d+(?:st|nd|rd|th) Treasurer\.', 1),
 ('sw-or-ag', 'OR', 'attorneyGeneral', r'<meta name="description" content="Attorney General '+N+r'">', 1),
 ('sw-or-boli', 'OR', 'laborCommissioner', r'<p>Learn more about Labor Commissioner '+N+r'</p>', 1),
]

# Elected offices whose official site refused retrieval with USER_AGENT (bot challenge, 403 or
# missing page) in November 2026: (state, office) -> (publisher, url, reason). Never filled from elsewhere.
BLOCKED = {
 ('MS', 'secretaryOfState'): ('Mississippi Secretary of State', 'https://www.sos.ms.gov/', 'Cloudflare block page (HTTP 403)'),
 ('MT', 'secretaryOfState'): ('Montana Secretary of State', 'https://sosmt.gov/', 'firewall block page (HTTP 403)'),
 ('NV', 'secretaryOfState'): ('Nevada Secretary of State', 'https://www.nvsos.gov/sos', 'Incapsula request-unsuccessful page'),
 ('NM', 'attorneyGeneral'): ('New Mexico Department of Justice', 'https://nmdoj.gov/', 'Cloudflare challenge (HTTP 403)'),
 ('NY', 'lieutenantGovernor'): ('Office of the Governor of New York', 'https://www.governor.ny.gov/about-lieutenant-governor', 'Access denied (HTTP 403); no other page of the governor\'s site names the lieutenant governor'),
}
# Sources read from an imported browser DOM observation; none in this module.
BROWSER = set()


def _statewide():
    out = {st: {} for st in STATES}
    for _, st, office, _, _ in RULES:
        out[st][office] = 'collected'
    for (st, office), (publisher, url, reason) in BLOCKED.items():
        assert office not in out[st], (st, office)
        out[st][office] = 'not-collected'
        out[st].setdefault('blockers', []).append(f'{OFFICES[office][0]}: {publisher} ({url}) refused automated retrieval: {reason}')
    return out


STATEWIDE = _statewide()
# New Hampshire elects no executive officer statewide besides the governor (the Executive Council is elected by district).
assert all(len([r for r in RULES if r[1:3] == (st, office)]) == 1 for st, office in {r[1:3] for r in RULES}), 'One rule per office'
assert all((holders > 1) == (office in MULTI) for _, _, office, _, holders in RULES)
assert {key for key, *_ in RULES} == set(SOURCES)

FORBIDDEN = re.compile(r'\b(?:Office|Governor|Lieutenant|Secretary|Attorney|General|Treasurer|Auditor|Comptroller|Controller|'
                       r'Commissioner|Superintendent|State|Home|Welcome|About|Meet|Department|Mississippi|Missouri|Montana|'
                       r'Nebraska|Nevada|New|North|Ohio|Oklahoma|Oregon)\b')


def names(raw, pattern, holders, label):
    """The distinct names one rule extracts; exactly `holders` of them or the build stops."""
    page = ' '.join(html.unescape(raw.decode('utf-8', 'replace')).split())
    found = []
    for m in re.finditer(pattern, page):
        name = ' '.join(m.group('name').split())
        if name not in found: found.append(name)
    assert len(found) == holders, (label, f'Expected {holders} distinct name(s)', found)
    for name in found:
        assert 2 <= len(name.split()) <= 6 and not FORBIDDEN.search(name), (label, name)
    return found


def parse(key, raw, source):
    rows = []
    for k, st, office, pattern, holders in RULES:
        if k != key: continue
        title = OFFICES[office][0]
        found = names(raw, pattern, holders, (st, office))
        for n, name in enumerate(found, 1):
            id = f'{st.lower()}-{office}' + (f'-{n}' if office in MULTI else '')
            row = record(source, id, name, st, 'state', BODY.format(NAMES[st]), office=title, website=source['url'])
            rows.append(row)
    assert rows, ('No rules for source', key)
    return rows


def collect(acquire, offline):
    rows, sources = [], []
    for key, (publisher, url) in SOURCES.items():
        raw, source = acquire(key, publisher, url, offline, **({} if key in BROWSER else dict(user_agent=USER_AGENT)))
        rows.extend(parse(key, raw, source))
        sources.append(source)
    return rows, sources
