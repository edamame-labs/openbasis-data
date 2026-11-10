"""Regression checks for statewide-office extraction in AL AK AZ AR CA CO CT DE FL GA HI."""
import unittest
import build
import statewide as vocabulary
from regions import statewide_a as region


def source(key):
    pub, url = region.SOURCES[key]
    return dict(id=key, name=pub, url=url, retrievedAt='2026-11-10T01:00:00+00:00', sha256='a'*64, representation='http-response-body')


def ga_item(name, title):
    return f'<div class="global-teaser"><h2 class="global-teaser__title">\n   {name}\n  </h2>  <p class="global-teaser__description">\n  {title}\n </p></div>'


GA_OFFICES = [('Brian Kemp', 'Governor'), ('Burt Jones', 'Lieutenant Governor'), ('Chris Carr', 'Attorney General'),
              ('Brad Raffensperger', 'Secretary of State'), ('Richard Woods', 'State School Superintendent'),
              ('Tyler Harper', 'Commissioner of Agriculture'), ('John King', 'Commissioner of Insurance'),
              ('B&aacute;rbara Rivera Holmes', 'Commissioner of Labor'), ('Jason  Shaw', 'Public Service Commission Chairman'),
              ('Peter Hubbard', 'Public Service Commissioner'), ('Alicia M. Johnson', 'Public Service Commissioner'),
              ('Lauren McDonald, Jr', 'Public Service Commissioner'), ('Stan Wise', 'Public Service Commissioner')]


def ga_page(items=GA_OFFICES):
    return ''.join(ga_item(n, t) for n, t in items).encode()


OHA = [('Kaiali’i Kahele', 'Chair<br />Hawaiʻi Island'), ('Keoni Souza', 'Vice-Chair<br />At-Large'), ('Dan Ahuna', 'Kauaʻi &amp; Niʻihau'),
       ('Kalei Akaka', 'Oʻahu'), ('Keli‘i Akina', 'At-Large'), ('Luana Alapa', 'Molokaʻi &amp; Lānaʻi'), ('Brickwood Galuteria', 'At-Large'),
       ('Carmen Hulu Lindsey', 'Maui'), ('John D. Waiheʻe IV', 'At-Large')]


def oha_page(items=OHA):
    card = '<div class="col-3"> <img src="x.jpg" /> <p class="center"><strong><a href=https://www.oha.org/?post_type=trustee&p={0}>{1}</a></strong><br />{2} Trustee</p> </div>'
    return ''.join(card.format(17000 + i, n, seat) for i, (n, seat) in enumerate(items)).encode()


class StatewideATests(unittest.TestCase):
    def test_single_office_title_rule(self):
        page = b'<html><head><title>\n  Lieutenant Governor Sylvia Luke\n</title></head></html>'
        rows = region.parse('sw-hi-ltgov', page, source('sw-hi-ltgov'))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row['id'], row['name'], row['office'], row['body'], row['level'], row['state']),
                         ('hi-lieutenantGovernor', 'Sylvia Luke', 'Lieutenant Governor', 'Hawaii Executive', 'state', 'HI'))
        self.assertEqual(row['website'], 'https://ltgov.hawaii.gov/')

    def test_state_list_maps_titles_and_skips_governor(self):
        rows = region.parse('sw-ga', ga_page(), source('sw-ga'))
        by_office = {}
        for r in rows: by_office.setdefault(r['office'], []).append(r['name'])
        self.assertNotIn('Governor', by_office)
        self.assertEqual(by_office['Superintendent of Public Instruction'], ['Richard Woods'])
        self.assertEqual(by_office['Commissioner of Labor'], ['Bárbara Rivera Holmes'])
        self.assertEqual(by_office['Public Service Commissioner'], ['Jason Shaw', 'Peter Hubbard', 'Alicia M. Johnson', 'Lauren McDonald, Jr', 'Stan Wise'])
        self.assertEqual([r['id'] for r in rows if r['office'] == 'Public Service Commissioner'],
                         [f'ga-publicServiceCommissioner-{n}' for n in range(1, 6)])
        self.assertEqual(vocabulary.executive_offices('GA', region.STATEWIDE['GA'], rows)['publicServiceCommissioner'],
                         dict(status='collected', records=5))

    def test_unknown_office_title_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('sw-ga', ga_page(GA_OFFICES + [('Jane Doe', 'Commissioner of Something New')]), source('sw-ga'))

    def test_missing_office_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('sw-ga', ga_page([x for x in GA_OFFICES if x[1] != 'Commissioner of Labor']), source('sw-ga'))

    def test_wrong_member_count_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('sw-ga', ga_page(GA_OFFICES[:-1]), source('sw-ga'))

    def test_missing_marker_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('sw-hi-ltgov', b'<title>Office of the Lieutenant Governor</title>', source('sw-hi-ltgov'))

    def test_conflicting_names_stop(self):
        page = b'<li><a href="/ag-bio">Attorney General James Uthmeier</a></li><li><a href="/ag-bio">Attorney General Someone Else</a></li>'
        with self.assertRaises(AssertionError):
            region.parse('sw-fl-ag', page, source('sw-fl-ag'))
        # The same holder repeated in several menus is one record.
        one = b'<li><a href="/ag-bio">Attorney General James Uthmeier</a></li>'
        self.assertEqual(len(region.parse('sw-fl-ag', one * 2, source('sw-fl-ag'))), 1)

    def test_placeholder_text_is_not_a_name(self):
        with self.assertRaises(AssertionError):
            region.parse('sw-ct-treasurer', b'<title>Connecticut Office of the Treasurer Home</title>', source('sw-ct-treasurer'))

    def test_page_block_must_be_unique(self):
        block = (b'<div id="block-footergovernment" class="b"><ul><li><a href="https://www.colorado.gov/governor/">Governor Jared Polis</a></li>'
                 b'<li><a href="https://ltgovernor.colorado.gov/">Lt. Governor Dianne Primavera</a></li>'
                 b'<li><a href="https://coag.gov/">Attorney General Phil Weiser</a></li>'
                 b'<li><a href="https://www.sos.state.co.us/">Secretary of State Jena Griswold</a></li>'
                 b'<li><a href="https://treasury.colorado.gov/">State Treasurer Dave Young</a></li></ul></div>')
        rows = region.parse('sw-co', block, source('sw-co'))
        self.assertEqual(sorted(r['office'] for r in rows), ['Attorney General', 'Lieutenant Governor', 'Secretary of State', 'Treasurer'])
        with self.assertRaises(AssertionError):
            region.parse('sw-co', block * 2, source('sw-co'))

    def test_controller_and_suffixes(self):
        boe = b''.join(f'<div class="text-center text-white m-y-sm">{n}<br><span class="h5 text-white">{d}</span></div>'.encode()
                       for n, d in [('Ted Gaines', 'First District'), ('Malia M. Cohen', 'Controller')])
        rows = region.parse('sw-ca-boe', boe, source('sw-ca-boe'))
        self.assertEqual([(r['id'], r['name']) for r in rows], [('ca-controller', 'Malia M. Cohen')])
        page = b'<div id="header-office">\n California Secretary of State\n</div>\n<div id="header-name">\n Shirley N. Weber, Ph.D.\n</div>'
        self.assertEqual(region.parse('sw-ca-sos', page, source('sw-ca-sos'))[0]['name'], 'Shirley N. Weber')

    def test_florida_cfo_heading(self):
        page = '<h2 class="oh3"><strong>Meet your Chief Financial Officer Blaise Ingoglia</strong> </h2>'.encode()
        row, = region.parse('sw-fl-cfo', page, source('sw-fl-cfo'))
        self.assertEqual((row['id'], row['name'], row['office']), ('fl-chiefFinancialOfficer', 'Blaise Ingoglia', 'Chief Financial Officer'))
        with self.assertRaises(AssertionError):  # the seal alt text alone is not read
            region.parse('sw-fl-cfo', b'<img alt="Official Seal of CFO Blaise Ingoglia" />', source('sw-fl-cfo'))
        with self.assertRaises(AssertionError):
            region.parse('sw-fl-cfo', page + b'<h2 class="oh3"><strong>Meet your Chief Financial Officer Jane Roe</strong></h2>', source('sw-fl-cfo'))

    def test_oha_trustees_keep_seat_labels(self):
        rows = region.parse('sw-hi-oha', oha_page(), source('sw-hi-oha'))
        self.assertEqual([(r['id'], r['name'], r['district']) for r in rows][:3],
                         [('hi-officeOfHawaiianAffairsTrustee-1', 'Kaiali’i Kahele', 'Hawaiʻi Island'),
                          ('hi-officeOfHawaiianAffairsTrustee-2', 'Keoni Souza', 'At-Large'),
                          ('hi-officeOfHawaiianAffairsTrustee-3', 'Dan Ahuna', 'Kauaʻi & Niʻihau')])
        self.assertEqual(sum(r['district'] == 'At-Large' for r in rows), 4)
        self.assertEqual({r['office'] for r in rows}, {'Office of Hawaiian Affairs Trustee'})
        ltgov = region.parse('sw-hi-ltgov', b'<title>Lieutenant Governor Sylvia Luke</title>', source('sw-hi-ltgov'))
        self.assertEqual(vocabulary.executive_offices('HI', region.STATEWIDE['HI'], rows + ltgov)['officeOfHawaiianAffairsTrustee'],
                         dict(status='collected', records=9))

    def test_oha_wrong_count_unknown_seat_or_shared_island_seat_stops(self):
        with self.assertRaises(AssertionError):  # eight trustees
            region.parse('sw-hi-oha', oha_page(OHA[:-1]), source('sw-hi-oha'))
        with self.assertRaises(AssertionError):  # ten trustees
            region.parse('sw-hi-oha', oha_page(OHA + [('Jane Roe', 'At-Large')]), source('sw-hi-oha'))
        with self.assertRaises(AssertionError):  # unknown seat label: the card is not matched, so eight trustees
            region.parse('sw-hi-oha', oha_page(OHA[:-1] + [('John D. Waiheʻe IV', 'Kahoʻolawe')]), source('sw-hi-oha'))
        with self.assertRaises(AssertionError):  # two holders of the Maui seat
            region.parse('sw-hi-oha', oha_page(OHA[:-1] + [('John D. Waiheʻe IV', 'Maui')]), source('sw-hi-oha'))

    def test_declarations(self):
        vocabulary.check_declarations(region.STATEWIDE, {}, build.STATE_CODES)
        self.assertEqual(set(region.STATEWIDE), set(region.NAMES))
        for (st, office) in region.BLOCKED:
            self.assertEqual(region.STATEWIDE[st][office], 'not-collected')
            self.assertTrue(any(b.startswith(vocabulary.OFFICES[office][0]) for b in region.STATEWIDE[st]['blockers']))
        # Appointed offices are not declared.
        self.assertNotIn('secretaryOfState', region.STATEWIDE['DE'])
        self.assertNotIn('secretaryOfState', region.STATEWIDE['FL'])
        self.assertEqual(set(region.STATEWIDE['AK']) - {'blockers'}, {'lieutenantGovernor'})
        for key in region.SOURCES:
            self.assertTrue(key.startswith('sw-') and region.SOURCES[key][1].startswith('https://'))

    def test_module_is_discovered(self):
        statewide, _ = build.declared_statewide()
        self.assertEqual(statewide['GA'], region.STATEWIDE['GA'])


if __name__ == '__main__':
    unittest.main()
