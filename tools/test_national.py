"""Regression checks for President and Vice President extraction from the White House administration page."""
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

    def test_source_is_allowlisted(self):
        self.assertTrue(build.source_allowed(SOURCE))
        self.assertFalse(build.source_allowed(dict(SOURCE, url='https://www.whitehouse.gov/news/')))


if __name__ == '__main__':
    unittest.main()
