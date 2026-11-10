"""Members of the courts of last resort for AL-MO (alphabetical by state name), from each court's own website.

Each state has one rule naming the page that lists the court's current members and a
pattern for the single element that carries each member's name and title. Patterns run on
the page with HTML comments removed, entities unescaped and whitespace collapsed. A rule
must yield exactly the court's seat count, less any vacancies the same page marks with
its own vacancy element, and exactly one chief justice. Anything else stops the build.

Courts whose official site refuses plain HTTP retrieval, or whose page does not account
for every seat, are listed in BLOCKED and declared not collected. No other publisher
substitutes for them.
"""
import html
import json
import re
import unicodedata
from build import record

USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'

COURT_NAMES = {
    'AL': 'Supreme Court of Alabama', 'AK': 'Alaska Supreme Court', 'AZ': 'Arizona Supreme Court',
    'AR': 'Arkansas Supreme Court', 'CA': 'Supreme Court of California', 'CO': 'Colorado Supreme Court',
    'CT': 'Connecticut Supreme Court', 'DE': 'Delaware Supreme Court', 'FL': 'Supreme Court of Florida',
    'GA': 'Supreme Court of Georgia', 'HI': 'Hawaii Supreme Court', 'ID': 'Idaho Supreme Court',
    'IL': 'Illinois Supreme Court', 'IN': 'Indiana Supreme Court', 'IA': 'Iowa Supreme Court',
    'KS': 'Kansas Supreme Court', 'KY': 'Supreme Court of Kentucky', 'LA': 'Louisiana Supreme Court',
    'ME': 'Maine Supreme Judicial Court', 'MD': 'Supreme Court of Maryland',
    'MA': 'Massachusetts Supreme Judicial Court', 'MI': 'Michigan Supreme Court',
    'MN': 'Minnesota Supreme Court', 'MS': 'Supreme Court of Mississippi', 'MO': 'Supreme Court of Missouri',
}

CJ = 'Chief Justice'
J = 'Justice'

# state: dict(publisher, url, seats, item, titles, [block], [default], [vacant], [statement]).
#   item      pattern with group 'name' and optionally 'title'; or 'head' to set the title of the names that follow.
#   titles    source title -> row office (Chief Justice | Justice). An unlisted title stops the build.
#   block     (start, end): item matches are read only between the single start match and the next end match.
#   default   title of a member whose element carries none.
#   vacant    pattern for the page's own vacant-seat element; each match accounts for one seat.
#   statement pattern for the page's own statement of the court's size; it must be present.
#   website   the page people read, when the source is the data that page is rendered from.
RULES = {
 'AL': dict(publisher='Alabama Judicial System', url='https://judicial.alabama.gov/appellate/supremecourt', seats=9,
            block=(r'<h2> Members of the Court </h2>', r'<b>Clerk</b>'),
            item=r'<b>(?P<head>Chief Justice|Associate Justices)</b>|<a href="/CourtMemberBio/ViewBio\?id=\d+">(?P<name>[^<]+)</a>',
            titles={'Chief Justice': CJ, 'Associate Justices': J},
            statement=r'composed of a chief justice and eight associate justices'),
 'AK': dict(publisher='Alaska Court System', url='https://courts.alaska.gov/judges/index.htm', seats=5,
            block=(r'<a id="justices"></a>Supreme Court Justices</h3>', r'<a id="coa-judges"></a>'),
            item=r'<tr> <td class="tdpw35"> (?:<a href="docs/[^"]+" target="_blank">)?(?P<name>[^<]+?) ?(?:</a>)?(?:<br> (?P<title>Chief Justice))? </td> <td class="tdpw35">[^<]+</td> <td class="tdpw35">\d{4}</td> </tr>',
            titles={'Chief Justice': CJ, 'Justice': J}, default='Justice'),
 'AZ': dict(publisher='Arizona Supreme Court', url='https://www.azcourts.gov/meetthejustices', seats=7,
            item=r'<p><strong><span style="color:#002458; font-size:21px">(?P<title>Chief Justice|Vice Chief Justice|Justice) (?P<name>[^<]+)</span></strong></p>',
            titles={'Chief Justice': CJ, 'Vice Chief Justice': J, 'Justice': J},
            statement=r'Seven justices are appointed by the governor to serve on the Arizona Supreme Court'),
 'AR': dict(publisher='Arkansas Judiciary', url='https://www.arcourts.gov/courts/supreme-court/justices', seats=7,
            item=r'<td headers="view-title-1-table-column" class="views-field views-field-title-1"><a href="/courts/supreme-court/justices/[a-z0-9-]+" hreflang="en">(?P<title>Chief Justice|Associate Justice) (?P<name>[^<]+), Position \d</a>',
            titles={'Chief Justice': CJ, 'Associate Justice': J}),
 # The side navigation lists sitting justices; the page's associate-justice cards mark an empty seat with a "Vacant Seat" card.
 'CA': dict(publisher='Supreme Court of California', url='https://supreme.courts.ca.gov/about-court/justices-court', seats=7,
            item=r'<li class="jcc-sub-nav__item"> <a class="" href="/about-court/justices-court/[a-z0-9-]+">(?P<title>Chief Justice|Associate Justice) (?P<name>[^<]+)</a> </li>',
            titles={'Chief Justice': CJ, 'Associate Justice': J},
            vacant=r'<div class="usa-card__brow-color"> <div>Vacant Seat</div> </div>',
            statement=r'consists of the Chief Justice of California and six Associate Justices'),
 'CO': dict(publisher='Colorado Judicial Branch', url='https://www.coloradojudicial.gov/supreme-court/supreme-court-judges-and-staff', seats=7,
            item=r'<span class="field field--name-title field--type-string field--label-hidden">(?P<name>[^<]+)</span> </div> <div class="node__content"> <div class="field field--name-field-contact-title field--type-string field--label-visually_hidden"> <div class="field__label visually-hidden">Title</div> <div class="field__items"> <div class="field__item">(?P<title>Chief Justice of the Supreme Court|Supreme Court Justice) ?</div>',
            titles={'Chief Justice of the Supreme Court': CJ, 'Supreme Court Justice': J}),
 # Former justices remain in the list inside HTML comments, which are removed before matching.
 'CT': dict(publisher='Connecticut Judicial Branch', url='https://www.jud.ct.gov/external/supapp/supjustices.htm', seats=7,
            item=r'<li><a href="[A-Za-z_\']*[Jj]ustice[A-Za-z_\']*\.html?">(?P<title>Chief Justice|Justice) (?P<name>[^<]+)</a></li>',
            titles={'Chief Justice': CJ, 'Justice': J}),
 'DE': dict(publisher='Delaware Courts', url='https://courts.delaware.gov/supreme/justices.aspx', seats=5,
            item=r'<h3>(?P<title>Chief Justice|Justice) (?P<name>[^<]+)</h3>',
            titles={'Chief Justice': CJ, 'Justice': J},
            statement=r'The Supreme Court consists of a chief justice and four justices'),
 # The page's embedded Next.js data carries the "Justices" section navigation.
 'FL': dict(publisher='Supreme Court of Florida', url='https://supremecourt.flcourts.gov/Justices', seats=7,
            item=r'\{"target":"_self","url":"/the-court/about-the-court/justices/[a-z0-9.-]+","name":"(?P<title>Chief Justice|Justice) (?P<name>[^"]+)","location":\d+,"subitems":\[\]\}',
            titles={'Chief Justice': CJ, 'Justice': J}),
 # Names are printed in capitals; display names come from the biography page titles (see GA_NAMES).
 'GA': dict(publisher='Supreme Court of Georgia', url='https://www.gasupreme.us/court-information/biographies/', seats=9,
            block=(r'<h1>Justice Biographies</h1>', r'</p>'),
            item=r'<a href="/court-information/biographies/(?P<slug>justice-[a-z0-9-]+)/">(?P<name>[A-Z][A-Z. \'-]+)</a>, (?P<title>Chief Justice|Presiding Justice|Justice)(?:<br />|$)',
            titles={'Chief Justice': CJ, 'Presiding Justice': J, 'Justice': J}),
 'ID': dict(publisher='Idaho Supreme Court', url='https://isc.idaho.gov/about-the-courts/sc-justices', seats=5,
            item=r'<div class="profile__info" data-v-[0-9a-f]+><h2 class="text-h3" data-v-[0-9a-f]+>(?P<title>Chief Justice|Justice) (?P<name>[^<]+)</h2>',
            titles={'Chief Justice': CJ, 'Justice': J},
            statement=r'The Idaho Supreme Court consists of five justices'),
 'IL': dict(publisher='Illinois Courts', url='https://www.illinoiscourts.gov/courts/supreme-court/meet-the-justices/', seats=7,
            item=r'<h2 class="accordion-title mceEditable"> (?P<name>[^<]+?)(?:, (?P<title>Chief Justice))? ?</h2>',
            titles={'Chief Justice': CJ, 'Justice': J}, default='Justice'),
 'IN': dict(publisher='Indiana Supreme Court', url='https://www.in.gov/courts/supreme/justices/', seats=5,
            block=(r'<h3>Current Justices</h3>', r'<hr />'),
            item=r'<h6><a href="/courts/supreme/justices/[a-z-]+"> (?P<title>Chief Justice|Justice) (?P<name>[^<(]+?) \(\d+\)</a></h6>',
            titles={'Chief Justice': CJ, 'Justice': J}),
 'IA': dict(publisher='Iowa Judicial Branch', url='https://www.iowacourts.gov/iowa-courts/supreme-court/justices/', seats=7,
            item=r'<h2 class="title_header">(?P<name>[^<]+)</h2> <div class="cms_metadata2 cms_title" role="heading" aria-level="2">(?P<title>Chief Justice|Justice)</div>',
            titles={'Chief Justice': CJ, 'Justice': J},
            statement=r'The Iowa Supreme Court is composed of seven justices'),
 'KY': dict(publisher='Kentucky Court of Justice', url='https://www.kycourts.gov/Courts/Supreme-Court/Pages/default.aspx', seats=7,
            item=r'<h3>(?P<name>[^<]+?) ?</h3><h4>(?P<title>Chief Justice of Kentucky|Deputy Chief Justice|Justice)<span class="court-name">Supreme Court</span></h4><p>\d\w\w Supreme Court District</p>',
            titles={'Chief Justice of Kentucky': CJ, 'Deputy Chief Justice': J, 'Justice': J}),
 'ME': dict(publisher='State of Maine Judicial Branch', url='https://www.courts.maine.gov/courts/sjc/justices.html', seats=7,
            item=r'<h3><strong>Hon\. (?P<name>[^<]+?) ?</strong><br> (?:<strong>)?(?P<title>Chief Justice|Associate Justice) ?(?:</strong>)?</h3>',
            titles={'Chief Justice': CJ, 'Associate Justice': J}),
 'MA': dict(publisher='Massachusetts Supreme Judicial Court', url='https://www.mass.gov/info-details/supreme-judicial-court-justices', seats=7,
            item=r'<h2 class="ma__comp-heading " id="[a-z0-9-]+" tabindex="-1">(?P<title>Chief Justice|Justice) (?P<name>[^<]+?) ?</h2>',
            titles={'Chief Justice': CJ, 'Justice': J},
            statement=r'The Court consists of a Chief Justice and six Associate Justices'),
 # courts.michigan.gov renders in the browser from its content delivery API; this is that API's record of the Justices page.
 'MI': dict(publisher='Michigan Supreme Court', url='https://www.courts.michigan.gov/api/episerver/v3.0/content?ContentUrl=https://www.courts.michigan.gov/courts/supreme-court/justices/', seats=7,
            website='https://www.courts.michigan.gov/courts/supreme-court/justices/',
            item=r'"title":"(?P<title>Chief Justice|Justice) (?P<name>[^"]+)","image":"[^"]*","imageAspectRatio":"[^"]*","description":"[^"]*","linkItem":',
            titles={'Chief Justice': CJ, 'Justice': J}),
 'MS': dict(publisher='State of Mississippi Judiciary', url='https://courts.ms.gov/appellatecourts/sc/scjustices.php', seats=9,
            item=r'<span><strong>(?P<title>Chief Justice|Presiding Justice|Associate Justice) (?P<name>[^<]+)</strong><br> </span>',
            titles={'Chief Justice': CJ, 'Presiding Justice': J, 'Associate Justice': J}),
}
# Georgia's WordPress API lists the biography pages under the Justices page with properly cased titles.
GA_NAMES = ('Supreme Court of Georgia', 'https://www.gasupreme.us/wp-json/wp/v2/pages?parent=80&per_page=100&_fields=title,link')

# Official court sites with no collected observation (November 2026). No other publisher substitutes for them.
BLOCKED = {
    'HI': 'https://www.courts.state.hi.us/courts/supreme/justices/justices lists four members (one Chief Justice, three Associate Justices) for the five seats it describes and marks no vacancy.',
    'KS': 'https://kscourts.gov/About-the-Courts/Supreme-Court/Justices refused automated retrieval (Cloudflare block page, HTTP 403).',
    'LA': 'https://www.lasc.org/Justices is a Blazor Server application; its HTTP response carries no member list, which is rendered in the browser over a live connection.',
    'MD': 'https://www.mdcourts.gov/scm/judges refused automated retrieval (bot challenge, HTTP 403).',
    'MN': 'https://mncourts.gov/supremecourt/justices refused automated retrieval (Cloudflare challenge, HTTP 403).',
    'MO': 'https://www.courts.mo.gov/ refused automated retrieval (HTTP 403).',
}
assert set(RULES) | set(BLOCKED) == set(COURT_NAMES) and not set(RULES) & set(BLOCKED)

SOURCES = {'court-'+st.lower(): (rule['publisher'], rule['url']) for st, rule in RULES.items()}
SOURCES['court-ga-names'] = GA_NAMES
COURTS = {st: ({name: 'collected', 'blockers': []} if st in RULES else
               {name: 'not-collected', 'blockers': ['The official court website could not be read: '+BLOCKED[st]]})
          for st, name in COURT_NAMES.items()}
NOT_A_NAME = re.compile(r'\b(?:Justice|Justices|Court|Supreme|Chief|Vacant|Seat|Clerk|Judge|Position|District)\b', re.I)


def normalize(raw):
    text = raw.decode('utf-8-sig', 'replace')
    text = re.sub(r'(?s)<!--.*?-->', ' ', text)
    return ' '.join(html.unescape(text).split())


def slug(name):
    ascii_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', ascii_name.lower()).strip('-')


def members(state, raw):
    """[(office, name, match)] for one court page, checked against the court's seats."""
    rule = RULES[state]
    page = normalize(raw)
    if 'statement' in rule:
        assert re.search(rule['statement'], page), (state, 'The court-size statement is missing')
    text = page
    if 'block' in rule:
        start, end = rule['block']
        starts = list(re.finditer(start, page))
        assert len(starts) == 1, (state, 'Expected one member-list start marker', len(starts))
        stop = re.compile(end).search(page, starts[0].end())
        assert stop, (state, 'The member-list end marker is missing')
        text = page[starts[0].end():stop.start()]
    found, head = {}, None
    for m in re.finditer(rule['item'], text):
        groups = m.groupdict()
        if groups.get('head'):
            head = groups['head']
            continue
        name = ' '.join(m.group('name').split()).strip(' ,')
        title = groups.get('title') or head or rule.get('default')
        assert title in rule['titles'], (state, 'Unknown title', title, name)
        office = rule['titles'][title]
        assert 2 <= len(name.split()) <= 6 and name[0].isupper() and not NOT_A_NAME.search(name), (state, 'Not a name', name)
        assert found.get(name, (office,))[0] == office, (state, 'Conflicting titles', name)
        found[name] = (office, m)
    vacant = len(re.findall(rule['vacant'], page)) if 'vacant' in rule else 0
    assert len(found) + vacant == rule['seats'], (state, 'Member count does not match seats', len(found), vacant, rule['seats'])
    assert sum(office == CJ for office, _ in found.values()) == 1, (state, 'Expected exactly one chief justice')
    assert len({slug(n) for n in found}) == len(found), (state, 'Duplicate member ids')
    return [(office, name, m) for name, (office, m) in found.items()]


def georgia_names(raw):
    """{biography slug: (title, name)} from the Georgia WordPress page listing."""
    out = {}
    for item in json.loads(raw):
        link = re.fullmatch(r'https://www\.gasupreme\.us/court-information/biographies/([a-z0-9-]+)/', item['link'])
        assert link, item['link']
        text = ' '.join(html.unescape(item['title']['rendered']).split())
        m = re.fullmatch(r'(?P<title>Chief Justice|Presiding Justice|Retired Justice|Justice) (?P<name>.+)', text)
        assert m, ('Unexpected Georgia biography title', text)
        out[link.group(1)] = (m.group('title'), m.group('name'))
    return out


def parse(key, raw, source, names=None):
    """Rows for one court page. Georgia also takes (raw, source) of GA_NAMES as names."""
    state = key.removeprefix('court-').upper()
    body = COURT_NAMES[state]
    listed = names and georgia_names(names[0])
    assert (state == 'GA') == bool(names), (state, 'Georgia, and only Georgia, needs the biography titles')
    rows = []
    for office, name, m in members(state, raw):
        sources = [source]
        if state == 'GA':
            assert m.group('slug') in listed, (state, 'No biography title for', name)
            title, display = listed[m.group('slug')]
            assert title == m.group('title') and display.upper() == name, (state, 'Biography title disagrees with the list', name, title, display)
            name, sources = display, [source, names[1]]
        row = record(sources[0], f'{state.lower()}-court-{slug(name)}', name, state, 'state', body, office=office)
        row.update(sources=sources, website=RULES[state].get('website', source['url']))
        rows.append(row)
    return rows


def collect(acquire, offline):
    rows, sources = [], []
    fetched = {key: acquire(key, publisher, url, offline, user_agent=USER_AGENT) for key, (publisher, url) in SOURCES.items()}
    for key, (raw, source) in fetched.items():
        sources.append(source)
        if key == 'court-ga-names': continue
        rows.extend(parse(key, raw, source, fetched['court-ga-names'] if key == 'court-ga' else None))
    return rows, sources
