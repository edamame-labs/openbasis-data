"""Regression checks for high-court member extraction (AL-MO) from official court websites."""
import json
import unittest
import build
import statewide
from regions import courts_a as region


def source(key):
    pub, url = region.SOURCES[key]
    return dict(id=key, name=pub, url=url, retrievedAt='2026-11-09T01:00:00+00:00', sha256='a'*64, representation='http-response-body')


def de_page(*members):
    head = b'<p>The Supreme Court consists of a chief justice and four justices who are nominated by the Governor.</p>'
    return head + b''.join(b'<img alt="x" />\n  <h3>' + m.encode() + b'</h3> <p>Bio.</p>' for m in members)


DE = ['Chief Justice Collins J. Seitz, Jr.', 'Justice Gary F. Traynor', 'Justice Abigail M. LeGrow',
      'Justice N. Christopher Griffiths', 'Justice Morgan T. Zurn']


class CourtTests(unittest.TestCase):
    def test_title_extraction(self):
        rows = region.parse('court-de', de_page(*DE), source('court-de'))
        self.assertEqual(len(rows), 5)
        self.assertEqual((rows[0]['id'], rows[0]['name'], rows[0]['office'], rows[0]['body'], rows[0]['level']),
                         ('de-court-collins-j-seitz-jr', 'Collins J. Seitz, Jr.', 'Chief Justice', 'Delaware Supreme Court', 'state'))
        self.assertEqual([r['office'] for r in rows[1:]], ['Justice'] * 4)
        self.assertEqual(rows[0]['website'], 'https://courts.delaware.gov/supreme/justices.aspx')

    def test_missing_marker_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('court-de', de_page(*DE[:4]), source('court-de'))
        with self.assertRaises(AssertionError):
            region.parse('court-de', b'<h1>Justices</h1>', source('court-de'))

    def test_missing_size_statement_stops(self):
        page = de_page(*DE).replace(b'chief justice and four justices', b'chief justice and justices')
        with self.assertRaises(AssertionError):
            region.parse('court-de', page, source('court-de'))

    def test_conflicting_names_stop(self):
        # Two chief justices, or the same person under two titles.
        with self.assertRaises(AssertionError):
            region.parse('court-de', de_page('Chief Justice Someone Else', *DE[1:4], 'Chief Justice Collins J. Seitz, Jr.'), source('court-de'))
        with self.assertRaises(AssertionError):
            region.parse('court-de', de_page(*DE[:4], 'Chief Justice Gary F. Traynor'), source('court-de'))

    def test_extra_member_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('court-de', de_page(*DE, 'Justice Sixth Person'), source('court-de'))

    def test_commented_out_former_justices_are_ignored(self):
        names = ['Chief Justice Raheem L. Mullins', 'Justice Andrew J. McDonald', "Justice Gregory T. D&#8217;Auria",
                 'Justice Steven D. Ecker', 'Justice Nora R. Dannehy', 'Justice William H. Bright, Jr.', 'Justice Melanie L. Cradle']
        items = ''.join(f'<li><a href="justice_{chr(65 + i)}.html">{n}</a></li>\n' for i, n in enumerate(names))
        page = ('<ul><!-- <li><a href="justiceRobinson.htm">Chief Justice Richard A. Robinson - Retired</a></li> -->'
                + items + '<!--<li><a href="justice_Kahn.htm">Justice Maria Araujo Kahn</a></li>--></ul>').encode()
        rows = region.parse('court-ct', page, source('court-ct'))
        self.assertEqual(len(rows), 7)
        self.assertIn('Gregory T. D’Auria', [r['name'] for r in rows])

    def test_page_marked_vacancy_counts_toward_seats(self):
        nav = ['Chief Justice Patricia Guerrero', 'Associate Justice Carol A. Corrigan', 'Associate Justice Goodwin H. Liu',
               'Associate Justice Leondra R. Kruger', 'Associate Justice Joshua P. Groban', 'Associate Justice Kelli Evans']
        items = ''.join(f'<li class="jcc-sub-nav__item"> <a class="" href="/about-court/justices-court/j{i}">{n}</a> </li>' for i, n in enumerate(nav))
        statement = '<p>The Supreme Court of California consists of the Chief Justice of California and six Associate Justices.</p>'
        vacant = '<div class="usa-card__brow"> <div class="usa-card__brow-color"> <div>Vacant Seat</div> </div> </div>'
        page = (statement + items + vacant).encode()
        rows = region.parse('court-ca', page, source('court-ca'))
        self.assertEqual((len(rows), sum(r['office'] == 'Chief Justice' for r in rows)), (6, 1))
        with self.assertRaises(AssertionError):
            region.parse('court-ca', (statement + items).encode(), source('court-ca'))

    def test_section_headings_set_titles(self):
        links = ''.join(f'<a href="/CourtMemberBio/ViewBio?id={i}">Member Number{chr(65 + i)}</a> <br /> ' for i in range(1, 9))
        page = ('<p>The Supreme Court of Alabama is composed of a chief justice and eight associate justices.</p>'
                '<h2> Members of the Court </h2> <div> <b>Chief Justice</b><br /> <a href="/CourtMemberBio/ViewBio?id=42">Sarah H. Stewart</a> <br /> '
                '<br /><b>Associate Justices</b><br /> ' + links +
                '<br /><b>Clerk</b><br /> <a href="/CourtMemberBio/ViewBio?id=75">Megan B. Rhodebeck</a>').encode()
        rows = region.parse('court-al', page, source('court-al'))
        self.assertEqual(rows[0]['name'], 'Sarah H. Stewart')
        self.assertEqual(rows[0]['office'], 'Chief Justice')
        self.assertEqual({r['office'] for r in rows[1:]}, {'Justice'})
        self.assertNotIn('Megan B. Rhodebeck', [r['name'] for r in rows])

    def test_georgia_names_come_from_biography_titles(self):
        people = [('nels-s-d-peterson', 'Nels S.D. Peterson', 'Chief Justice'), ('sarah-hawkins-warren', 'Sarah Hawkins Warren', 'Presiding Justice')] + \
                 [(f'person-{c}', f'Person {c.upper()}. Name', 'Justice') for c in 'abcdefg']
        listing = '<br /> '.join(f'<a href="/court-information/biographies/justice-{s}/">{n.upper()}</a>, {t}' for s, n, t in people)
        page = f'<h1>Justice Biographies</h1> <p>{listing}</p>'.encode()
        api = json.dumps([{'link': f'https://www.gasupreme.us/court-information/biographies/justice-{s}/', 'title': {'rendered': f'{t} {n}'}} for s, n, t in people]).encode()
        names = (api, source('court-ga-names'))
        rows = region.parse('court-ga', page, source('court-ga'), names)
        self.assertEqual((rows[0]['name'], rows[0]['office'], rows[0]['id']), ('Nels S.D. Peterson', 'Chief Justice', 'ga-court-nels-s-d-peterson'))
        self.assertEqual([s['id'] for s in rows[0]['sources']], ['court-ga', 'court-ga-names'])
        bad = api.replace(b'Sarah Hawkins Warren', b'Sarah Hawkins Smith')
        with self.assertRaises(AssertionError):
            region.parse('court-ga', page, source('court-ga'), (bad, names[1]))
        with self.assertRaises(AssertionError):
            region.parse('court-ga', page, source('court-ga'))

    def test_declarations(self):
        self.assertEqual(set(region.COURTS), set(region.COURT_NAMES))
        statewide.check_declarations({}, region.COURTS, build.STATE_CODES)
        for st, item in region.COURTS.items():
            self.assertEqual(item[region.COURT_NAMES[st]] == 'collected', st in region.RULES)
            self.assertEqual(bool(item['blockers']), st in region.BLOCKED)
        for st, rule in region.RULES.items():
            self.assertIn('court-'+st.lower(), region.SOURCES)
            self.assertTrue(set(rule['titles'].values()) <= statewide.COURT_OFFICES and 'Chief Justice' in rule['titles'].values())

    def test_coverage_matches_rows(self):
        rows = region.parse('court-de', de_page(*DE), source('court-de'))
        out = statewide.court_coverage('DE', region.COURTS['DE'], rows)
        self.assertEqual(out['courts']['Delaware Supreme Court'], dict(status='collected', records=5))
        out = statewide.court_coverage('KS', region.COURTS['KS'], [])
        self.assertEqual(out['courts']['Kansas Supreme Court']['status'], 'not-collected')


if __name__ == '__main__':
    unittest.main()
