"""Regression checks for governor extraction from official governor websites."""
import importlib.util
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

    def test_release_without_executive_rows_keeps_published_coverage(self):
        self.assertEqual(build.state_executive('TX', region.EXECUTIVE['TX'], 0, legacy=True), 'not-collected')
        with self.assertRaises(AssertionError):
            build.state_executive('TX', region.EXECUTIVE['TX'], 0, legacy=False)

    def test_executive_coverage_must_match_rows(self):
        with self.assertRaises(AssertionError):
            build.executive_coverage('TX', region.EXECUTIVE['TX'], 0)
        self.assertEqual(build.executive_coverage('TX', region.EXECUTIVE['TX'], 1)['offices']['governor'], dict(status='collected', records=1))


def tiny_pdf(lines):
    """A one-page PDF with one text line per entry."""
    text = b'BT /F1 12 Tf 72 720 Td 14 TL ' + b' '.join(b'(' + l.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)').encode('latin-1') + b") '" for l in lines) + b' ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
               b'<< /Length %d >>\nstream\n' % len(text) + text + b'\nendstream', b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out, offsets = b'%PDF-1.4\n', []
    for n, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % n + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1) + b''.join(b'%010d 00000 n \n' % o for o in offsets)
    return out + b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects) + 1, xref)


def party_source(st):
    pub, url = region.PARTY_SOURCES['gov-party-'+st.lower()]
    return dict(id='gov-party-'+st.lower(), name=pub, url=url, retrievedAt='2026-11-11T01:00:00+00:00', sha256='b'*64, representation='http-response-body')


class GovernorPartyTests(unittest.TestCase):
    ND = (b'<a href="/exhibits/governors/governors33.html">Doug Burgum</a> (R) 2016-2024<br />\n'
          b'<a href="/exhibits/governors/governors34.html">Kelly Armstrong</a> (R) 2024-present</p>')

    def test_party_is_read_from_the_entry_naming_the_governor(self):
        self.assertEqual(region.governor_party('ND', self.ND, 'Kelly Armstrong'), 'Republican')
        page = (b'<tr><td data-label="Candidate">MATT MEYER</td><td data-label="Party">Democratic Party</td>'
                b'<tr><td data-label="Candidate">MIKE RAMONE</td><td data-label="Party">Republican Party</td>')
        self.assertEqual(region.governor_party('DE', page, 'Matt Meyer'), 'Democratic')

    def test_minnesota_label_is_kept(self):
        page = (b'<th scope="row">Tim Walz</th><td> <span id="x_assumedoffice">1/7/2019</span> </td><td> <span id="x_govnum">41</span> </td><td>Democratic-Farmer-Labor</td>'
                b'<th scope="row">Alexander Ramsey</th><td> <span id="y_assumedoffice">1/2/1860</span> </td><td> <span id="y_govnum">2</span> </td><td>Republican</td>')
        self.assertEqual(region.governor_party('MN', page, 'Tim Walz'), 'Democratic-Farmer-Labor')

    def test_page_that_does_not_name_the_governor_stops(self):
        with self.assertRaises(AssertionError):
            region.governor_party('ND', self.ND, 'Someone Else')

    def test_page_with_no_entries_stops(self):
        with self.assertRaises(AssertionError):
            region.governor_party('ND', b'<p>Governors</p>', 'Kelly Armstrong')

    def test_two_parties_for_the_governor_stop(self):
        page = self.ND + b'<a href="/exhibits/governors/governors35.html">Kelly Armstrong</a> (D) 2028-present'
        with self.assertRaises(AssertionError):
            region.governor_party('ND', page, 'Kelly Armstrong')

    def test_unmapped_label_stops(self):
        page = b'<a href="/exhibits/governors/governors34.html">Kelly Armstrong</a> (Pop) 2024-present'
        with self.assertRaises(AssertionError):
            region.governor_party('ND', page, 'Kelly Armstrong')

    def test_same_person(self):
        same = [('Kay Ivey', 'IVEY, KAY'), ('J. Kevin Stitt', 'Kevin Stitt'), ('JB Pritzker', 'J.B. PRITZKER'), ('Brian P. Kemp', 'Brian Kemp'),
                ('Michelle Lujan Grisham', 'MICHELLE LUJAN GRISHAM'), ('Dan McKee', 'Daniel J. McKee'), ('Josh Shapiro', 'SHAPIRO, JOSHUA D'),
                ('Jeff Landry', '\\"Jeff\\" Landry'), ('Ned Lamont', 'Edward M. "Ned" Lamont, Jr.'), ('Wes Moore', 'WESTLEY WATENDE OMARI (WES) MOORE')]
        different = [('Mike Dunleavy', 'Dunleavy'), ('Mike Dunleavy', 'Michael J. Dunleavy'), ('Phil Scott', 'Rick Scott'), ('Kelly Ayotte', 'Kelly Armstrong'),
                     ('Jim Pillen', 'Jo Pillen'), ('Josh Green', 'Josh Greene')]
        for governor, listed in same: self.assertTrue(region.same_person(governor, listed), (governor, listed))
        for governor, listed in different: self.assertFalse(region.same_person(governor, listed), (governor, listed))

    def test_party_carries_field_evidence_and_both_references(self):
        gov = region.parse('gov-nd', b'<title>Governor Kelly Armstrong | North Dakota Office of the Governor</title>', source('gov-nd'))[0]
        row = region.add_party(gov, region.governor_party('ND', self.ND, gov['name']), party_source('ND'))
        self.assertEqual(row['party'], 'Republican')
        self.assertEqual(row['fieldEvidence'], {'party': {'value': 'Republican', 'sourceIds': ['gov-party-nd']}})
        self.assertEqual([s['id'] for s in row['sources']], ['gov-nd', 'gov-party-nd'])
        self.assertTrue(set(row) <= build.FIELDS and 'party' in build.EVIDENCED)

    def test_every_state_has_a_party_rule_or_a_reason(self):
        self.assertEqual(set(region.PARTY_RULES) | set(region.PARTY_NOT_COLLECTED), build.STATE_CODES)
        self.assertFalse(set(region.PARTY_RULES) & set(region.PARTY_NOT_COLLECTED))
        for st, (publisher, url, pattern, period) in region.PARTY_RULES.items():
            self.assertTrue(publisher and url.startswith('https://'), st)
            self.assertTrue(build.source_allowed(dict(url=url)), st)
            self.assertTrue({'name', 'party'} <= set(__import__('re').compile(pattern).groupindex), st)

    def test_party_sources_are_not_governor_sources(self):
        self.assertFalse(set(region.PARTY_SOURCES) & set(region.SOURCES))

    # Text as pdf_text returns it for each PDF source: (state, governor, party, text).
    PDF_TEXT = [
        ('AR', 'Sarah Huckabee Sanders', 'Republican', 'vote for the Office of Governor. \nGOVERNOR \nSarah Huckabee Sanders (REP) 571,105 (62.96%) \nChris Jones (DEM) 319,242 (35.20%) \nRicky Dale Harrington, Jr. (LIB) 16,690 (1.84%) \nThe Oath'),
        ('IA', 'Kim Reynolds', 'Republican', 'Chester\nJ.\nCulver\n(D)\n2007\n–\n201\n1\nT\nerry\nE.\nBranstad\n(R)\n201\n1\n–\n2017\nKim\nReynolds\n(R)\n2017\n–\n322'),
        ('KY', 'Andy Beshear', 'Democratic', 'Governor\nDemocratic Party Republican Party Write-In\nAndy\nBESHEAR\nJacqueline\nCOLEMAN\nDaniel\nCAMERON\nRobert M. "Robby"\nMILLS\nAdair 1,688 3,597 0'),
        ('MI', 'Gretchen Whitmer', 'Democratic', 'R — Rick Snyder ....................  2011-2018\nD — Gretchen Whitmer ...............  2019- 0000\nPolitical Party Designation'),
        ('MS', 'Tate Reeves', 'Republican', 'State Of Mississippi-Governor\nBrandon Presley Democrat 5782 2205 2025\nTate Reeves Republican 3516 6138 2946\nGwendolyn Gray Independent 130 125 111'),
        ('NE', 'Jim Pillen', 'Republican', 'J. James Exon (D). ................................1971-1979\nPete Ricketts (R)....................................2015-2023\nJim Pillen (R) .........................................2023-\n1'),
        ('NH', 'Kelly Ayotte', 'Republican', 'FOR GOVERNOR\n Kelly Ayotte, r  Joyce Craig, d Stephen Villee, i\nBelknap 24,732 14,762 718'),
        ('NJ', 'Mikie Sherrill', 'Democratic', 'Candidates for Governor\nTallySloganCountyPartyName Address\nMIKIE SHERRILL (w) P.O. BOX 43032\nMONTCLAIR, NJ 07043\nDemocratic\nATLANTIC DEMOCRATIC 51,201\n'
                                              'Candidates for Governor\nTallySloganCountyPartyName Address\nJACK CIATTARELLI 99 GRAYROCK ROAD Apt-Unit 202\nCLINTON, NJ 08809\nRepublican\nATLANTIC REPUBLICAN 47,603'),
        ('OH', 'Mike DeWine', 'Republican', 'For Governor and Lieutenant Governor\nVote For 1\nProvisionalAbsenteeElection DayTOTAL\nREP Mike DeWine and Jon Husted 13,553 7,247 6,119 187\n'
                                           'DEM Nan Whaley and Cheryl L. Stephens 2,777 963 1,775 39\nREP Pat DeWine 12,345 6,789 5,432 124\nDEM Marilyn Zayas 3,210 1,234 1,900 76'),
        ('SC', 'Henry McMaster', 'Republican', 'Columbia 29201, Tel. (803) 737-3000 \nMcMASTER, Henry D. [R]—(Jan. 2017–27) Richland Co.—\nresiding in'),
        ('TN', 'Bill Lee', 'Republican', '(615) 741-2001 \nTN.gov/governor\nBill Lee (R) \nGovernor of Tennessee\nBill Lee is a seventh-generation Tennessean'),
        ('WI', 'Tony Evers', 'Democratic', 'Zimmerman, Shannon   51\nTony Evers, Governor\nDemocrat\nPersonal: Born Plymouth\nJohn S. Leiber, State Treasurer\nRepublican\nPersonal: Born'),
        ('WY', 'Mark Gordon', 'Republican', 'Name Term of Office\nMark Gordon (R) Jan. 7, 2019 to Jan. 4, 2027\nMatt Mead (R) Jan. 3, 2011 to Jan. 7, 2019\nDave Freudenthal (D) Jan. 6, 2003 to Jan. 3, 2011'),
    ]

    def test_rules_for_pdf_sources_read_the_extracted_text(self):
        for st, governor, party, text in self.PDF_TEXT:
            self.assertTrue(region.PARTY_SOURCES['gov-party-'+st.lower()][1].endswith('.pdf'), st)
            self.assertEqual(region.governor_party(st, text.encode(), governor), party, st)
            with self.assertRaises(AssertionError, msg=st):
                region.governor_party(st, text.encode(), 'Someone Else')

    def test_kentucky_reads_only_the_first_column(self):
        # The certification sets the party headings above the slates; only the first heading and first slate are adjacent.
        text = dict((st, t) for st, _, _, t in self.PDF_TEXT)['KY'].encode()
        with self.assertRaises(AssertionError):
            region.governor_party('KY', text, 'Daniel Cameron')

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'pypdf is not installed; use requirements-geo.txt for PDF party sources')
    def test_pdf_response_is_read_as_text(self):
        raw = tiny_pdf(['Name Term of Office', 'Mark Gordon (R) Jan. 7, 2019 to Jan. 4, 2027', 'Matt Mead (R) Jan. 3, 2011 to Jan. 7, 2019'])
        self.assertIn('Mark Gordon (R) Jan. 7, 2019', ' '.join(region.pdf_text(raw).split()))
        self.assertEqual(region.governor_party('WY', raw, 'Mark Gordon'), 'Republican')
        with self.assertRaises(AssertionError):
            region.governor_party('WY', raw, 'Someone Else')
        self.assertEqual(region.pdf_text(raw, slice(1, 5)), '')
        self.assertTrue(set(region.PDF_PAGES) <= set(region.PARTY_RULES))


if __name__ == '__main__':
    unittest.main()
