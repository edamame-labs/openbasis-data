"""Members of the courts of last resort for MT-WY (alphabetical second half), from each court's own website.

Each rule names one repeated element of the court's roster page (a heading, a
table row, a card title or a list entry) that carries a member's title and
name. The pattern runs on the HTML-unescaped page with whitespace collapsed.
It must yield exactly the court's number of seats (from the official source
cited in docs/COURTS-B.md), distinct names, and exactly one chief or
presiding member. Anything else stops the build. A court whose page can't be
read, or doesn't list every seat, is in BLOCKED and recorded as not collected;
no other publisher substitutes for it.
"""
import html
import re
from build import record

N = r"(?P<name>[A-Z][^<>\"\d]*?)"
# key: (state, court name, publisher, url, pattern, seats, extra).
# extra: default = title for a match with no title group; chief = pattern naming the chief member
# when the members pattern carries no title; vacancy = pattern for a vacancy marker the page shows;
# strip = markup read as a space before matching.
RULES = {
 'court-mt': ('MT', 'Montana Supreme Court', 'Montana Judicial Branch', 'https://courts.mt.gov/Courts/Supreme/About/bios/',
              r'<a href="\w+"><img [^>]*/></a>(?P<title>Chief Justice|Justice) '+N+r' (?:is|was) ', 7, {}),
 'court-ne': ('NE', 'Nebraska Supreme Court', 'Nebraska Judicial Branch', 'https://nebraskajudicial.gov/courts/supreme-court/supreme-court-justices',
              r'<div class="views-field views-field-title"><span class="field-content"><a href="/courts/hon-[a-z0-9-]+" hreflang="en">Hon\. '+N+r'(?:, (?P<title>Chief Justice))?</a>', 7, dict(default='Justice')),
 'court-nj': ('NJ', 'Supreme Court of New Jersey', 'New Jersey Courts', 'https://www.njcourts.gov/courts/supreme/about',
              r'<a href="/public/museum/meet-the-justices/[a-z0-9-]+"> <h2 class="mt-0">(?P<title>Chief Justice|Justice) '+N+r'</h2>', 7, {}),
 'court-nm': ('NM', 'New Mexico Supreme Court', 'New Mexico Supreme Court', 'https://supremecourt.nmcourts.gov/about-this-court/supreme-court-justices/',
              r'<h2 class="wp-block-heading" id="h-[a-z0-9-]+">(?P<title>Chief Justice|Justice) '+N+r'</h2>', 5, {}),
 'court-nc': ('NC', 'Supreme Court of North Carolina', 'North Carolina Judicial Branch', 'https://www.nccourts.gov/courts/supreme-court/meet-the-justices',
              r'<span class="judge__title">(?P<title>Chief Justice|Associate Justice)</span> <span class="judge__full-name">'+N+r'</span>', 7, {}),
 'court-nd': ('ND', 'North Dakota Supreme Court', 'North Dakota Court System', 'https://www.ndcourts.gov/supreme-court/justices',
              r'<h5 class="card-title">(?P<title>Chief Justice|Justice) '+N+r'</h5>', 5, {}),
 'court-oh': ('OH', 'Supreme Court of Ohio', 'Supreme Court of Ohio', 'https://www.supremecourt.ohio.gov/courts/judicial-system/supreme-court-of-ohio/justices-overview/',
              r'<li><a href="/courts/judicial-system/supreme-court-of-ohio/justices-overview/[a-z-]+/"><span class="float-right"><i class="fas fa-angle-right ml-3"></i></span>(?P<title>Chief Justice|Justice) '+N+r'</a></li>', 7, {}),
 'court-ok-cca': ('OK', 'Oklahoma Court of Criminal Appeals', 'Oklahoma Court of Criminal Appeals', 'https://www.okcca.net/judges/',
              r'<a href="https://www\.okcca\.net/judges/[a-z-]+/" data-type="page" data-id="\d+"> ?(?P<title>Vice Presiding Judge|Presiding Judge|Judge) '+N+r'</a>', 5, {}),
 # The roster page renders this list with scripts; the URL reads the same official list (view "Supreme") as XML. See parse_oregon.
 'court-or': ('OR', 'Oregon Supreme Court', 'Oregon Judicial Department',
              "https://www.courts.oregon.gov/courts/_api/web/GetList('/courts/Lists/Judges')/items?%24filter=Category%20eq%20%27Supreme%27&%24select=Title,FirstName,Middle_x0020_Initial,Suffix,Job_x0020_Title,Category",
              None, 7, {}),
 'court-pa': ('PA', 'Supreme Court of Pennsylvania', 'Unified Judicial System of Pennsylvania', 'https://www.pacourts.us/courts/supreme-court/supreme-court-justices',
              r'<span>(?P<title>Chief Justice|Justice)<br/> '+N+r'</span> </a>', 7, {}),
 'court-sd': ('SD', 'South Dakota Supreme Court', 'South Dakota Unified Judicial System', 'https://ujs.sd.gov/supreme-court/',
              r'<h3 class="profilepage__subhead"> <a href="/sd-unified-judicial-system-directory/[a-z-]+/">(?P<title>Chief Justice|Justice) '+N+r'</a> </h3> <p>Supreme Court (?P=title)</p>', 5, {}),
 'court-tx-supreme': ('TX', 'Supreme Court of Texas', 'Supreme Court of Texas', 'https://www.txcourts.gov/supreme/about-the-court/justices/',
              r'<div class="span9 offset1"><h2><a href="/supreme/about-the-court/justices/[a-z-]+/">(?P<title>Chief Justice|Justice) '+N+r'</a></h2>', 9, {}),
 'court-tx-cca': ('TX', 'Texas Court of Criminal Appeals', 'Texas Court of Criminal Appeals', 'https://www.txcourts.gov/cca/about-the-court/judges/',
              r'<div class="span9 offset1"><h2><a href="/cca/about-the-court/judges/[a-z-]+/">(?P<title>Presiding Judge|Judge) '+N+r'</a></h2>', 9, {}),
 # Names are upper case on this page; see display_name. Each card prints its heading twice; the one on the card's back face is read.
 'court-ut': ('UT', 'Utah Supreme Court', 'Utah State Courts', 'https://www.utcourts.gov/en/courts/other-court-info/judges-bios/appellate-courts/supreme-court.html',
              r'<div class="flip-card-back"> <h2 class="cmp-teaser__title" style="color:" role="heading" aria-level="1"> <a class="cmp-teaser__title-link aa-cta" href="/en/courts/other-court-info/judges-bios/appellate-courts/supreme-court/[a-z-]+\.html" role="link">(?P<title>INTERIM CHIEF JUSTICE|CHIEF JUSTICE|JUSTICE) '+N+r'</a> </h2>', 7, {}),
 'court-vt': ('VT', 'Vermont Supreme Court', 'Vermont Judiciary', 'https://www.vtcourts.gov/supreme-court',
              r'<tr><td><a href="/people/[a-z-]+">Honorable '+N+r'</a></td><td>(?P<title>Chief Justice|Associate Justice)</td></tr>', 5, {}),
 # Senior Justices follow in a third section without a term line and are not seat holders.
 'court-va': ('VA', 'Supreme Court of Virginia', 'Supreme Court of Virginia', 'https://www.vacourts.gov/courts/scv/home',
              r'<li><strong>The Honorable '+N+r'</strong><br>Expiration of term: [A-Z][a-z]+ \d{1,2}, \d{4}</li>', 7,
              dict(default='Justice', chief=r'<div class="acc-title-no-link"> Chief Justice </div> <div class="[^"]*"><ul><li><strong>The Honorable '+N+r'</strong>')),
 # Names are upper case and broken by <br> at varying points; line breaks are read as spaces.
 'court-wa': ('WA', 'Washington Supreme Court', 'Washington Courts', 'https://www.courts.wa.gov/appellate_trial_courts/SupremeCourt/?fa=supremecourt.justices',
              r'<li><a href="/appellate_trial_courts/supreme/bios/\?fa=scbios\.display_file&fileID=\w+">(?P<title>ASSOCIATE CHIEF JUSTICE|CHIEF JUSTICE|JUSTICE) '+N+r'</a></li>', 9,
              dict(strip=r'<br>')),
 'court-wv': ('WV', 'Supreme Court of Appeals of West Virginia', 'West Virginia Judiciary', 'https://www.courtswv.gov/appellate-courts/supreme-court-of-appeals/justices-staff',
              r'<tr><td>(?P<title>Chief Justice|Justice) '+N+r'<br>', 5, {}),
 'court-wi': ('WI', 'Wisconsin Supreme Court', 'Wisconsin Court System', 'https://www.wicourts.gov/courts/supreme/justices/index.htm',
              r'<p class="team-title-heading"><a href="[a-z]+\.htm">(?P<title>Chief Justice|Justice)<br />'+N+r'</a></p>', 7, {}),
 'court-wy': ('WY', 'Wyoming Supreme Court', 'Wyoming Judicial Branch', 'https://www.wyocourts.gov/supreme-court/',
              r'<h4 id="team-member-name-\d+" class="title">(?P<title>Chief Justice|Justice) '+N+r' ?</h4> <p class="role">(?P=title)</p>', 5, {}),
}
# Courts of last resort with no collected observation. No other publisher substitutes for them.
BLOCKED = {
 'court-nv': ('NV', 'Supreme Court of Nevada', 'https://nvcourts.gov/supreme/justices',
              'nvcourts.gov answered USER_AGENT with a bot challenge (HTTP 403, "Just a moment...") in November 2026.'),
 'court-nh': ('NH', 'New Hampshire Supreme Court', 'https://www.courts.nh.gov/our-courts/supreme-court',
              'courts.nh.gov refused USER_AGENT with HTTP 403 "Access Denied" in November 2026.'),
 'court-ny': ('NY', 'New York Court of Appeals', 'https://www.nycourts.gov/ctapps/',
              'nycourts.gov answered USER_AGENT with a bot challenge (HTTP 403, "Just a moment...") in November 2026. '
              'The court titles its members Chief Judge and Associate Judge; statewide.COURT_OFFICES has no Chief Judge.'),
 'court-ok-supreme': ('OK', 'Supreme Court of Oklahoma', 'https://www.oscn.net/static/JudicialDirectory.pdf',
              'oscn.net lists the current justices only in the PDF Judicial Directory; the build has no PDF text extraction.'),
 'court-ri': ('RI', 'Rhode Island Supreme Court', 'https://www.courts.ri.gov/Courts/SupremeCourt/Pages/default.aspx',
              'courts.ri.gov publishes no current list of the justices in its HTTP responses (November 2026); '
              'the only roster document, AboutTheSupremeCourt.pdf, was last modified in 2023.'),
 'court-sc': ('SC', 'Supreme Court of South Carolina', 'https://www.sccourts.org/courts/supreme-court/justices/',
              'The justices page listed 4 members for 5 seats (S.C. Code 14-3-10) and showed no vacancy marker (November 2026).'),
 'court-tn': ('TN', 'Tennessee Supreme Court', 'https://www.tncourts.gov/courts/supreme-court/judges',
              'tncourts.gov answered USER_AGENT with a JavaScript challenge page instead of content in November 2026.'),
}
assert not set(RULES) & set(BLOCKED)
# Sources read from an imported browser DOM observation (tools/import_snapshot.py). None yet.
BROWSER = set()

SOURCES = {key: (publisher, url) for key, (_, _, publisher, url, *_) in RULES.items()}
COURTS = {}
for _key, (_st, _court, *_rest) in [*RULES.items(), *BLOCKED.items()]:
    COURTS.setdefault(_st, {'blockers': []})[_court] = 'collected' if _key in RULES else 'not-collected'
for _key, (_st, _court, _url, _reason) in BLOCKED.items():
    COURTS[_st]['blockers'].append(f'{_court} ({_url}): {_reason}')
# Several judiciary sites reject curl's default agent; this one identifies the project and is recorded in provenance.
USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'

# Source title -> row office. Associate, vice and interim titles keep the member's seat type.
TITLES = {'Chief Justice': 'Chief Justice', 'Interim Chief Justice': 'Chief Justice', 'Justice': 'Justice',
          'Associate Justice': 'Justice', 'Associate Chief Justice': 'Justice', 'Presiding Judge': 'Presiding Judge',
          'Vice Presiding Judge': 'Judge', 'Judge': 'Judge'}
CHIEFS = {'Chief Justice', 'Presiding Judge'}
FAMILIES = ({'Chief Justice', 'Justice'}, {'Presiding Judge', 'Judge'})
ROMAN = re.compile(r'(?:[IVX]+|[A-Z]\.(?:[A-Z]\.)*),?')


def display_name(text):
    """Collapse whitespace; title-case a name the page prints in capitals, keeping initials and numerals."""
    name = ' '.join(text.split()).strip(' ,')
    if any(c.islower() for c in name.replace('Mc', '')):
        return name
    def word(w):
        if ROMAN.fullmatch(w): return w
        w = '-'.join(p[:1] + p[1:].lower() for p in w.split('-'))
        return re.sub(r'^(Mc)([a-z])', lambda m: m.group(1) + m.group(2).upper(), w)
    return ' '.join(word(w) for w in name.split())


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def page_text(raw):
    return ' '.join(html.unescape(raw.decode('utf-8', 'replace')).split())


def members_from_page(key, raw):
    """[(source title, name)] the rule extracts from the court's roster page."""
    _, _, _, _, pattern, _, extra = RULES[key]
    page = page_text(raw)
    if 'strip' in extra:
        page = ' '.join(re.sub(extra['strip'], ' ', page).split())
    found = []
    for m in re.finditer(pattern, page):
        title = m.groupdict().get('title') or extra.get('default')
        found.append((title, m.group('name')))
    if 'chief' in extra:
        chiefs = {display_name(m.group('name')) for m in re.finditer(extra['chief'], page)}
        assert len(chiefs) == 1, (key, 'Expected exactly one chief', sorted(chiefs))
        chief = chiefs.pop()
        assert chief in {display_name(n) for _, n in found}, (key, 'Chief is not among the members', chief)
        found = [('Chief Justice' if display_name(n) == chief else t, n) for t, n in found]
    vacancies = len(re.findall(extra['vacancy'], page)) if 'vacancy' in extra else 0
    return found, vacancies


def parse_oregon(raw):
    """Members of the Oregon Judicial Department's Judges list filtered to the Supreme Court (OData XML)."""
    text = raw.decode('utf-8', 'replace')
    found = []
    for entry in re.findall(r'<m:properties>(.*?)</m:properties>', text, re.S):
        f = {k: html.unescape(v or '') for k, v in re.findall(r'<d:(\w+)(?: [^>]*?)?(?:/>|>([^<]*)</d:\1>)', entry)}
        assert f.get('Category') == 'Supreme', ('court-or', 'Unexpected category', f.get('Category'))
        title = {'Supreme Court Chief Justice': 'Chief Justice', 'Supreme Court Justice': 'Justice'}.get(f.get('Job_x0020_Title'))
        assert title, ('court-or', 'Unexpected job title', f.get('Job_x0020_Title'))
        middle = f.get('Middle_x0020_Initial', '').strip()
        parts = [f.get('FirstName', ''), middle + ('.' if len(middle) == 1 else ''), f.get('Title', ''), f.get('Suffix', '')]
        found.append((title, ' '.join(p.strip() for p in parts if p.strip())))
    return found, 0


def check_members(key, found, vacancies):
    """[(office, name)] after the seat-count, distinct-name and single-chief checks."""
    seats = RULES[key][5]
    members = []
    for title, name in found:
        title = ' '.join(title.split()).title()
        assert title in TITLES, (key, 'Unknown title', title)
        name = display_name(name)
        assert 2 <= len(name.split()) <= 6 and not re.search(r'\b(?:Justice|Judge|Chief|Court|Honorable|Hon|Vacant|Vacancy)\b', name, re.I), (key, name)
        members.append((TITLES[title], name))
    assert len(members) + vacancies == seats, (key, 'Expected seats', seats, 'found', len(members), 'vacancies', vacancies)
    names = [n for _, n in members]
    assert len(set(names)) == len(names), (key, 'Repeated or conflicting names', sorted(names))
    chiefs = [n for t, n in members if t in CHIEFS]
    assert len(chiefs) == 1, (key, 'Expected exactly one chief or presiding member', chiefs)
    assert any({t for t, _ in members} <= family for family in FAMILIES), (key, 'Mixed title families')
    return members


def parse(key, raw, source):
    st, court = RULES[key][:2]
    found, vacancies = parse_oregon(raw) if key == 'court-or' else members_from_page(key, raw)
    rows = []
    for office, name in check_members(key, found, vacancies):
        row = record(source, f'{st.lower()}-court-{slug(name)}', name, st, 'state', court)
        row.update(office=office, website=source['url'])
        rows.append(row)
    return rows


def collect(acquire, offline):
    rows, sources = [], []
    for key, (publisher, url) in SOURCES.items():
        raw, source = acquire(key, publisher, url, offline, **({} if key in BROWSER else dict(user_agent=USER_AGENT)))
        rows.extend(parse(key, raw, source))
        sources.append(source)
    assert len({r['id'] for r in rows}) == len(rows), 'Duplicate court member ids'
    return rows, sources
