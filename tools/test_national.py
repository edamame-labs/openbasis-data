"""Regression checks for President and Vice President extraction from the White House administration page."""
import json
import unittest
import build
import national

SOURCE = dict(id='us-executive', name=national.PUBLISHER, url=national.URL, retrievedAt='2026-11-10T05:00:00+00:00', sha256='a'*64, representation='http-response-body')
PAGE = b'''<a href="/administration/donald-j-trump/"><img width="2000" src="https://www.whitehouse.gov/wp-content/uploads/2025/06/President-Donald-J.-Trump.png" alt="President Donald J. Trump Official Portrait" class="wp-image-14011"></a>
<h2 class="wp-block-heading" id="h-donald-j-trump"><a href="/administration/donald-j-trump/">President Donald J. Trump</a></h2>
<p>45th &amp; 47th President of the United States</p>
<h2 class="wp-block-heading" id="h-jd-vance"><a href="/administration/jd-vance/">Vice President JD Vance</a></h2>
<p>In 2024, President Donald J. Trump selected...</p>
<h2 class="wp-block-heading" id="h-the-cabinet"><a href="/administration/the-cabinet/">The Cabinet</a></h2>'''

FEC = json.dumps(dict(results=[dict(candidate_id='P80001571', name='TRUMP, DONALD J.', office='P', election_years=[2016, 2020, 2024], party='REP', party_full='REPUBLICAN PARTY')])).encode()
VPS = b'''<table width="100%" id="SortableData_table" class="display"><thead><tr><th>Name</th><th>Party</th><th>Presidency</th><th>Term</th></tr></thead><tbody>
<tr><td><a href="https://bioguide.congress.gov/search/bio/H001075">Kamala D. Harris</a></td><td>Democratic</td><td>Joseph R. Biden, Jr.</td><td>2021&#150;2025</td></tr>
<tr><td><a href="https://bioguide.congress.gov/search/bio/V000137">J.D. Vance</a><sup>40</sup></td><td>Republican</td><td>Donald Trump</td><td>2025&#150;present</td></tr>
</tbody></table><p>2. "Republican" refers to ... the present Republican Party</p>'''


def acquire(key, publisher, url, offline, user_agent=None):
    assert (publisher, url) == national.SOURCES[key] and user_agent == national.USER_AGENT
    return {'us-executive': PAGE, 'us-president-fec': FEC, 'us-vice-presidents': VPS}[key], dict(SOURCE, id=key, name=publisher, url=url)


class NationalTests(unittest.TestCase):
    def test_extracts_both_offices(self):
        rows = national.parse(PAGE, SOURCE)
        self.assertEqual([(r['id'], r['office'], r['name']) for r in rows],
                         [('us-president', 'President', 'Donald J. Trump'), ('us-vice-president', 'Vice President', 'JD Vance')])
        self.assertEqual(rows[0]['website'], 'https://www.whitehouse.gov/administration/donald-j-trump/')
        self.assertEqual(rows[0]['photo'], 'https://www.whitehouse.gov/wp-content/uploads/2025/06/President-Donald-J.-Trump.png')
        self.assertNotIn('photo', rows[1])
        self.assertTrue(all('state' not in r for r in rows))
        national.validate(rows, build.source_allowed)
        self.assertEqual(national.coverage(rows), dict(president=dict(status='collected', records=1), vicePresident=dict(status='collected', records=1)))

    def test_missing_vice_president_stops(self):
        with self.assertRaises(AssertionError):
            national.parse(PAGE.replace(b'Vice President JD Vance', b'Office of the Vice President'), SOURCE)

    def test_two_presidents_stop(self):
        extra = b'<h2><a href="/administration/someone-else/">President Someone Else</a></h2>'
        with self.assertRaises(AssertionError):
            national.parse(PAGE + extra, SOURCE)

    def test_party_from_federal_sources_with_field_evidence(self):
        rows, sources = national.collect(acquire, False)
        self.assertEqual([(r['id'], r['party'], r['fieldEvidence']['party']['sourceIds']) for r in rows],
                         [('us-president', 'Republican', ['us-president-fec']), ('us-vice-president', 'Republican', ['us-vice-presidents'])])
        self.assertEqual([s['id'] for s in sources], list(national.SOURCES))
        national.validate(rows, build.source_allowed)

    def test_party_conflicts_stop(self):
        with self.assertRaises(AssertionError): national.fec_party(FEC.replace(b'TRUMP, DONALD J.', b'DOE, JOHN'), 'Donald J. Trump')
        with self.assertRaises(AssertionError): national.fec_party(FEC.replace(b'"REP"', b'"LIB"'), 'Donald J. Trump')
        with self.assertRaises(AssertionError): national.senate_vp_party(VPS, 'Someone Else', 'Donald J. Trump')
        with self.assertRaises(AssertionError): national.senate_vp_party(VPS, 'JD Vance', 'Someone Else')
        with self.assertRaises(AssertionError): national.senate_vp_party(VPS.replace(b'2021&#150;2025', b'2021&#150;present'), 'JD Vance', 'Donald J. Trump')
        self.assertEqual(national.senate_vp_party(VPS, 'JD Vance', 'Donald J. Trump'), 'Republican')

    def test_source_is_allowlisted(self):
        self.assertTrue(build.source_allowed(SOURCE))
        self.assertFalse(build.source_allowed(dict(SOURCE, url='https://www.whitehouse.gov/news/')))


if __name__ == '__main__':
    unittest.main()
