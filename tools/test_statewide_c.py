"""Regression checks for elected statewide officers in MS MO MT NE NV NH NJ NM NY NC ND OH OK OR."""
import unittest
import build
import statewide
from district_links import target_layer, statewide_rule
from regions import statewide_c as region


def source(key):
    pub, url = region.SOURCES[key]
    return dict(id=key, name=pub, url=url, retrievedAt='2026-11-10T01:00:00+00:00', sha256='a'*64, representation='http-response-body')


def parse(key, page):
    return region.parse(key, page, source(key))


class StatewideCTests(unittest.TestCase):
    def test_title_rule_extracts_name_across_whitespace_and_entities(self):
        page = b'<title>\n  Office of the New York State Comptroller |\n\tThomas P. DiNapoli </title>'
        row, = parse('sw-ny-osc', page)
        self.assertEqual((row['id'], row['name'], row['office'], row['body'], row['level'], row['website']),
                         ('ny-comptroller', 'Thomas P. DiNapoli', 'Comptroller', 'New York Executive', 'state', 'https://www.osc.ny.gov/'))

    def test_entity_encoded_marker(self):
        page = b'<p>Jill Doe, Mississippi&#8217;s 11th Commissioner of Insurance and State Fire Marshal, is serving</p>'
        self.assertEqual(parse('sw-ms-ins', page)[0]['name'], 'Jill Doe')

    def test_one_page_yields_several_offices(self):
        page = b''.join(b'<h2 class="h3">%s Jane Roe%d</h2>' % (t, i) for i, t in enumerate(
            [b'Lieutenant Governor', b'Secretary of State', b'State Treasurer', b'Attorney General', b'Auditor of Public Accounts']))
        page = page.replace(b'Roe0', b'Roe').replace(b'Roe1', b'Poe').replace(b'Roe2', b'Moe').replace(b'Roe3', b'Low').replace(b'Roe4', b'Bow')
        rows = parse('sw-ne', page)
        self.assertEqual([(r['id'], r['name']) for r in rows],
                         [('ne-lieutenantGovernor', 'Jane Roe'), ('ne-secretaryOfState', 'Jane Poe'), ('ne-treasurer', 'Jane Moe'),
                          ('ne-attorneyGeneral', 'Jane Low'), ('ne-auditor', 'Jane Bow')])

    def test_missing_marker_stops(self):
        with self.assertRaises(AssertionError):
            parse('sw-ny-osc', b'<title>Office of the New York State Comptroller</title>')
        # One office of a multi-office page missing stops the whole page.
        page = b'<h2 class="h3">Lieutenant Governor Jane Roe</h2>'
        with self.assertRaises(AssertionError):
            parse('sw-ne', page)

    def test_conflicting_names_stop(self):
        page = b'<meta name="description" content="Attorney General Dan Rayfield"><meta name="description" content="Attorney General Jane Roe">'
        with self.assertRaises(AssertionError):
            parse('sw-or-ag', page)

    def test_repeated_name_is_one_holder(self):
        page = b'<img alt="Office of Missouri Lieutenant Governor Jane Roe" /><img alt="Office of Missouri Lieutenant Governor Jane Roe" />'
        self.assertEqual(len(parse('sw-mo-lg', page)), 1)

    def test_placeholder_text_is_not_a_name(self):
        with self.assertRaises(AssertionError):
            parse('sw-nj-lg', b'<title>Lt. Governor Office of the State</title>')
        with self.assertRaises(AssertionError):
            parse('sw-nj-lg', b'<title>Lt. Governor Jane</title>')

    def test_multi_member_commission_needs_exact_seat_count(self):
        card = '<div class="cmp-card__heading"> <p>{}</p> <h2>{}</h2>'
        three = ''.join(card.format(t, n) for t, n in [('CHAIRMAN', 'Ann One'), ('COMMISSIONER', 'Bob Two'), ('COMMISSIONER', 'Cal Three')])
        rows = parse('sw-ok-occ', three.encode())
        self.assertEqual([(r['id'], r['name'], r['office']) for r in rows],
                         [('ok-corporationCommissioner-1', 'Ann One', 'Corporation Commissioner'),
                          ('ok-corporationCommissioner-2', 'Bob Two', 'Corporation Commissioner'),
                          ('ok-corporationCommissioner-3', 'Cal Three', 'Corporation Commissioner')])
        with self.assertRaises(AssertionError):
            parse('sw-ok-occ', (three + card.format('COMMISSIONER', 'Dee Four')).encode())
        with self.assertRaises(AssertionError):
            parse('sw-ok-occ', three.rsplit('<div', 1)[0].encode())

    def test_nd_commission_tabs_strip_chair_label(self):
        tab = '<button class="nav-link" id="tabs-inline-blockndit-tabs-51-tab-{0}" data-bs-toggle="tab" data-text="{1}" >'
        page = ''.join(tab.format(i, n) for i, n in enumerate(['Ann One (Current Chair)', 'Bob Two-Three', 'Cal Four']))
        self.assertEqual([r['name'] for r in parse('sw-nd-psc', page.encode())], ['Ann One', 'Bob Two-Three', 'Cal Four'])

    def test_nd_tax_commissioner_portrait_title(self):
        img = ('<img class="align-left" src="/sites/www/files/documents/about/commissioner-pics/{0}.jpg" data-entity-uuid '
               'alt="Headshot photo of {1}" width="221" height="332" title="Photo of Commissioner {1}">')
        row, = parse('sw-nd-tax', img.format('Ann-One', 'Ann One').encode())
        self.assertEqual((row['id'], row['name'], row['office'], row['body']),
                         ('nd-taxCommissioner', 'Ann One', 'Tax Commissioner', 'North Dakota Executive'))
        with self.assertRaises(AssertionError):
            parse('sw-nd-tax', b'<h1>Commissioner Bio</h1>')
        with self.assertRaises(AssertionError):
            parse('sw-nd-tax', (img.format('Ann-One', 'Ann One') + img.format('Bob-Two', 'Bob Two')).encode())

    def test_nickname_and_suffix_markers(self):
        self.assertEqual(parse('sw-nc', b''.join([
            b'<h3 class="app-card__title"><a href="https://ltgov.nc.gov/">Lieutenant Governor A Bee</a></h3>',
            b'<a href="https://ncdoj.gov/">Attorney General: B Bee</a>',
            b'<a href="https://www.ncagr.gov/">Commissioner of Agriculture: C Bee</a>',
            b'<a href="https://ncdoi.gov">Commissioner of Insurance: D Bee</a>',
            b'<a href="https://www.labor.nc.gov/">Commissioner of Labor: E Bee</a>',
            b'<a href="https://www.sosnc.gov/">Secretary of State: F. G. Bee</a>',
            b'<a href="https://www.auditor.nc.gov/">State Auditor: H Bee</a>',
            b'<a href="https://www.nctreasurer.gov/">State Treasurer: I Bee</a>',
            b'<a href="https://www.dpi.nc.gov/">Superintendent of Public Instruction: Maurice (Mo) Green</a>']))[-1]['name'], 'Maurice (Mo) Green')
        page = b'<h1>Oklahoma State <br> Auditor &amp; Inspector</h1> <p><p><strong>Cindy Byrd, CPA</strong></p>'
        self.assertEqual(parse('sw-ok-aud', page)[0]['name'], 'Cindy Byrd')

    def test_declarations_are_valid_and_cover_the_region(self):
        statewide.check_declarations(region.STATEWIDE, {}, build.STATE_CODES)
        self.assertEqual(set(region.STATEWIDE), set(region.STATES))
        for st, item in region.STATEWIDE.items():
            blocked = {office for s, office in region.BLOCKED if s == st}
            self.assertEqual({k for k, v in item.items() if v == 'not-collected'}, blocked)
            self.assertEqual(bool(item.get('blockers')), bool(blocked))
        self.assertNotIn('governor', {k for item in region.STATEWIDE.values() for k in item})

    def test_rows_agree_with_declared_coverage(self):
        rows = []
        for key, st, office, _, holders in region.RULES:
            rows.extend(dict(id=f'{st.lower()}-{office}-{n}', office=statewide.OFFICES[office][0]) for n in range(holders))
        for st in region.STATES:
            title_rows = [r for r in rows if r['id'].startswith(st.lower()+'-')]
            statewide.executive_offices(st, region.STATEWIDE[st], title_rows)

    def test_executive_rows_link_to_state(self):
        row = dict(level='state', state='NE', body='Nebraska Executive', office='Attorney General')
        self.assertEqual((target_layer(row), statewide_rule(row)), ('states', 'statewide-executive-state-fips'))

    def test_sources_are_official_https(self):
        for key, (pub, url) in region.SOURCES.items():
            self.assertTrue(url.startswith('https://'), key)
        self.assertFalse(region.BROWSER)


if __name__ == '__main__':
    unittest.main()
