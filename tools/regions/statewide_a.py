"""Elected statewide executive officers other than the governor: AL AK AZ AR CA CO CT DE FL GA HI.

Sources are official state pages: a state page that lists the elected officials
(Arkansas, Colorado, Delaware, Georgia) or each office's own website. Every rule
names one element per officeholder (a heading, title, meta tag, caption or menu
link) and runs on the HTML-unescaped page with comments removed and whitespace
collapsed. Each rule must match, every matched office title must be known, and
each office must yield exactly its expected number of distinct holders; anything
else stops the build. Offices whose official site refused retrieval are listed in
BLOCKED and recorded as not collected. See docs/STATEWIDE-A.md.
"""
import html
import re
from build import record
from statewide import OFFICES, MULTI

NAMES = dict(AL='Alabama', AK='Alaska', AZ='Arizona', AR='Arkansas', CA='California', CO='Colorado', CT='Connecticut',
             DE='Delaware', FL='Florida', GA='Georgia', HI='Hawaii')
USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'
NAME = r'(?P<name>[^<>"]+?)'
ORDINAL = r'(?P<district>\d+(?:st|nd|rd|th) Congressional District|At[- ]Large)'
WORDS = dict(First='1', Second='2', Third='3', Fourth='4')

# key: dict(state, publisher, url, read=[(pattern, office key | {source title: office key or None}), ...],
#           expect={office key: number of holders}, within=optional pattern whose 'block' group is searched,
#           shared=seat labels several holders may hold at once, such as at-large seats).
# A 'seat' group is recorded verbatim as the row's district; a 'district' group is normalized by district().
# A title mapped to None (the governor) is read but not published by this module.
RULES = {
 'sw-al-ltgov': dict(state='AL', publisher='Office of the Lieutenant Governor of Alabama', url='https://ltgov.alabama.gov/',
     read=[(r'<meta property="og:site_name" content="Lt\. Governor '+NAME+r'"/?>', 'lieutenantGovernor')]),
 'sw-al-sos': dict(state='AL', publisher='Alabama Secretary of State', url='https://www.sos.alabama.gov/',
     read=[(r'<h1>Official Website of the Alabama Secretary of State</h1> <span class="banner-body">'+NAME+r'</span>', 'secretaryOfState')]),
 'sw-al-ag': dict(state='AL', publisher='Office of the Alabama Attorney General', url='https://www.alabamaag.gov/',
     read=[(r'<meta name="description" content="'+NAME+r' was sworn in as the [a-z-]+ Attorney General of the State of Alabama ', 'attorneyGeneral')]),
 'sw-al-treasurer': dict(state='AL', publisher='Office of the Alabama State Treasurer', url='https://treasury.alabama.gov/',
     read=[(r'<meta property="og:site_name" content="Office of the Alabama State Treasurer - '+NAME+r'" />', 'treasurer')]),
 'sw-al-auditor': dict(state='AL', publisher='Office of the Alabama State Auditor', url='https://auditor.alabama.gov/',
     read=[(r'<p style="text-align: right;">- '+NAME+r', State Auditor</p>', 'auditor')]),
 'sw-al-agriculture': dict(state='AL', publisher='Alabama Department of Agriculture and Industries', url='https://agi.alabama.gov/',
     read=[(r'<h3 class="section-title">Meet Commissioner '+NAME+r'</h3>', 'agricultureCommissioner')]),
 'sw-al-psc': dict(state='AL', publisher='Alabama Public Service Commission', url='https://psc.alabama.gov/',
     read=[(r'<figcaption class="widget-image-caption wp-caption-text">Commissioner '+NAME+r', (?:President|Place One|Place Two)</figcaption>', 'publicServiceCommissioner')],
     expect={'publicServiceCommissioner': 3}),
 'sw-ak-ltgov': dict(state='AK', publisher='Office of the Lieutenant Governor of Alaska', url='https://ltgov.alaska.gov/',
     read=[(r'<a href="https://ltgov\.alaska\.gov/meet-lt-governor-[a-z-]+/">Meet Lt\. Governor '+NAME+r'</a>', 'lieutenantGovernor')]),
 'sw-az-ag': dict(state='AZ', publisher='Arizona Attorney General', url='https://www.azag.gov/',
     read=[(r'<a href="/[a-z-]+" class="nav-link--[a-z-]+" data-drupal-link-system-path="node/\d+">'+NAME+r', Attorney General</a>', 'attorneyGeneral')]),
 'sw-az-treasurer': dict(state='AZ', publisher='Arizona State Treasurer', url='https://www.aztreasury.gov/',
     read=[(r'>The Honorable '+NAME+r' serves as the \d+(?:st|nd|rd|th) Treasurer of Arizona\.', 'treasurer')]),
 'sw-az-acc': dict(state='AZ', publisher='Arizona Corporation Commission', url='https://www.azcc.gov/',
     read=[(r'<a href="/[A-Za-z-]+/biography" class="dropdown-item">(?:Chair |Vice Chair )?'+NAME+r'</a>', 'corporationCommissioner')],
     expect={'corporationCommissioner': 5}),
 'sw-ar': dict(state='AR', publisher='State of Arkansas', url='https://portal.arkansas.gov/elected-officials/',
     within=r'>Elected Officials for the State of Arkansas</h2>(?P<block>.*?)>Federal Elected Officials</h2>',
     read=[(r'<p class="elementor-heading-title elementor-size-default"><a href="[^"]*">(?P<title>[^<>]+?)</a></p> </div> </div> <div [^<>]*> <div class="elementor-widget-container"> <h3 class="elementor-heading-title elementor-size-default"><a href="[^"]*">'+NAME+r'</a></h3>',
            {'Governor of Arkansas': None, 'Lieutenant Governor': 'lieutenantGovernor', 'Secretary of State': 'secretaryOfState',
             'Attorney General': 'attorneyGeneral', 'Treasurer': 'treasurer', 'Auditor of State': 'auditor', 'Land Commissioner': 'landCommissioner'})]),
 'sw-ca-ltg': dict(state='CA', publisher='Office of the Lieutenant Governor of California', url='https://ltg.ca.gov/about/',
     read=[(r'<title>\s*About '+NAME+r' - Lieutenant Governor\s*</title>', 'lieutenantGovernor')]),
 'sw-ca-sos': dict(state='CA', publisher='California Secretary of State', url='https://www.sos.ca.gov/',
     read=[(r'<div id="header-office"> California Secretary of State </div> <div id="header-name"> '+NAME+r' </div>', 'secretaryOfState')]),
 'sw-ca-ag': dict(state='CA', publisher='California Department of Justice, Office of the Attorney General', url='https://oag.ca.gov/about',
     read=[(r'<h1 class="page-header">Attorney General '+NAME+r'</h1>', 'attorneyGeneral')]),
 'sw-ca-treasurer': dict(state='CA', publisher='California State Treasurer', url='https://www.treasurer.ca.gov/bio',
     read=[(r'<p>'+NAME+r' is California[’\']s \d+(?:st|nd|rd|th) State Treasurer\.', 'treasurer')]),
 'sw-ca-insurance': dict(state='CA', publisher='California Department of Insurance', url='https://www.insurance.ca.gov/0500-about-us/',
     read=[(r'<p>Information about Commissioner '+NAME+r'</p>', 'insuranceCommissioner')]),
 # The Board of Equalization homepage shows the State Controller, an ex officio member (sco.ca.gov refuses this agent).
# The board's four members are elected by district and, like other district-elected boards, are outside statewide scope.
 'sw-ca-boe': dict(state='CA', publisher='California State Board of Equalization', url='https://www.boe.ca.gov/',
     read=[(r'<div class="text-center text-white m-y-sm">'+NAME+r'<br><span class="h5 text-white">Controller</span></div>', 'controller')]),
 'sw-co': dict(state='CO', publisher='State of Colorado', url='https://www.colorado.gov/',
     within=r'<div id="block-footergovernment"[^<>]*>(?P<block>.*?)</ul>',
     read=[(r'<li><a href="[^"]+">(?P<title>Governor|Lt\. Governor|Attorney General|Secretary of State|State Treasurer) '+NAME+r'</a></li>',
            {'Governor': None, 'Lt. Governor': 'lieutenantGovernor', 'Attorney General': 'attorneyGeneral',
             'Secretary of State': 'secretaryOfState', 'State Treasurer': 'treasurer'})]),
 'sw-ct-ltgov': dict(state='CT', publisher='Office of the Lieutenant Governor of Connecticut', url='https://portal.ct.gov/lt-governor',
     read=[(r'<title>\s*Lieutenant Governor '+NAME+r' \| Office of the Lieutenant Governor \| CT\.GOV\s*</title>', 'lieutenantGovernor')]),
 'sw-ct-sots': dict(state='CT', publisher='Connecticut Secretary of the State', url='https://portal.ct.gov/sots',
     read=[(r'<h2 class="cg-c-section-title[^"]*">Secretary of the State '+NAME+r'</h2>', 'secretaryOfState')]),
 # The Attorney General's homepage links "About the Attorney General" to this biography page, whose URL names the officeholder.
 'sw-ct-ag': dict(state='CT', publisher='Connecticut Office of the Attorney General', url='https://portal.ct.gov/ag/about-the-ag/william-tong-biography-page',
     read=[(r'<h1 class=show-for-sr>Attorney General '+NAME+r'</h1>', 'attorneyGeneral')]),
 'sw-ct-treasurer': dict(state='CT', publisher='Connecticut Office of the Treasurer', url='https://portal.ct.gov/ott',
     read=[(r'<title>\s*Connecticut Office of the Treasurer '+NAME+r'\s*</title>', 'treasurer')]),
 'sw-ct-comptroller': dict(state='CT', publisher='Connecticut Office of the State Comptroller', url='https://osc.ct.gov/',
     read=[(r'<h5 class="font-weight-normal"> <a href="javascript:;">Comptroller '+NAME+r'</a> </h5>', 'comptroller')]),
 'sw-de': dict(state='DE', publisher='State of Delaware', url='https://delaware.gov/guides/your-government/',
     read=[(r'<h5><a href="https://[a-z]+\.delaware\.gov/">(?P<title>Governor|Lt\. Governor|Attorney General|State Auditor|Insurance Commissioner|State Treasurer) '+NAME+r'</a></h5>',
            {'Governor': None, 'Lt. Governor': 'lieutenantGovernor', 'Attorney General': 'attorneyGeneral', 'State Auditor': 'auditor',
             'Insurance Commissioner': 'insuranceCommissioner', 'State Treasurer': 'treasurer'})]),
 # The Executive Office of the Governor's "Lieutenant Governor" menu link points to this page, whose URL names the officeholder.
 'sw-fl-ltgov': dict(state='FL', publisher='Executive Office of the Governor of Florida', url='https://www.flgov.com/eog/leadership/people/jay-collins',
     read=[(r'<div class="administration"><h2>Lieutenant Governor '+NAME+r'</h2><h3><time [^<>]*>[^<>]*</time> – Present</h3>', 'lieutenantGovernor')]),
 'sw-fl-ag': dict(state='FL', publisher='Office of the Florida Attorney General', url='https://www.myfloridalegal.com/',
     read=[(r'<li><a href="/ag-bio">Attorney General '+NAME+r'</a></li>', 'attorneyGeneral')]),
 'sw-fl-agriculture': dict(state='FL', publisher='Florida Department of Agriculture and Consumer Services', url='https://www.fdacs.gov/',
     read=[(r'<a href="https://www\.fdacs\.gov/About-Us/Meet-Commissioner-[A-Za-z-]+" [^<>]*>Learn More About Commissioner '+NAME+r'</a>', 'agricultureCommissioner')]),
 'sw-fl-cfo': dict(state='FL', publisher='Florida Department of Financial Services', url='https://www.myfloridacfo.com/about/meet-the-cfo',
     read=[(r'<h2 class="oh3"><strong>Meet your Chief Financial Officer '+NAME+r'</strong> ?</h2>', 'chiefFinancialOfficer')]),
 'sw-ga': dict(state='GA', publisher='State of Georgia', url='https://georgia.gov/elected-officials',
     read=[(r'<h2 class="global-teaser__title"> '+NAME+r' </h2> <p class="global-teaser__description"> (?P<title>[^<>]+?) </p>',
            {'Governor': None, 'Lieutenant Governor': 'lieutenantGovernor', 'Attorney General': 'attorneyGeneral',
             'Secretary of State': 'secretaryOfState', 'State School Superintendent': 'superintendentOfPublicInstruction',
             'Commissioner of Agriculture': 'agricultureCommissioner', 'Commissioner of Insurance': 'insuranceCommissioner',
             'Commissioner of Labor': 'laborCommissioner', 'Public Service Commission Chairman': 'publicServiceCommissioner',
             'Public Service Commissioner': 'publicServiceCommissioner'})],
     expect={'publicServiceCommissioner': 5}),
 'sw-hi-ltgov': dict(state='HI', publisher='Office of the Lieutenant Governor of Hawaii', url='https://ltgov.hawaii.gov/',
     read=[(r'<title>\s*Lieutenant Governor '+NAME+r'\s*</title>', 'lieutenantGovernor')]),
 # The page states that all nine trustees "are elected in public elections open to all State of Hawai'i voters":
 # four hold at-large seats and five represent island districts.
 # Each trustee card gives the name, an optional board officer line and the seat label.
 'sw-hi-oha': dict(state='HI', publisher='Office of Hawaiian Affairs', url='https://www.oha.org/about/leadership/board-of-trustees/',
     read=[(r'<p class="center"><strong><a href=https://www\.oha\.org/\?post_type=trustee&p=\d+>'+NAME+r'</a></strong><br />(?:(?:Chair|Vice-Chair)<br />)?'
            r'(?P<seat>At-Large|Hawaiʻi Island|Kauaʻi & Niʻihau|Oʻahu|Molokaʻi & Lānaʻi|Maui) Trustee</p>', 'officeOfHawaiianAffairsTrustee')],
     expect={'officeOfHawaiianAffairsTrustee': 9}, shared={'At-Large'}),
}

# Elected offices whose official site refused retrieval with USER_AGENT. No other publisher substitutes for them.
BLOCKED = {
 ('AZ', 'secretaryOfState'): 'azsos.gov answered USER_AGENT with HTTP 403 and a Cloudflare challenge page (Nov 2026).',
 ('AZ', 'superintendentOfPublicInstruction'): 'azed.gov answered USER_AGENT with HTTP 403 and a Cloudflare challenge page (Nov 2026).',
 ('AZ', 'mineInspector'): 'asmi.az.gov answered USER_AGENT with HTTP 403 and a Cloudflare challenge page (Nov 2026).',
 ('CA', 'superintendentOfPublicInstruction'): 'cde.ca.gov answered USER_AGENT with a Radware bot-manager captcha page (Nov 2026).',
}

SOURCES = {key: (rule['publisher'], rule['url']) for key, rule in RULES.items()}


def _offices(rule):
    """Office keys a rule publishes, in rule order."""
    out = {}
    for _, office in rule['read']:
        out.update(dict.fromkeys([v for v in office.values() if v] if isinstance(office, dict) else [office]))
    return list(out)


def _expected(rule):
    return {key: rule.get('expect', {}).get(key, 1) for key in _offices(rule)}


STATEWIDE = {}
for _key, _rule in RULES.items():
    STATEWIDE.setdefault(_rule['state'], {}).update({k: 'collected' for k in _offices(_rule)})
for (_st, _office), _why in BLOCKED.items():
    STATEWIDE.setdefault(_st, {})[_office] = 'not-collected'
    STATEWIDE[_st].setdefault('blockers', []).append(f'{OFFICES[_office][0]}: {_why}')
for _st in STATEWIDE: STATEWIDE[_st].setdefault('blockers', [])
assert set(STATEWIDE) == set(NAMES)
assert all(k in OFFICES for item in STATEWIDE.values() for k in item if k != 'blockers')
assert all((k in MULTI) == (n > 1) for rule in RULES.values() for k, n in _expected(rule).items() if n > 1)

SUFFIX = re.compile(r',? (?:Ph\.D\.|Ed\.D\.?|M\.D\.|CPA)$')
NOT_A_NAME = re.compile(r'\b(?:Office|Governor|Home|Welcome|State|Commissioner|Treasurer|Attorney|Secretary|Auditor|District)\b')


def page_text(raw):
    text = raw.decode('utf-8', 'replace')
    text = re.sub(r'(?s)<!--.*?-->', ' ', text)
    return ' '.join(html.unescape(text).split())


def clean_name(text):
    name = SUFFIX.sub('', ' '.join(text.split()))
    assert 2 <= len(name.split()) <= 6 and not NOT_A_NAME.search(name), ('Not a person name', name)
    return name


def district(match):
    if match.groupdict().get('seat'): return match.group('seat')
    value = match.groupdict().get('district')
    if not value: return None
    if value in WORDS: return WORDS[value]
    m = re.fullmatch(r'(\d+)(?:st|nd|rd|th) Congressional District', value)
    return str(int(m.group(1))) if m else ('At-Large' if re.fullmatch(r'At[- ]Large', value) else str(int(value)))


def holders(key, raw):
    """{office key: [(name, district), ...]} read from one source; stops on any missing, unknown or conflicting entry."""
    rule = RULES[key]
    page = page_text(raw)
    if 'within' in rule:
        blocks = re.findall(rule['within'], page)
        assert len(blocks) == 1, (key, 'Expected exactly one source block', len(blocks))
        page = blocks[0]
    found = {}
    for pattern, office in rule['read']:
        matches = list(re.finditer(pattern, page))
        assert matches, (key, 'Officeholder marker not found', pattern)
        for m in matches:
            if isinstance(office, dict):
                title = ' '.join(m.group('title').split())
                assert title in office, (key, 'Unexpected office title', title)
                if office[title] is None: continue
                target = office[title]
            else:
                target = office
            item = (clean_name(m.group('name')), district(m))
            entries = found.setdefault(target, [])
            if item not in entries: entries.append(item)
    expected = _expected(rule)
    assert set(found) == set(expected), (key, 'Offices found disagree with the rule', sorted(found), sorted(expected))
    for office, n in expected.items():
        names = found[office]
        assert len(names) == n, (key, office, f'Expected {n} distinct holder(s)', names)
        assert len({name for name, _ in names}) == n, (key, office, 'Repeated holder name', names)
        seats = [d for _, d in names if d and d not in rule.get('shared', ())]
        assert len(seats) == len(set(seats)), (key, office, 'Two holders for one seat', names)
    return found


def parse(key, raw, source):
    rule = RULES[key]
    st = rule['state']
    rows = []
    for office, names in holders(key, raw).items():
        for n, (name, seat) in enumerate(names, 1):
            id = f'{st.lower()}-{office}' + (f'-{n}' if office in MULTI else '')
            row = record(source, id, name, st, 'state', f'{NAMES[st]} Executive', district=seat, office=OFFICES[office][0])
            row['website'] = source['url']
            rows.append(row)
    return rows


def collect(acquire, offline):
    rows, sources = [], []
    for key, (publisher, url) in SOURCES.items():
        raw, source = acquire(key, publisher, url, offline, user_agent=USER_AGENT)
        rows.extend(parse(key, raw, source))
        sources.append(source)
    return rows, sources
