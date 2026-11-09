"""Regression checks for governor extraction from official governor websites."""
import unittest
import build
from district_links import target_layer
from regions import executive as region


def source(key):
    pub, url = region.SOURCES[key]
    return dict(id=key, name=pub, url=url, retrievedAt='2026-11-09T01:00:00+00:00', sha256='a'*64, representation='http-response-body')


class GovernorTests(unittest.TestCase):
    def test_title_rule_extracts_name_across_whitespace_and_entities(self):
        page = b'<html><head><title>\n\tWelcome - \n  Kentucky Governor Andy Beshear\n</title></head></html>'
        rows = region.parse('gov-ky', page, source('gov-ky'))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row['id'], row['name'], row['office'], row['body'], row['level']),
                         ('ky-governor', 'Andy Beshear', 'Governor', 'Kentucky Executive', 'state'))
        self.assertEqual(row['website'], 'https://governor.ky.gov/')

    def test_entity_encoded_title(self):
        page = b"<title>Nevada Governor&#39;s Office | Joe Lombardo</title>"
        self.assertEqual(region.parse('gov-nv', page, source('gov-nv'))[0]['name'], 'Joe Lombardo')

    def test_missing_marker_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('gov-ky', b'<title>Welcome</title>', source('gov-ky'))

    def test_conflicting_names_stop(self):
        page = b'<p>Governor Kay Ivey, who became the 54th Governor of Alabama in 2017</p><p>Governor Someone Else, who became the 55th Governor of Alabama in 2027</p>'
        with self.assertRaises(AssertionError):
            region.parse('gov-al', page, source('gov-al'))

    def test_placeholder_text_is_not_a_name(self):
        with self.assertRaises(AssertionError):
            region.parse('gov-oh', b'<title>Governor Office of the State</title>', source('gov-oh'))

    def test_every_state_is_collected_or_explicitly_blocked(self):
        self.assertEqual(set(region.RULES) | set(region.BLOCKED), build.STATE_CODES)
        for st, item in region.EXECUTIVE.items():
            self.assertEqual(item['governor'] == 'collected', st in region.RULES)
            self.assertEqual(bool(item['blockers']), st in region.BLOCKED)

    def test_kansas_menu_link_rule(self):
        page = b'<a class="megamenu_level1" href="/about-the-office/governor-laura-kelly" aria-label="Governor Laura Kelly" data-navid="53">Governor Laura Kelly</a>'
        self.assertEqual(region.parse('gov-ks', page, source('gov-ks'))[0]['name'], 'Laura Kelly')

    def test_browser_markers(self):
        cases = {
            'gov-ma': (b'<title>Governor Maura Healey and Lt. Governor Kim Driscoll | Mass.gov</title>', 'Maura Healey'),
            'gov-mn': (b'<meta property="og:site_name" content="Office of Governor Tim Walz and Lt. Governor Peggy Flanagan">', 'Tim Walz'),
            'gov-ny': (b'<meta property="og:site_name" content="Governor Kathy Hochul">', 'Kathy Hochul'),
            'gov-ri': (b"<title>Welcome to the Office of Governor Dan McKee | Governor's Office, State of Rhode Island</title>", 'Dan McKee'),
        }
        cases.update({
            'gov-ct': (b'<title>Connecticut Governor Ned Lamont | CT.gov</title>', 'Ned Lamont'),
            'gov-co': (b"<title>Colorado Governor's Office Home Page | Colorado Governor Jared Polis</title>", 'Jared Polis'),
            'gov-tn': (b'<a href="/governor/about-bill-lee.html" aria-label="Governor Bill Lee" title="Governor Bill Lee">Governor Bill Lee</a>', 'Bill Lee'),
        })
        for key, (page, name) in cases.items():
            self.assertEqual(region.parse(key, page, source(key))[0]['name'], name)

    def test_browser_sources_are_registered(self):
        for key in region.BROWSER:
            self.assertIn(key, region.SOURCES)

    def test_governor_links_to_state_not_legislative_district(self):
        row = dict(level='state', state='NE', body='Nebraska Executive', office='Governor')
        self.assertEqual(target_layer(row), 'states')
        self.assertTrue(build.is_executive(row))

    def test_executive_coverage_must_match_rows(self):
        with self.assertRaises(AssertionError):
            build.executive_coverage('TX', region.EXECUTIVE['TX'], 0)
        self.assertEqual(build.executive_coverage('TX', region.EXECUTIVE['TX'], 1)['offices']['governor'], dict(status='collected', records=1))


if __name__ == '__main__':
    unittest.main()
