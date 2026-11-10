"""Elected statewide executive officers other than the governor: PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY.

Sources are official state pages only: a state page that lists the statewide
elected officers where one exists (RI.gov, SC.gov, the South Dakota Secretary
of State, the Wisconsin Board of Commissioners of Public Lands), otherwise each
office's own website. Each rule names one element (page title, heading, meta
tag, image alt or menu link) and a pattern that must yield exactly the expected
number of distinct names. A missing, extra or conflicting match stops the build.

Which offices each state elects is documented, with its official citation, in
docs/STATEWIDE-D.md. Tennessee elects no statewide executive officer other than
the governor (its secretary of state, treasurer and comptroller are chosen by the
General Assembly, and the lieutenant governor is the Speaker of the Senate), so
its declaration is empty. Officeholders-elect from the November 2026 election
are not recorded until the official source shows them in office.
"""
import html
import re
from build import record
from statewide import OFFICES, MULTI

NAMES = dict(PA='Pennsylvania', RI='Rhode Island', SC='South Carolina', SD='South Dakota', TN='Tennessee', TX='Texas',
             UT='Utah', VT='Vermont', VA='Virginia', WA='Washington', WV='West Virginia', WI='Wisconsin', WY='Wyoming')

N = r"(?P<name>[A-Z][A-Za-z.,'’\- ]+?)"
TITLE = r'<title[^>]*>\s*'
PARTY = r' \([A-Z]\)\s*</strong>'

SOURCES = {
    'sw-pa-ltgov': ('Office of the Lieutenant Governor of Pennsylvania', 'https://www.pa.gov/ltgovernor'),
    'sw-pa-ag': ('Pennsylvania Office of Attorney General', 'https://www.attorneygeneral.gov/'),
    'sw-pa-auditor': ('Pennsylvania Department of the Auditor General', 'https://www.paauditor.gov/'),
    'sw-pa-treasurer': ('Pennsylvania Treasury', 'https://www.patreasury.gov/'),
    'sw-ri-officials': ('State of Rhode Island', 'https://www.ri.gov/officials/'),
    'sw-sc-officers': ('State of South Carolina', 'https://sc.gov/government/getting-know-your-government/elected-officials/constitutional-officers'),
    'sw-sd-officials': ('South Dakota Secretary of State', 'https://sdsos.gov/elections-voting/election-resources/current-elected-officials.aspx'),
    'sw-tx-ltgov': ('Office of the Lieutenant Governor of Texas', 'https://www.ltgov.texas.gov/'),
    'sw-tx-ag': ('Office of the Attorney General of Texas', 'https://www.texasattorneygeneral.gov/about-office'),
    'sw-tx-comptroller': ('Texas Comptroller of Public Accounts', 'https://comptroller.texas.gov/about/bio.php'),
    'sw-tx-glo': ('Texas General Land Office', 'https://www.glo.texas.gov/'),
    'sw-tx-agriculture': ('Texas Department of Agriculture', 'https://texasagriculture.gov/'),
    'sw-tx-rrc': ('Railroad Commission of Texas', 'https://www.rrc.texas.gov/about-us/commissioners/'),
    'sw-ut-ltgov': ('Office of the Lieutenant Governor of Utah', 'https://ltgovernor.utah.gov/'),
    'sw-ut-ag': ('Utah Office of the Attorney General', 'https://attorneygeneral.utah.gov/'),
    'sw-ut-auditor': ('Utah Office of the State Auditor', 'https://auditor.utah.gov/'),
    'sw-ut-treasurer': ('Utah Office of State Treasurer', 'https://treasurer.utah.gov/'),
    'sw-vt-ltgov': ('Office of the Lieutenant Governor of Vermont', 'https://ltgov.vermont.gov/'),
    'sw-vt-sos': ('Vermont Secretary of State', 'https://sos.vermont.gov/secretarys-desk'),
    'sw-vt-treasurer': ('Office of the Vermont State Treasurer', 'https://www.vermonttreasurer.gov/'),
    'sw-vt-auditor': ('Office of the Vermont State Auditor', 'https://auditor.vermont.gov/about-us/biographies'),
    'sw-vt-ag': ('Office of the Vermont Attorney General', 'https://ago.vermont.gov/'),
    'sw-va-ltgov': ('Office of the Lieutenant Governor of Virginia', 'https://www.ltgov.virginia.gov/'),
    'sw-va-ag': ('Office of the Attorney General of Virginia', 'https://www.oag.state.va.us/'),
    'sw-wa-ltgov': ('Office of the Lieutenant Governor of Washington', 'https://www.ltgov.wa.gov/'),
    'sw-wa-sos': ('Washington Secretary of State', 'https://www.sos.wa.gov/'),
    'sw-wa-treasurer': ('Office of the Washington State Treasurer', 'https://tre.wa.gov/'),
    'sw-wa-auditor': ('Office of the Washington State Auditor', 'https://sao.wa.gov/'),
    'sw-wa-ag': ('Washington State Office of the Attorney General', 'https://www.atg.wa.gov/'),
    'sw-wa-lands': ('Washington State Department of Natural Resources', 'https://dnr.wa.gov/'),
    'sw-wa-ospi': ('Washington Office of Superintendent of Public Instruction', 'https://ospi.k12.wa.us/'),
    'sw-wa-insurance': ('Washington Office of the Insurance Commissioner', 'https://www.insurance.wa.gov/'),
    'sw-wv-sos': ('West Virginia Secretary of State', 'https://sos.wv.gov/about-secretary'),
    'sw-wv-ag': ('Office of the West Virginia Attorney General', 'https://ago.wv.gov/'),
    'sw-wv-treasurer': ('West Virginia State Treasurer', 'https://wvtreasury.gov/'),
    'sw-wv-auditor': ('West Virginia State Auditor', 'https://www.wvsao.gov/'),
    'sw-wv-agriculture': ('West Virginia Department of Agriculture', 'https://agriculture.wv.gov/'),
    'sw-wi-ltgov': ('Office of the Lieutenant Governor of Wisconsin', 'https://evers.wi.gov/ltgov/Pages/default.aspx'),
    'sw-wi-bcpl': ('Wisconsin Board of Commissioners of Public Lands', 'https://bcpl.wisconsin.gov/Pages/AboutBCPL.aspx'),
    'sw-wi-dpi': ('Wisconsin Department of Public Instruction', 'https://dpi.wi.gov/'),
    'sw-wy-sos': ('Wyoming Secretary of State', 'https://sos.wyo.gov/AboutUs/AboutSecretary.aspx'),
    'sw-wy-auditor': ('Wyoming State Auditor', 'https://sao.wyo.gov/'),
    'sw-wy-treasurer': ('Wyoming State Treasurer', 'https://statetreasurer.wyo.gov/'),
    'sw-wy-education': ('Wyoming Department of Education', 'https://edu.wyoming.gov/'),
}

# (source key, state, office key, pattern, expected distinct names). Patterns run on the
# HTML-unescaped page with whitespace collapsed and zero-width characters removed.
RULES = [
    ('sw-pa-ltgov', 'PA', 'lieutenantGovernor', r'<meta name="copapwp-page-title" content="'+N+r'"/>', 1),
    ('sw-pa-ag', 'PA', 'attorneyGeneral', r'<img src="[^"]+" alt="AG '+N+r'" width=', 1),
    ('sw-pa-auditor', 'PA', 'auditor', r'class="hero-auditor-img" src="[^"]+" alt="PA Auditor General '+N+r'">', 1),
    ('sw-pa-treasurer', 'PA', 'treasurer', r'<meta property="og:site_name" content="Pennsylvania Treasury, '+N+r' - State Treasurer" />', 1),

    ('sw-ri-officials', 'RI', 'lieutenantGovernor', r'<h3 class="blue-sub-header">Lt\. Governor</h3> <h5>'+N+r'</h5>', 1),
    ('sw-ri-officials', 'RI', 'secretaryOfState', r'<h3 class="blue-sub-header">Secretary of State</h3> <h5>'+N+r'</h5>', 1),
    ('sw-ri-officials', 'RI', 'attorneyGeneral', r'<h3 class="blue-sub-header">Attorney General</h3> <h5>'+N+r'</h5>', 1),
    ('sw-ri-officials', 'RI', 'treasurer', r'<h3 class="blue-sub-header">General Treasurer</h3> <h5>'+N+r'</h5>', 1),

    ('sw-sc-officers', 'SC', 'lieutenantGovernor', r'<h3 data-item="0">Lt\. Governor '+N+r'</h3>', 1),
    ('sw-sc-officers', 'SC', 'secretaryOfState', r'<h3 data-item="0">Secretary of State '+N+r'</h3>', 1),
    ('sw-sc-officers', 'SC', 'treasurer', r'<h3 data-item="0">Treasurer '+N+r'</h3>', 1),
    ('sw-sc-officers', 'SC', 'attorneyGeneral', r'<h3 data-item="0">Attorney General '+N+r'</h3>', 1),
    ('sw-sc-officers', 'SC', 'comptroller', r'<h3 data-item="0">Comptroller General '+N+r'</h3>', 1),
    ('sw-sc-officers', 'SC', 'superintendentOfPublicInstruction', r'<h3 data-item="0">State Superintendent of Education '+N+r'</h3>', 1),
    ('sw-sc-officers', 'SC', 'agricultureCommissioner', r'<h3 data-item="0">Commissioner of Agriculture '+N+r'</h3>', 1),

    ('sw-sd-officials', 'SD', 'lieutenantGovernor', r'<p><strong>Lt\. Governor '+N+PARTY, 1),
    ('sw-sd-officials', 'SD', 'secretaryOfState', r'<p><strong>Secretary of State '+N+PARTY, 1),
    ('sw-sd-officials', 'SD', 'attorneyGeneral', r'<p><strong>Attorney General '+N+PARTY, 1),
    ('sw-sd-officials', 'SD', 'auditor', r'<p><strong>State Auditor '+N+PARTY, 1),
    ('sw-sd-officials', 'SD', 'treasurer', r'<p><strong>State Treasurer '+N+PARTY, 1),
    ('sw-sd-officials', 'SD', 'landCommissioner', r'<p><strong>Commissioner of School and Public Lands<br> '+N+PARTY, 1),
    ('sw-sd-officials', 'SD', 'publicServiceCommissioner', r'<p><strong>Public Utilities Commissioner<br> '+N+PARTY, 3),

    ('sw-tx-ltgov', 'TX', 'lieutenantGovernor', TITLE+r'Home - Lieutenant Governor '+N+r'\s*</title>', 1),
    ('sw-tx-ag', 'TX', 'attorneyGeneral', r'<meta name="description" content="'+N+r' is the \d+\w+ Attorney General of Texas\.', 1),
    ('sw-tx-comptroller', 'TX', 'comptroller', TITLE+N+r' - Texas Comptroller of Public Accounts\s*</title>', 1),
    ('sw-tx-glo', 'TX', 'landCommissioner', r"<span class='d-block show-for-large'>Commissioner "+N+r'(?:, M\.D\.)?</span>', 1),
    ('sw-tx-agriculture', 'TX', 'agricultureCommissioner', r'alt="Texas Agriculture Commissioner '+N+r'"', 1),
    ('sw-tx-rrc', 'TX', 'railroadCommissioner', r'<h4 style="text-align: center;">'+N+r'</h4> <h5 style="text-align: center;">(?:Chairman|Commissioner)</h5>', 3),

    ('sw-ut-ltgov', 'UT', 'lieutenantGovernor', TITLE+r'Home - Lt\. Governor '+N+r'\s*</title>', 1),
    ('sw-ut-ag', 'UT', 'attorneyGeneral', r'<h2 class="elementor-heading-title elementor-size-default">Utah Attorney General</h2> </div> </div> <div [^>]+> <div class="elementor-widget-container"> <h2 class="elementor-heading-title elementor-size-default">'+N+r'</h2>', 1),
    ('sw-ut-auditor', 'UT', 'auditor', r'<a href="/about-us/meet-auditor-[a-z-]+/">Meet Auditor '+N+r'</a>', 1),
    ('sw-ut-treasurer', 'UT', 'treasurer', r'<a href="https://treasurer\.utah\.gov/about/state-treasurer-[a-z-]+/"><span>State Treasurer '+N+r'<i ', 1),

    ('sw-vt-ltgov', 'VT', 'lieutenantGovernor', r'<img alt="Lieutenant Governor '+N+r'\."', 1),
    ('sw-vt-sos', 'VT', 'secretaryOfState', r'<p><strong>'+N+r', Secretary of State</strong></p>', 1),
    ('sw-vt-treasurer', 'VT', 'treasurer', r'<h1><em><strong>Welcome to the Office of Vermont State Treasurer '+N+r'</strong></em></h1>', 1),
    ('sw-vt-auditor', 'VT', 'auditor', r'<h3>State Auditor '+N+r'(?:, J\.D\.)?</h3>', 1),
    ('sw-vt-ag', 'VT', 'attorneyGeneral', r'<span class="usa-logo__slogan">'+N+r'</span> <a href="/" class="usa-logo__site-name" title="Home"> Office of the Vermont Attorney General', 1),

    ('sw-va-ltgov', 'VA', 'lieutenantGovernor', r'<span class="office-name">Lieutenant Governor of Virginia</span> '+N+r' </a>', 1),
    ('sw-va-ag', 'VA', 'attorneyGeneral', r'<meta name="twitter:title" content="Attorney General '+N+r'" />', 1),

    ('sw-wa-ltgov', 'WA', 'lieutenantGovernor', TITLE+r'Lieutenant Governor '+N+r'\s*</title>', 1),
    ('sw-wa-sos', 'WA', 'secretaryOfState', r'href="/about-office/secretary-state-[a-z-]+">Secretary of State '+N+r' Biography</a>', 1),
    ('sw-wa-treasurer', 'WA', 'treasurer', r'alt="Washington State Treasurer - '+N+r'"', 1),
    ('sw-wa-auditor', 'WA', 'auditor', r'href="/about-sao/state-auditor-[a-z-]+" title="State Auditor '+N+r'">', 1),
    ('sw-wa-ag', 'WA', 'attorneyGeneral', r'<section role="main" id="block-displayspresentattorneygeneralname" class="block block-block"> <div class="container"> <div class="row"> <div class="col-md-12"> <h2 class="block-title">Attorney General</h2> </div> </div> </div> <div class="space20"></div> <div class="content"> <div><p>'+N+r'</p>', 1),
    ('sw-wa-lands', 'WA', 'landCommissioner', r'<h2>Commissioner of Public Lands</h2> </div> <div class="content"> <div class="[^"]*field--name-body[^"]*"><p>Commissioner '+N+r' is ', 1),
    ('sw-wa-ospi', 'WA', 'superintendentOfPublicInstruction', r'<a class="dropdown-item fw-bold" href="/about-ospi/superintendent-[a-z-]+"> Superintendent '+N+r' <br>', 1),
    ('sw-wa-insurance', 'WA', 'insuranceCommissioner', r'<a href="/about-us/about-(?!us")[a-z-]+" class="dropdown-item" [^>]*>About '+N+r'</a>', 1),

    ('sw-wv-sos', 'WV', 'secretaryOfState', r'<h2>'+N+r"</h2><h3>West Virginia's \d+\w+ Secretary of State</h3>", 1),
    ('sw-wv-ag', 'WV', 'attorneyGeneral', TITLE+r'Office of the WV Attorney General '+N+r'\s*</title>', 1),
    ('sw-wv-treasurer', 'WV', 'treasurer', r'<div class="tname">'+N+r'</div> <div class="ttitle">West Virginia State Treasurer</div>', 1),
    ('sw-wv-auditor', 'WV', 'auditor', r"West Virginia State Auditor's Office</div> <div class=\"text-white fs-5\">Auditor "+N+r'</div>', 1),
    ('sw-wv-agriculture', 'WV', 'agricultureCommissioner', r'<h1 class="visually-hidden">West Virginia Department of Agriculture, '+N+r', Commissioner</h1>', 1),

    ('sw-wi-ltgov', 'WI', 'lieutenantGovernor', r'<img class="dot-logo" src="[^"]+" alt="Lieutenant Governor '+N+r'"', 1),
    ('sw-wi-bcpl', 'WI', 'secretaryOfState', r'<figcaption> <h3>'+N+r'</h3>Secretary of State</figcaption>', 1),
    ('sw-wi-bcpl', 'WI', 'treasurer', r'<figcaption> <h3>'+N+r'</h3>State Treasurer</figcaption>', 1),
    ('sw-wi-bcpl', 'WI', 'attorneyGeneral', r'<figcaption> <h3>'+N+r'</h3>Attorney General</figcaption>', 1),
    ('sw-wi-dpi', 'WI', 'superintendentOfPublicInstruction', r'<h2 class="homepage-widget__header-super-title">State Superintendent of Public Instruction</h2> .{0,600}?alt="Head shot of (?:Dr\. )?'+N+r'"', 1),

    ('sw-wy-sos', 'WY', 'secretaryOfState', r'class="picture right secretary-headshot" src="[^"]+" alt="'+N+r', Wyoming Secretary of State"', 1),
    ('sw-wy-auditor', 'WY', 'auditor', r'<h4 style="[^"]*">'+N+r'</h4> <h5>State Auditor</h5>', 1),
    ('sw-wy-treasurer', 'WY', 'treasurer', r'<img class="brxe-image block-home-intro__image" alt="'+N+r'"', 1),
    ('sw-wy-education', 'WY', 'superintendentOfPublicInstruction', r'alt="Headshot of '+N+r', Wyoming Superintendent of Public Instruction"', 1),
]

# Sources that are the office's own website; their rows carry it as `website`.
OFFICE_SITES = {k for k in SOURCES if k not in {'sw-ri-officials', 'sw-sc-officers', 'sw-sd-officials', 'sw-wi-bcpl'}}
BROWSER = set()

STATEWIDE = {st: {} for st in NAMES}
for _key, _st, _office, _pattern, _count in RULES:
    STATEWIDE[_st][_office] = 'collected'
for _item in STATEWIDE.values():
    if _item: _item['blockers'] = []

assert set(SOURCES) == {r[0] for r in RULES}
assert all(office in OFFICES and (count == 1) == (office not in MULTI) for _, _, office, _, count in RULES)
assert len({(st, office) for _, st, office, _, _ in RULES}) == len(RULES)

BODY = '{} Executive'
USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'
NOT_A_NAME = re.compile(r'\b(?:Office|Governor|Lieutenant|Secretary|Attorney|General|Treasurer|Auditor|Comptroller|Commissioner|'
                        r'Superintendent|State|Home|Welcome|About|Us|Biography)\b')


def page_text(raw):
    page = html.unescape(raw.decode('utf-8', 'replace')).replace('​', '').replace('﻿', '')
    return ' '.join(page.split())


def names(pattern, page, count, label):
    """The distinct names a rule extracts, in page order; exactly `count` or the build stops."""
    found = []
    for m in re.finditer(pattern, page):
        name = ' '.join(m.group('name').split()).rstrip(',')
        if name not in found: found.append(name)
    assert len(found) == count, (label, f'Expected {count} distinct name(s)', found)
    for name in found:
        assert 2 <= len(name.replace(', Jr.', '').split()) <= 5 and not NOT_A_NAME.search(name), (label, name)
    return found


def parse(key, raw, source):
    page = page_text(raw)
    rows = []
    for rule_key, st, office, pattern, count in RULES:
        if rule_key != key: continue
        for n, name in enumerate(names(pattern, page, count, (key, st, office)), 1):
            id = f'{st.lower()}-{office}' + (f'-{n}' if office in MULTI else '')
            row = record(source, id, name, st, 'state', BODY.format(NAMES[st]), office=OFFICES[office][0],
                         website=source['url'] if key in OFFICE_SITES else None)
            rows.append(row)
    assert rows, (key, 'No rules for source')
    return rows


def collect(acquire, offline):
    rows, sources = [], []
    for key, (publisher, url) in SOURCES.items():
        raw, source = acquire(key, publisher, url, offline, **({} if key in BROWSER else dict(user_agent=USER_AGENT)))
        rows.extend(parse(key, raw, source))
        sources.append(source)
    return rows, sources
