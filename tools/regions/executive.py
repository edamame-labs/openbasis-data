"""Sitting governors from each state's official governor website; no fallback inputs.

Each rule names one element of the governor's own homepage that identifies the
officeholder (page title, a heading, or a meta description), with a pattern that
must match at least once and yield exactly one distinct name. A missing or
ambiguous match stops the build. Sites that refuse plain HTTP retrieval are
listed in BLOCKED and recorded as not collected rather than filled from another
publisher.
"""
import html
import re
from build import record

NAMES = dict(AL='Alabama', AK='Alaska', AZ='Arizona', AR='Arkansas', CA='California', CO='Colorado', CT='Connecticut', DE='Delaware',
             FL='Florida', GA='Georgia', HI='Hawaii', ID='Idaho', IL='Illinois', IN='Indiana', IA='Iowa', KS='Kansas', KY='Kentucky',
             LA='Louisiana', ME='Maine', MD='Maryland', MA='Massachusetts', MI='Michigan', MN='Minnesota', MS='Mississippi',
             MO='Missouri', MT='Montana', NE='Nebraska', NV='Nevada', NH='New Hampshire', NJ='New Jersey', NM='New Mexico',
             NY='New York', NC='North Carolina', ND='North Dakota', OH='Ohio', OK='Oklahoma', OR='Oregon', PA='Pennsylvania',
             RI='Rhode Island', SC='South Carolina', SD='South Dakota', TN='Tennessee', TX='Texas', UT='Utah', VT='Vermont',
             VA='Virginia', WA='Washington', WV='West Virginia', WI='Wisconsin', WY='Wyoming')

N = r"(?P<name>[A-Z][A-Za-z.'\- ]+?)"
TITLE = r'<title[^>]*>\s*'
# state: (publisher, url, pattern). Patterns run on the HTML-unescaped page with whitespace collapsed.
# A rule whose URL contains the governor's name (ND) stops the build when the office changes hands.
RULES = {
 'AL': ('Office of the Governor of Alabama', 'https://governor.alabama.gov/', r'<p>Governor '+N+r', who became the \d+\w+ Governor of Alabama'),
 'AK': ('Office of the Governor of Alaska', 'https://gov.alaska.gov/', TITLE+r'Governor \w+ Home - '+N+r'\s*</title>'),
 'AZ': ('Office of the Arizona Governor', 'https://azgovernor.gov/', TITLE+r'Office of the Arizona Governor '+N+r'\s*</title>'),
 'AR': ('Office of the Governor of Arkansas', 'https://governor.arkansas.gov/', TITLE+r'Home Page - Arkansas Governor - '+N+r'\s*</title>'),
 'CA': ('Office of the Governor of California', 'https://www.gov.ca.gov/', r'<meta name="description" content="The official website of California Governor '+N+r'\. '),
 'DE': ('Office of the Governor of Delaware', 'https://governor.delaware.gov/', TITLE+r'Governor '+N+r' - State of Delaware\s*</title>'),
 'FL': ('Executive Office of the Governor of Florida', 'https://www.flgov.com/eog/', TITLE+r'Governor '+N+r' \| Executive Office of the Governor\s*</title>'),
 'GA': ('Office of the Governor of Georgia', 'https://gov.georgia.gov/', TITLE+r'Governor '+N+r' Office of the Governor\s*</title>'),
 'HI': ('Office of the Governor of Hawaii', 'https://governor.hawaii.gov/', TITLE+r'Governor '+N+r', M\.D\. - Office of the Governor\s*</title>'),
 'ID': ('Office of the Governor of Idaho', 'https://gov.idaho.gov/', r'<meta property="og:title" content="Governor '+N+r'">'),
 'IL': ('Office of the Governor of Illinois', 'https://gov.illinois.gov/', TITLE+N+r', Governor\s*</title>'),
 'IN': ('Office of the Governor of Indiana', 'https://www.in.gov/gov/', r'<h1\s*>Indiana Governor '+N+r'</h1>'),
 'IA': ('Office of the Governor of Iowa', 'https://governor.iowa.gov/', r'<meta property="og:site_name" content="Governor '+N+r'" />'),
 # Browser-captured (see BROWSER); the menu link to the governor's page carries the name. Redirects to www.governor.ks.gov.
 'KS': ('Office of the Governor of Kansas', 'https://governor.kansas.gov/', r'<a class="megamenu_level1" href="/about-the-office/governor-[a-z-]+" aria-label="Governor '+N+r'"'),
 'KY': ('Office of the Governor of Kentucky', 'https://governor.ky.gov/', TITLE+r'Welcome - Kentucky Governor '+N+r'\s*</title>'),
 'LA': ('Office of the Governor of Louisiana', 'https://gov.louisiana.gov/', TITLE+r'Home \| Office of Governor '+N+r'\s*</title>'),
 'ME': ('Office of the Governor of Maine', 'https://www.maine.gov/governor/mills/', TITLE+r'Home \| Office of Governor '+N+r'\s*</title>'),
 'MD': ('Office of the Governor of Maryland', 'https://governor.maryland.gov/', TITLE+r'The Office of Governor '+N+r'\s*</title>'),
 'MS': ('Office of the Governor of Mississippi', 'https://governorreeves.ms.gov/', TITLE+r'Official Website of Mississippi Governor '+N+r'\s*</title>'),
 'MO': ('Office of the Governor of Missouri', 'https://governor.mo.gov/', TITLE+N+r', Governor of Missouri Homepage'),
 'MT': ('Office of the Governor of Montana', 'https://governor.mt.gov/', TITLE+r'Montana Governor '+N+r' Official Website\s*</title>'),
 'NE': ('Office of the Governor of Nebraska', 'https://governor.nebraska.gov/', TITLE+r'Latest News \| Office of Governor '+N+r'\s*</title>'),
 'NV': ('Office of the Governor of Nevada', 'https://www.gov.nv.gov/', TITLE+r"Nevada Governor's Office \| "+N+r'\s*</title>'),
 'NJ': ('Office of the Governor of New Jersey', 'https://www.nj.gov/governor/', TITLE+r'Office of New Jersey Governor '+N+r'\s*</title>'),
 'NM': ('Office of the Governor of New Mexico', 'https://www.governor.state.nm.us/', TITLE+r'Home - Office of the Governor - '+N+r'\s*</title>'),
 'NC': ('Office of the Governor of North Carolina', 'https://governor.nc.gov/', r'<meta name="description" content="The official website for North Carolina Governor '+N+r'\." />'),
 # The homepage names the governor only in news items; its "Governor" menu links to this biography page.
 'ND': ('Office of the Governor of North Dakota', 'https://www.governor.nd.gov/governor-kelly-armstrong', TITLE+r'Governor '+N+r' \| North Dakota Office of the Governor\s*</title>'),
 'OH': ('Office of the Governor of Ohio', 'https://governor.ohio.gov/', TITLE+r'Governor '+N+r'\s*</title>'),
 'OK': ('Office of the Governor of Oklahoma', 'https://oklahoma.gov/governor.html', TITLE+r'Governor '+N+r'\s*</title>'),
 'OR': ('Office of the Governor of Oregon', 'https://www.oregon.gov/gov/Pages/index.aspx', TITLE+r'Governor of Oregon : Governor '+N+r' : State of Oregon\s*</title>'),
 'PA': ('Office of the Governor of Pennsylvania', 'https://www.pa.gov/governor', r'<meta name="copapwp-page-title" content="Governor '+N+r'"/>'),
 'SC': ('Office of the Governor of South Carolina', 'https://governor.sc.gov/', TITLE+r'Home \| S\.C\. Governor '+N+r'\s*</title>'),
 'SD': ('Office of the Governor of South Dakota', 'https://governor.sd.gov/governor/about.aspx', TITLE+r'South Dakota Governor '+N+r'\s*</title>'),
 'TX': ('Office of the Texas Governor', 'https://gov.texas.gov/', TITLE+r'Office of the Texas Governor \| '+N+r'\s*</title>'),
 'UT': ('Office of the Governor of Utah', 'https://governor.utah.gov/', TITLE+r'Governor '+N+r'\s*</title>'),
 'VT': ('Office of the Governor of Vermont', 'https://governor.vermont.gov/', TITLE+r'Home \| Office of Governor '+N+r'\s*</title>'),
 'VA': ('Office of the Governor of Virginia', 'https://www.governor.virginia.gov/', r'<meta name="description" content="'+N+r', Commonwealth, Governor of Virginia'),
 'WA': ('Office of the Governor of Washington', 'https://governor.wa.gov/', TITLE+r'Home \| Governor '+N+r'\s*</title>'),
 'WV': ('Office of the Governor of West Virginia', 'https://governor.wv.gov/', TITLE+r'WV Office of the Governor '+N+r'\s*</title>'),
 'WI': ('Office of the Governor of Wisconsin', 'https://evers.wi.gov/Pages/Home.aspx', TITLE+r'Official site of Governor '+N+r'\s*</title>'),
 'WY': ('Office of the Governor of Wyoming', 'https://governor.wyo.gov/', TITLE+r'Wyoming Governor '+N+r'\s*</title>'),
}
# Sources read from an imported browser DOM observation (tools/import_snapshot.py), not over HTTP.
BROWSER = {'gov-ks'}
# Official governor sites with no collected observation: they refused retrieval with USER_AGENT
# (bot challenge, 403 or timeout) and have no imported browser capture. No other publisher substitutes for them.
BLOCKED = {
 'CO': 'https://governor.colorado.gov/', 'CT': 'https://portal.ct.gov/governor',
 'MA': 'https://www.mass.gov/orgs/office-of-the-governor', 'MI': 'https://www.michigan.gov/whitmer', 'MN': 'https://mn.gov/governor/', 'NH': 'https://www.governor.nh.gov/',
 'NY': 'https://www.governor.ny.gov/', 'RI': 'https://governor.ri.gov/', 'TN': 'https://www.tn.gov/governor.html',
}
assert set(RULES) | set(BLOCKED) == set(NAMES) and not set(RULES) & set(BLOCKED)
assert all(k.removeprefix('gov-').upper() in RULES for k in BROWSER)

SOURCES = {'gov-'+st.lower(): (publisher, url) for st, (publisher, url, _) in RULES.items()}
EXECUTIVE = {st: dict(governor='collected' if st in RULES else 'not-collected',
                      blockers=[] if st in RULES else ['The official governor website refused automated retrieval: '+BLOCKED[st]])
             for st in NAMES}
BODY = '{} Executive'
# Several state sites reject curl's default agent; this one identifies the project and is recorded in provenance.
USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'


def governor_name(state, raw):
    """The single governor name the state's rule extracts from its homepage."""
    page = ' '.join(html.unescape(raw.decode('utf-8', 'replace')).split())
    names = {' '.join(m.group('name').split()) for m in re.finditer(RULES[state][2], page)}
    assert len(names) == 1, (state, 'Expected exactly one governor name', sorted(names))
    name = names.pop()
    assert 2 <= len(name.split()) <= 5 and not re.search(r'\b(?:Office|Governor|Home|Welcome|State)\b', name), (state, name)
    return name


def parse(key, raw, source):
    state = key.removeprefix('gov-').upper()
    row = record(source, f'{state.lower()}-governor', governor_name(state, raw), state, 'state', BODY.format(NAMES[state]))
    row.update(office='Governor', website=source['url'])
    return [row]


def collect(acquire, offline):
    rows, sources = [], []
    for key, (publisher, url) in SOURCES.items():
        raw, source = acquire(key, publisher, url, offline, **({} if key in BROWSER else dict(user_agent=USER_AGENT)))
        rows.extend(parse(key, raw, source))
        sources.append(source)
    return rows, sources
