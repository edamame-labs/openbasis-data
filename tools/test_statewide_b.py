"""Regression checks for statewide-office extraction in tools/regions/statewide_b.py."""
import unittest
import build
import statewide
from regions import statewide_b as region


def source(key, retrieved='2026-11-09T01:00:00+00:00'):
    pub, url = region.SOURCES[key]
    return dict(id=key, name=pub, url=url, retrievedAt=retrieved, sha256='a'*64, representation='http-response-body')


def idaho_card(label, name, site):
    return (f'<p><strong>{label}</strong></p> </div> </div> <div class="x"> <h3 class="elementor-heading-title elementor-size-default">{name}</h3>'
            f' </div> <p><a class="link--external" href="{site}" rel="noopener noreferrer" target="_blank">site</a></p>')


def kansas_card(name, title, site):
    return (f'<a class="elementor-cta" href="{site}" target="_blank" rel="nofollow"> <div></div> '
            f'<div class="elementor-cta__title elementor-cta__content-item elementor-content-item"> {name} </div> '
            f'<div class="elementor-cta__description elementor-cta__content-item elementor-content-item"> {title} </div> </a>')


IDAHO = [('Lieutenant Governor', 'Scott Bedke (R)'), ('Secretary of State', 'Phil McGrane (R)'), ('Attorney General', 'Ra&uacute;l Labrador (R)'),
         ('State Controller', 'Brandon Woolf (R)'), ('State Treasurer', 'Julie A. Ellsworth (R)'),
         ('Superintendent of <br />Public Instruction', 'Debbie Critchfield (R)')]
KANSAS = [('David Toland', 'Lt. Governor'), ('Scott Schwab', 'Secretary of State'), ('Steven Johnson', 'State Treasurer'),
          ('Kris Kobach', 'Attorney General'), ('Vicki Schmidt', 'Insurance Commissioner')]


class StatewideBTests(unittest.TestCase):
    def test_idaho_list_extracts_every_office_with_party_and_site(self):
        page = ''.join(idaho_card(label, name, f'https://o{i}.idaho.gov/') for i, (label, name) in enumerate(IDAHO)).encode()
        rows = {r['office']: r for r in region.parse('sw-id-officials', page, source('sw-id-officials'))}
        self.assertEqual(len(rows), 6)
        ag = rows['Attorney General']
        self.assertEqual((ag['id'], ag['name'], ag['party'], ag['body'], ag['level'], ag['website']),
                         ('id-attorneyGeneral', 'Raúl Labrador', 'Republican', 'Idaho Executive', 'state', 'https://o2.idaho.gov/'))
        self.assertEqual(rows['Superintendent of Public Instruction']['name'], 'Debbie Critchfield')
        self.assertEqual(rows['Controller']['name'], 'Brandon Woolf')

    def test_kansas_list(self):
        page = ''.join(kansas_card(n, t, f'https://k{i}.ks.gov/') for i, (n, t) in enumerate(KANSAS)).encode()
        rows = {r['office']: r['name'] for r in region.parse('sw-ks-officials', page, source('sw-ks-officials'))}
        self.assertEqual(rows['Lieutenant Governor'], 'David Toland')
        self.assertEqual(rows['Insurance Commissioner'], 'Vicki Schmidt')

    def test_title_rule_across_whitespace(self):
        page = b'<title>\n Office of the Illinois Attorney General\n Kwame Raoul </title>'
        row = region.parse('sw-il-ag', page, source('sw-il-ag'))[0]
        self.assertEqual((row['id'], row['name'], row['office'], row['website']),
                         ('il-attorneyGeneral', 'Kwame Raoul', 'Attorney General', 'https://illinoisattorneygeneral.gov/'))

    def test_zero_width_characters_are_removed(self):
        page = '<h2 class="agencyElement-H2-Fancy">​A Mess​​age from Treasurer Mark H. Metcalf</h2>'.encode()
        self.assertEqual(region.parse('sw-ky-treasurer', page, source('sw-ky-treasurer'))[0]['name'], 'Mark H. Metcalf')

    def test_mass_gov_header_picks_the_titled_leader(self):
        link = ('<li class="ma__page-header__link"> <span class="ma__decorative-link ma__decorative-link--inverse"> '
                '<a href="https://www.mass.gov/person/{}" class="js-clickable-link" > <span> {}</span> <svg a="b"><use href="#x"></use></svg></a> '
                '</span> <div class="ma__page-header-legacy__description"> {} </div>')
        page = (link.format('maura-healey-governor', 'Maura Healey', 'Governor') +
                link.format('kim-driscoll-lieutenant-governor', 'Kim Driscoll', 'Lieutenant Governor')).encode()
        self.assertEqual(region.parse('sw-ma-governor', page, source('sw-ma-governor'))[0]['name'], 'Kim Driscoll')

    def test_minnesota_lrl_first_state_row_and_name_order(self):
        head = '<table> <colgroup> <col /> </colgroup> <thead> <tr> <th>ASSUMED OFFICE</th> <th>SECRETARY OF STATE</th> <th>RESIDENCE</th> </tr> </thead> '
        territory = '<table> <thead> <tr> <th>ASSUMED OFFICE</th> <th>SECRETARY OF STATE</th> <th>RESIDENCE</th> </tr> </thead> <tbody> <tr> <td>1857 April 23</td> <td>Chase, Charles L.</td> </tr>'
        page = (head + '<tbody> <tr> <td>2015 January 5</td> <td>Simon, Steve</td> <td>Saint Louis Park</td> </tr> <tr> <td>2007 January 2</td> <td>Ritchie, Mark</td> </tr> </tbody> </table>' + territory).encode()
        self.assertEqual(region.parse('sw-mn-sos', page, source('sw-mn-sos'))[0]['name'], 'Steve Simon')

    def test_minnesota_row_dated_after_retrieval_stops(self):
        page = (b'</colgroup> <thead> <tr> <th>ASSUMED OFFICE</th> <th>NAME</th> <th>PARTY</th> <th>RESIDENCE</th> <th>OCCUPATION</th> </tr> </thead> '
                b'<tbody> <tr> <td>1/4/2027</td> <td>Jane Doe</td> <td>Republican</td>')
        with self.assertRaises(AssertionError):
            region.parse('sw-mn-ltgov', page, source('sw-mn-ltgov'))
        row = region.parse('sw-mn-ltgov', page, source('sw-mn-ltgov', '2027-01-05T00:00:00+00:00'))[0]
        self.assertEqual((row['name'], row['party']), ('Jane Doe', 'Republican'))

    def test_missing_marker_stops(self):
        with self.assertRaises(AssertionError):
            region.parse('sw-il-ag', b'<title>Office of the Illinois Attorney General</title>', source('sw-il-ag'))
        # A list page missing one office stops, even when the others are present.
        page = ''.join(kansas_card(n, t, 'https://k.ks.gov/') for n, t in KANSAS[:-1]).encode()
        with self.assertRaises(AssertionError):
            region.parse('sw-ks-officials', page, source('sw-ks-officials'))

    def test_conflicting_names_stop(self):
        page = b'<h1>Attorney General Todd Rokita</h1><h1>Attorney General Jane Roe</h1>'
        with self.assertRaises(AssertionError):
            region.parse('sw-in-ag', page, source('sw-in-ag'))

    def test_placeholder_text_is_not_a_name(self):
        with self.assertRaises(AssertionError):
            region.parse('sw-in-ag', b'<h1>Attorney General Office Home</h1>', source('sw-in-ag'))

    def test_comptroller_name_keeps_middle_initial(self):
        page = b'<meta name="description" content="Office of the Comptroller of Maryland, led by Comptroller Brooke E. Lierman. Working towards a more equitable Maryland."/>'
        self.assertEqual(region.parse('sw-md-comptroller', page, source('sw-md-comptroller'))[0]['name'], 'Brooke E. Lierman')

    def test_michigan_university_boards_need_eight_members(self):
        msu_card = ('<h2 class="line">{}</h2><div class="mixed-content-text"><div class="ck-content"><p style="margin-left:0px;">'
                    '{}Term ends Jan. 1, 2031</p></div></div>')
        msu = [('Ann One', 'Chair | '), ('Bob Two', 'Vice Chair | ')] + [(f'Member {w}', '') for w in 'Cee Dee Eee Fee Gee Hee'.split()]
        page = ''.join(msu_card.format(n, label) for n, label in msu)
        # A span-wrapped term line and the "Committees" card (no term line) are handled.
        page = page.replace('<p style="margin-left:0px;">Term', '<p><span style="x"><span style="y">Term', 1)
        page += '<h2 class="line">Committees</h2><a href="/committees" class="cta green">View Members</a>'
        rows = region.parse('sw-mi-msu', page.encode(), source('sw-mi-msu'))
        self.assertEqual([(r['id'], r['name']) for r in rows][:3],
                         [('mi-universityTrustee-1', 'Ann One'), ('mi-universityTrustee-2', 'Bob Two'), ('mi-universityTrustee-3', 'Member Cee')])
        self.assertEqual(len(rows), 8)
        msu_rows = rows
        with self.assertRaises(AssertionError):
            region.parse('sw-mi-msu', ''.join(msu_card.format(n, l) for n, l in msu[:7]).encode(), source('sw-mi-msu'))
        wsu_card = '<div id="promo-{}" class="my-1 font-bold text-lg group-hover:underline leading-snug"> {} </div>'
        wsu = ['Bryan C. Barnhill II, Chair'] + [f'Member {w}' for w in 'Bee Cee Dee Eee Fee Gee Hee'.split()]
        rows = region.parse('sw-mi-wsu', ''.join(wsu_card.format(i, n) for i, n in enumerate(wsu)).encode(), source('sw-mi-wsu'))
        self.assertEqual((rows[0]['id'], rows[0]['name'], rows[0]['office']),
                         ('mi-universityGovernor-1', 'Bryan C. Barnhill II', 'University Board of Governors Member'))
        coverage = statewide.executive_offices('MI', region.STATEWIDE['MI'], msu_rows + rows)
        self.assertEqual((coverage['universityTrustee'], coverage['universityGovernor']), (dict(status='collected', records=8),) * 2)
        with self.assertRaises(AssertionError):  # a ninth card, such as an ex officio president, stops the build
            region.parse('sw-mi-wsu', ''.join(wsu_card.format(i, n) for i, n in enumerate(wsu + ['Jane Roe'])).encode(), source('sw-mi-wsu'))

    def test_declarations(self):
        statewide.check_declarations(region.STATEWIDE, {}, build.STATE_CODES)
        self.assertEqual(set(region.STATEWIDE), set(region.NAMES))
        self.assertEqual(region.STATEWIDE['ME'], {'blockers': []})
        for st, item in region.STATEWIDE.items():
            for office, status in item.items():
                if office == 'blockers': continue
                self.assertEqual(status == 'collected', any(r[:2] == (st, office) for r in region.RULES), (st, office))
        self.assertEqual(region.STATEWIDE['MI'].get('lieutenantGovernor'), 'not-collected')
        for st, office in region.HOLDERS:
            self.assertIn(office, statewide.MULTI)
        self.assertTrue(all(office not in statewide.MULTI or (st, office) in region.HOLDERS for st, office, _, _ in region.RULES))

    def test_every_source_is_read(self):
        self.assertEqual({key for _, _, key, _ in region.RULES}, set(region.SOURCES))
        self.assertTrue(all(url.startswith('https://') for _, url in region.SOURCES.values()))


if __name__ == '__main__':
    unittest.main()
