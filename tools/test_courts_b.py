"""Regression checks for court-of-last-resort extraction (MT-WY) from official judiciary websites."""
import unittest
import build
import statewide
from regions import courts_b as region


def source(key):
    pub, url = region.SOURCES[key]
    return dict(id=key, name=pub, url=url, retrievedAt='2026-11-09T01:00:00+00:00', sha256='a'*64, representation='http-response-body')


def wy_card(title, name):
    return f'<h4 id="team-member-name-1" class="title">{title} {name} </h4> <p class="role">{title}</p>'


WY = ''.join(wy_card(t, n) for t, n in [('Chief Justice', 'Lynne Boomgaarden'), ('Justice', 'Kari Gray'), ('Justice', 'John G. Fenn'),
                                         ('Justice', 'Robert C. Jarosh'), ('Justice', 'Bridget Hill')])


def tx_cca(rows):
    return ''.join(f'<div class="span9 offset1"><h2><a href="/cca/about-the-court/judges/x/">{t} {n}</a></h2>' for t, n in rows)


CCA = [('Presiding Judge', 'David J. Schenck'), ('Judge', 'Bert Richardson'), ('Judge', 'Kevin Yeary'), ('Judge', 'David Newell'),
       ('Judge', 'Mary Lou Keel'), ('Judge', 'Scott Walker'), ('Judge', 'Jesse F. McClure, III'), ('Judge', 'Lee Finley'), ('Judge', 'Gina G. Parker')]


class CourtTests(unittest.TestCase):
    def test_title_extraction_and_row_shape(self):
        rows = region.parse('court-wy', WY.encode(), source('court-wy'))
        self.assertEqual(len(rows), 5)
        self.assertEqual((rows[0]['id'], rows[0]['name'], rows[0]['office'], rows[0]['body'], rows[0]['level'], rows[0]['website']),
                         ('wy-court-lynne-boomgaarden', 'Lynne Boomgaarden', 'Chief Justice', 'Wyoming Supreme Court', 'state', 'https://www.wyocourts.gov/supreme-court/'))
        self.assertEqual([r['office'] for r in rows[1:]], ['Justice'] * 4)

    def test_presiding_judge_court(self):
        rows = region.parse('court-tx-cca', tx_cca(CCA).encode(), source('court-tx-cca'))
        self.assertEqual([r['office'] for r in rows], ['Presiding Judge'] + ['Judge'] * 8)
        self.assertEqual(rows[6]['name'], 'Jesse F. McClure, III')
        self.assertEqual({r['body'] for r in rows}, {'Texas Court of Criminal Appeals'})

    def test_missing_marker_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('court-wy', b'<h4 class="title">Justice Kari Gray</h4>', source('court-wy'))

    def test_missing_seat_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('court-tx-cca', tx_cca(CCA[:-1]).encode(), source('court-tx-cca'))

    def test_conflicting_names_stop(self):
        # The same person listed twice, under two titles.
        rows = CCA[:-1] + [('Judge', 'David J. Schenck')]
        with self.assertRaises(AssertionError):
            region.parse('court-tx-cca', tx_cca(rows).encode(), source('court-tx-cca'))

    def test_two_chiefs_stop(self):
        page = WY.replace('<h4 id="team-member-name-1" class="title">Justice Kari Gray </h4> <p class="role">Justice</p>',
                          wy_card('Chief Justice', 'Kari Gray'))
        with self.assertRaises(AssertionError):
            region.parse('court-wy', page.encode(), source('court-wy'))

    def test_no_chief_stops(self):
        rows = [('Judge', 'Someone Else')] + CCA[1:]
        with self.assertRaises(AssertionError):
            region.parse('court-tx-cca', tx_cca(rows).encode(), source('court-tx-cca'))

    def test_vacancy_marker_counts_only_when_declared(self):
        key = 'court-wy'
        rule = region.RULES[key]
        page = WY.replace(wy_card('Justice', 'Bridget Hill'), '<p class="vacant">Vacant seat</p>').encode()
        with self.assertRaises(AssertionError):
            region.parse(key, page, source(key))
        region.RULES[key] = rule[:6] + ({**rule[6], 'vacancy': r'<p class="vacant">Vacant seat</p>'},)
        try:
            self.assertEqual(len(region.parse(key, page, source(key))), 4)
        finally:
            region.RULES[key] = rule

    def test_upper_case_names_and_line_breaks(self):
        names = ['CHIEF JUSTICE<br> DEBRA L. STEPHENS', 'ASSOCIATE CHIEF JUSTICE CHARLES W. JOHNSON', 'JUSTICE SHERYL GORDON McCLOUD',
                 'JUSTICE RAQUEL<br> MONTOYA-LEWIS', 'JUSTICE <br> SALVADOR A. MUNGIA', 'JUSTICE G. HELEN<br> WHITENER',
                 'JUSTICE STEVEN C. GONZ&Aacute;LEZ', 'JUSTICE A B', 'JUSTICE C D']
        page = ''.join(f'<li><a href="/appellate_trial_courts/supreme/bios/?fa=scbios.display_file&fileID=x">{n}</a></li>' for n in names)
        rows = region.parse('court-wa', page.encode(), source('court-wa'))
        self.assertEqual([r['name'] for r in rows[:7]], ['Debra L. Stephens', 'Charles W. Johnson', 'Sheryl Gordon McCloud', 'Raquel Montoya-Lewis',
                                                        'Salvador A. Mungia', 'G. Helen Whitener', 'Steven C. González'])
        self.assertEqual([r['office'] for r in rows[:2]], ['Chief Justice', 'Justice'])

    def test_separate_chief_rule(self):
        def li(n): return f'<li><strong>The Honorable {n}</strong><br>Expiration of term: July 31, 2035</li>'
        names = ['Cleo E. Powell', 'D. Arthur Kelsey', 'Stephen R. McCullough', 'Teresa M. Chafin', 'Wesley G. Russell Jr.', 'Thomas P. Mann', 'Junius P. Fulton, III']
        page = (f'<div class="acc-title-no-link"> Chief Justice </div> <div class="x"><ul>{li(names[0])}</ul></div>'
                f'<div class="acc-title-no-link"> Justices </div> <div class="x"><ul>{"".join(li(n) for n in names[1:])}</ul></div>'
                '<ul><li><span>The Honorable S. Bernard Goodwyn</span></li></ul>')
        rows = region.parse('court-va', page.encode(), source('court-va'))
        self.assertEqual([(r['office'], r['name']) for r in rows][:2], [('Chief Justice', 'Cleo E. Powell'), ('Justice', 'D. Arthur Kelsey')])
        with self.assertRaises(AssertionError):
            region.parse('court-va', page.replace('Chief Justice </div>', 'Justices </div>').encode(), source('court-va'))

    def test_oregon_list(self):
        def entry(last, first, mi, title):
            return (f'<entry><m:properties><d:Title>{last}</d:Title><d:FirstName>{first}</d:FirstName><d:Middle_x0020_Initial>{mi}</d:Middle_x0020_Initial>'
                    f'<d:Suffix m:null="true" /><d:Category>Supreme</d:Category><d:Job_x0020_Title>{title}</d:Job_x0020_Title></m:properties></entry>')
        people = [('Flynn', 'Meagan', 'A', 'Supreme Court Chief Justice')] + [(f'Last{c}', f'First{c}', c, 'Supreme Court Justice') for c in 'BCDEFG']
        rows = region.parse('court-or', ''.join(entry(*p) for p in people).encode(), source('court-or'))
        self.assertEqual((rows[0]['name'], rows[0]['office'], rows[1]['office']), ('Meagan A. Flynn', 'Chief Justice', 'Justice'))
        bad = ''.join(entry(*p) for p in people).replace('Supreme Court Justice', 'Circuit Court Judge', 1)
        with self.assertRaises(AssertionError):
            region.parse('court-or', bad.encode(), source('court-or'))

    def test_declarations_cover_assigned_states(self):
        self.assertEqual(set(region.COURTS), set('MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()))
        statewide.check_declarations({}, region.COURTS, build.STATE_CODES)
        self.assertEqual(region.COURTS['TX'], {'Supreme Court of Texas': 'collected', 'Texas Court of Criminal Appeals': 'collected', 'blockers': []})
        self.assertEqual(region.COURTS['OK']['Oklahoma Court of Criminal Appeals'], 'collected')
        self.assertEqual(region.COURTS['OK']['Supreme Court of Oklahoma'], 'not-collected')
        for key, (st, court, url, reason) in region.BLOCKED.items():
            self.assertTrue(any(url in b for b in region.COURTS[st]['blockers']), key)

    def test_coverage_matches_rows(self):
        rows = region.parse('court-wy', WY.encode(), source('court-wy'))
        cov = statewide.court_coverage('WY', region.COURTS['WY'], rows)
        self.assertEqual(cov['courts']['Wyoming Supreme Court'], dict(status='collected', records=5))
        with self.assertRaises(AssertionError):
            statewide.court_coverage('WY', region.COURTS['WY'], [])

    def test_offices_are_court_vocabulary(self):
        self.assertTrue(set(region.TITLES.values()) <= statewide.COURT_OFFICES)

    def test_sources_are_https_and_registered(self):
        for key, (pub, url) in region.SOURCES.items():
            self.assertTrue(url.startswith('https://'), key)
        self.assertEqual(region.BROWSER, set())


if __name__ == '__main__':
    unittest.main()
