"""Regression checks for statewide executive officers in PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI and WY."""
import unittest
import build
import statewide
from regions import statewide_d as region


def source(key):
    pub, url = region.SOURCES[key]
    return dict(id=key, name=pub, url=url, retrievedAt='2026-11-10T01:00:00+00:00', sha256='a'*64, representation='http-response-body')


def parse(key, page):
    return region.parse(key, page, source(key))


SD = (b'<p><strong>Governor Larry Rhoden (R)</strong></p>'
      b'<p><strong>Lt. Governor Tony Venhuizen (R)</strong></p>'
      b'<p><strong>Secretary of State Monae L. Johnson (R)</strong></p>'
      b'<p><strong>Attorney General Marty Jackley (R)</strong></p>'
      b'<p><strong>State Auditor Rich Sattgast (R)</strong></p>'
      b'<p><strong>State Treasurer Josh Haeder (R) </strong></p>'
      b'<p><strong>Commissioner of School and Public Lands<br>\n Brock Greenfield (R)</strong></p>'
      b'<p><strong>Public Utilities Commissioner<br> Gary Hanson (R)</strong></p>'
      b'<p><strong>Public Utilities Commissioner<br> Kristie Fiegen (R)</strong></p>'
      b'<p><strong>Public Utilities Commissioner<br> Chris Nelson (R)</strong></p>'
      b'<p><strong>Chief Justice of the Supreme Court<br> Steven R. Jensen</strong></p>')

RRC = b''.join(b'<h4 style="text-align: center;">%s</h4>\n<h5 style="text-align: center;">%s</h5>' % (n, t)
               for n, t in ((b'Jim Wright', b'Commissioner'), (b'Christi Craddick', b'Chairman'), (b'Wayne Christian', b'Commissioner')))


class StatewideDTests(unittest.TestCase):
    def test_title_rule_extracts_name_across_whitespace(self):
        rows = parse('sw-tx-ltgov', b'<html><head><title>\n  Home - Lieutenant Governor\n Dan Patrick </title></head></html>')
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row['id'], row['name'], row['office'], row['body'], row['level'], row['state']),
                         ('tx-lieutenantGovernor', 'Dan Patrick', 'Lieutenant Governor', 'Texas Executive', 'state', 'TX'))
        self.assertEqual(row['website'], 'https://www.ltgov.texas.gov/')
        self.assertEqual(row['sources'][0]['id'], 'sw-tx-ltgov')

    def test_entities_suffixes_and_zero_width_characters(self):
        page = b'<h2 class="elementor-heading-title elementor-size-default">Utah Attorney General</h2> </div> </div> <div class="x"> <div class="elementor-widget-container"> <h2 class="elementor-heading-title elementor-size-default">Derek\xe2\x80\x8b Brown</h2>'
        self.assertEqual(parse('sw-ut-ag', page)[0]['name'], 'Derek Brown')
        page = b"<span class='d-block show-for-large'>Commissioner Dawn Buckingham, M.D.</span>"
        self.assertEqual(parse('sw-tx-glo', page)[0]['name'], 'Dawn Buckingham')
        page = b'<h2>Kris Warner</h2><h3>West Virginia&#39;s 31st Secretary of State</h3>'
        self.assertEqual(parse('sw-wv-sos', page)[0]['name'], 'Kris Warner')
        page = b'<img class="brxe-image block-home-intro__image" alt="Curtis E. Meier, Jr." id="x">'
        self.assertEqual(parse('sw-wy-treasurer', page)[0]['name'], 'Curtis E. Meier, Jr.')

    def test_multi_office_list_page(self):
        rows = parse('sw-sd-officials', SD)
        by_office = {}
        for r in rows: by_office.setdefault(r['office'], []).append(r)
        self.assertEqual({o: len(v) for o, v in by_office.items()},
                         {'Lieutenant Governor': 1, 'Secretary of State': 1, 'Attorney General': 1, 'Auditor': 1, 'Treasurer': 1,
                          'Commissioner of Public Lands': 1, 'Public Service Commissioner': 3})
        self.assertEqual([r['id'] for r in by_office['Public Service Commissioner']],
                         ['sd-publicServiceCommissioner-1', 'sd-publicServiceCommissioner-2', 'sd-publicServiceCommissioner-3'])
        self.assertEqual(by_office['Treasurer'][0]['name'], 'Josh Haeder')
        self.assertNotIn('website', rows[0])  # a list page is not the office's own website
        self.assertEqual(statewide.executive_offices('SD', region.STATEWIDE['SD'], rows)['publicServiceCommissioner'],
                         dict(status='collected', records=3))

    def test_railroad_commission(self):
        rows = parse('sw-tx-rrc', RRC)
        self.assertEqual([(r['id'], r['name']) for r in rows],
                         [('tx-railroadCommissioner-1', 'Jim Wright'), ('tx-railroadCommissioner-2', 'Christi Craddick'),
                          ('tx-railroadCommissioner-3', 'Wayne Christian')])

    def test_missing_marker_stops(self):
        with self.assertRaises(AssertionError):
            parse('sw-tx-ltgov', b'<title>Home</title>')
        with self.assertRaises(AssertionError):
            parse('sw-sd-officials', SD.replace(b'Lt. Governor', b'Lieutenant Governor'))

    def test_conflicting_names_stop(self):
        page = b'<meta name="twitter:title" content="Attorney General Jay Jones" /><meta name="twitter:title" content="Attorney General Jason Miyares" />'
        with self.assertRaises(AssertionError):
            parse('sw-va-ag', page)

    def test_repeated_identical_name_is_one_holder(self):
        page = b'<meta name="twitter:title" content="Attorney General Jay Jones" /><meta name="twitter:title" content="Attorney General Jay  Jones" />'
        self.assertEqual(len(parse('sw-va-ag', page)), 1)

    def test_wrong_member_count_stops(self):
        with self.assertRaises(AssertionError):
            parse('sw-tx-rrc', RRC + b'<h4 style="text-align: center;">Someone Else</h4> <h5 style="text-align: center;">Commissioner</h5>')
        with self.assertRaises(AssertionError):
            parse('sw-sd-officials', SD.replace(b'<p><strong>Public Utilities Commissioner<br> Chris Nelson (R)</strong></p>', b''))

    def test_placeholder_text_is_not_a_name(self):
        with self.assertRaises(AssertionError):
            parse('sw-wa-ltgov', b'<title>Lieutenant Governor Office of the State</title>')
        with self.assertRaises(AssertionError):
            parse('sw-wa-insurance', b'<a href="/about-us/about-the-office" class="dropdown-item" x="y">About The Office</a>')

    def test_declarations_follow_shared_vocabulary(self):
        statewide.check_declarations(region.STATEWIDE, {}, build.STATE_CODES)
        self.assertEqual(set(region.STATEWIDE), set(region.NAMES))
        self.assertEqual(region.STATEWIDE['TN'], {})
        self.assertNotIn('secretaryOfState', region.STATEWIDE['TX'])
        self.assertNotIn('attorneyGeneral', region.STATEWIDE['WY'])
        self.assertNotIn('lieutenantGovernor', region.STATEWIDE['WV'])
        self.assertEqual(set(region.STATEWIDE['VA']) - {'blockers'}, {'lieutenantGovernor', 'attorneyGeneral'})
        for st, item in region.STATEWIDE.items():
            self.assertTrue(all(v == 'collected' for k, v in item.items() if k != 'blockers'), st)

    def test_every_source_has_a_rule_and_is_https(self):
        self.assertEqual(set(region.SOURCES), {r[0] for r in region.RULES})
        for pub, url in region.SOURCES.values():
            self.assertTrue(url.startswith('https://'), url)


if __name__ == '__main__':
    unittest.main()
