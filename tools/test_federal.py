"""U.S. House and Senate fields beyond the roster XML: fetch retry, office addresses, house.gov websites,
Clerk member photos and the non-voting House members published in national.json."""
import subprocess
import unittest
from unittest.mock import patch
import build
import national

def source(key, url):
    return dict(id=key, url=url, name='Official publisher', retrievedAt='2026-11-10T05:00:00+00:00', sha256='a'*64)

HOUSE = source('house', build.SOURCES['house'][1])
DIRECTORY = source('house-directory', build.HOUSE_DIRECTORY[1])
KEY = '''<div class="col"><h2><span>Key to Room Codes</span></h2><ul>
<li>CHOB:&nbsp;<a href="https://www.aoc.gov/x/cannon">Cannon House Office Building</a></li>
<li>LHOB:&nbsp;<a href="https://www.aoc.gov/x/longworth">Longworth House Office Building</a></li>
<li>RHOB:&nbsp;<a href="https://www.aoc.gov/x/rayburn">Rayburn House Office Building</a></li>
<li><a href="https://www.visitthecapitol.gov/">View the campus map</a></li></ul></div>'''
HEAD = '<thead><tr><th>District</th><th>Name</th><th>Party</th><th>Office Room</th><th>Phone</th><th>Committee Assignment</th></tr></thead>'

def row(district, name, href):
    link = f'<a href="{href}">{name}</a>' if href else name
    return f'<tr><td>{district} </td><td>{link} </td><td>D</td><td>1 RHOB</td><td>(202) 225-0000</td><td>Rules</td></tr>'

def directory(alabama=('1st', 'Doe, Jane', 'https://doe.house.gov/'), extra=''):
    return (KEY + '<table id="housegov_reps_by_state-block_default-1"><caption id="state-alabama"> Alabama </caption>' + HEAD + '<tbody>'
            + row(*alabama) + row('2nd', '<a href="https://clerk.house.gov/members/AL02/vacancy">Former, Member</a>- Vacancy', None) + extra + '</tbody></table>'
            + '<table id="housegov_reps_by_state-block_default-2"><caption id="state-district-of-columbia">District of Columbia</caption>' + HEAD + '<tbody>'
            + row('Delegate', 'Norton, Eleanor', 'https://norton.house.gov/') + '</tbody></table>').encode()

def member(statedistrict, state, fullname, district, bio, namelist, official, building='RHOB', room='2136', plus4='5101'):
    return (f'<member><statedistrict>{statedistrict}</statedistrict><member-info><namelist>{namelist}</namelist><bioguideID>{bio}</bioguideID>'
            f'<official-name>{official}</official-name><party>D</party><state postal-code="{state}"><state-fullname>{fullname}</state-fullname></state>'
            f'<district>{district}</district><office-building>{building}</office-building><office-room>{room}</office-room>'
            f'<office-zip>20515</office-zip><office-zip-suffix>{plus4}</office-zip-suffix><phone>(202) 225-8050</phone></member-info></member>')

def member_data(*members):
    return ('<MemberData publish-date="November 3, 2026"><title-info><congress-num>119</congress-num></title-info><members>' + ''.join(members)
            + '<member><statedistrict>AL02</statedistrict><member-info><bioguideID /><state postal-code="AL"><state-fullname>Alabama</state-fullname></state>'
            '<district>2nd</district><office-building>RHOB</office-building></member-info></member></members></MemberData>').encode()

JANE = member('AL01', 'AL', 'Alabama', '1st', 'D000001', 'Doe, Jane', 'Jane Q. Doe', building='LHOB', room='1511', plus4='0101')
NORTON = member('DC00', 'DC', 'District of Columbia', 'Delegate', 'N000147', 'Norton, Eleanor', 'Eleanor Holmes Norton')

def clerk_page(bio, name, room, plus4, alt=None):
    return (f'<html><img src=/images/members/{bio}.jpg alt="Photo of {alt or name}"><div class="member" tabindex="0"><h3 class="library-h3">Contact</h3>'
            f'<span class="member-name"><text>The Honorable </text>{name}<!-- comment --></span><br />'
            f'<span aria-label=" {room}, "> {room} </span><br /><span class="address"> Washington,\n DC,\n 20515-{plus4} </span></div></html>').encode()


class RetryTests(unittest.TestCase):
    def curl(self, *codes):
        results = [subprocess.CalledProcessError(c, 'curl') if c else subprocess.CompletedProcess('curl', 0, b'ok', b'') for c in codes]
        def run(*args, **kwargs):
            item = results.pop(0)
            if isinstance(item, Exception): raise item
            return item
        return run

    def test_transient_transport_error_is_retried_once(self):
        for code in sorted(build.TRANSIENT_CURL):
            with self.subTest(code=code), patch.object(build.subprocess, 'run', side_effect=self.curl(code, 0)) as run, patch.object(build.time, 'sleep') as sleep:
                self.assertEqual(build.run_curl(['curl', 'https://x.gov/']).stdout, b'ok')
                self.assertEqual(run.call_count, 2)
                sleep.assert_called_once_with(build.RETRY_DELAY)

    def test_http_error_is_not_retried(self):
        with patch.object(build.subprocess, 'run', side_effect=self.curl(22, 0)) as run, patch.object(build.time, 'sleep') as sleep:
            with self.assertRaises(subprocess.CalledProcessError): build.run_curl(['curl', 'https://x.gov/'])
            self.assertEqual(run.call_count, 1)
            sleep.assert_not_called()

    def test_second_transient_failure_stops(self):
        with patch.object(build.subprocess, 'run', side_effect=self.curl(28, 28)) as run, patch.object(build.time, 'sleep'):
            with self.assertRaises(subprocess.CalledProcessError): build.run_curl(['curl', 'https://x.gov/'])
            self.assertEqual(run.call_count, 2)


class HouseTests(unittest.TestCase):
    def parsed(self, page=None, members=(JANE, NORTON)):
        buildings, seats = build.parse_house_directory(page or directory(), expected_tables=2, size=(1, 10))
        rows, delegates, details = build.parse_house(member_data(*members), dict(HOUSE), buildings)
        return rows, delegates, details, seats

    def enrich(self, row, details, seats, page):
        bio = row['ids']['bioguide']
        return build.add_house_fields(row, details[row['id']], seats, DIRECTORY, page, source('house-member-'+bio, build.CLERK_MEMBER+bio))

    def test_directory_key_and_seats(self):
        buildings, seats = build.parse_house_directory(directory(), expected_tables=2, size=(1, 10))
        self.assertEqual(buildings, {'CHOB':'Cannon House Office Building', 'LHOB':'Longworth House Office Building', 'RHOB':'Rayburn House Office Building'})
        self.assertEqual(seats, {('Alabama', '1st'): ('Doe, Jane', 'https://doe.house.gov/'), ('District of Columbia', 'Delegate'): ('Norton, Eleanor', 'https://norton.house.gov/')})

    def test_directory_changes_stop(self):
        for page in [directory().replace(b'Key to Room Codes', b'Rooms'), directory(extra=row('1st', 'Doe, Jane', 'https://doe.house.gov/')),
                     directory().replace(b'<th>Phone</th>', b'')]:
            with self.subTest(page=page[-80:]), self.assertRaises(AssertionError):
                build.parse_house_directory(page, expected_tables=2, size=(1, 10))
        with self.assertRaises(AssertionError): build.parse_house_directory(directory())

    def test_state_and_non_voting_members(self):
        rows, delegates, details, seats = self.parsed()
        self.assertEqual([(r['id'], r['state'], r['district']) for r in rows], [('us-house-D000001', 'AL', '1')])
        self.assertEqual([(r['id'], r['office'], r['territory']) for r in delegates], [('us-house-N000147', 'Delegate', 'DC')])
        self.assertNotIn('state', delegates[0])
        self.assertEqual(details['us-house-D000001'], (('Alabama', '1st'), 'Doe, Jane', '1511 Longworth House Office Building, Washington, DC 20515-0101'))

    def test_unknown_building_code_stops(self):
        with self.assertRaises(AssertionError):
            self.parsed(members=(member('AL01', 'AL', 'Alabama', '1st', 'D000001', 'Doe, Jane', 'Jane Q. Doe', building='FHOB'), NORTON))

    def test_unknown_non_voting_office_stops(self):
        with self.assertRaises(AssertionError):
            self.parsed(members=(JANE, NORTON.replace('<district>Delegate</district>', '<district>At Large</district>')))

    def test_website_address_and_photo_with_field_evidence(self):
        rows, delegates, details, seats = self.parsed()
        jane = self.enrich(rows[0], details, seats, clerk_page('D000001', 'Jane Q. Doe', '1511 Longworth House Office Building', '0101'))
        self.assertEqual(jane['website'], 'https://doe.house.gov/')
        self.assertEqual(jane['address'], '1511 Longworth House Office Building, Washington, DC 20515-0101')
        self.assertEqual(jane['photo'], 'https://clerk.house.gov/images/members/D000001.jpg')
        self.assertEqual([s['id'] for s in jane['sources']], ['house', 'house-directory', 'house-member-D000001'])
        self.assertEqual(jane['fieldEvidence'], dict(website=dict(value=jane['website'], sourceIds=['house-directory']),
            address=dict(value=jane['address'], sourceIds=['house', 'house-directory', 'house-member-D000001']),
            photo=dict(value=jane['photo'], sourceIds=['house-member-D000001'])))
        self.assertTrue(all(build.source_allowed(s) for s in jane['sources']))
        self.assertFalse(build.source_allowed(source('x', 'https://clerk.house.gov/members/D000001/votes')))

    def test_page_without_member_photo_publishes_no_photo(self):
        rows, delegates, details, seats = self.parsed()
        page = clerk_page('D000001', 'Jane Q. Doe', '1511 Longworth House Office Building', '0101').replace(b'/images/members/D000001.jpg', b'/assets/img/logo.jpg')
        self.assertNotIn('photo', self.enrich(rows[0], details, seats, page))

    def test_conflicts_stop(self):
        page = clerk_page('D000001', 'Jane Q. Doe', '1511 Longworth House Office Building', '0101')
        cases = {
            'directory names someone else': (directory(alabama=('1st', 'Roe, Jane', 'https://doe.house.gov/')), page),
            'website outside house.gov': (directory(alabama=('1st', 'Doe, Jane', 'https://doe.example.com/')), page),
            'Clerk page states another room': (directory(), page.replace(b'1511 ', b'1512 ')),
            'photo labeled for someone else': (directory(), clerk_page('D000001', 'Jane Q. Doe', '1511 Longworth House Office Building', '0101', alt='John Roe')),
            'member missing from directory': (directory(alabama=('3rd', 'Doe, Jane', 'https://doe.house.gov/')), page),
        }
        for label, (listing, member_page) in cases.items():
            rows, delegates, details, seats = self.parsed(page=listing)
            with self.subTest(label), self.assertRaises(AssertionError):
                self.enrich(rows[0], details, seats, member_page)

    def test_names_compare_without_accents_or_middle_names(self):
        self.assertTrue(build.same_member('Sanchez, Linda', 'Sánchez, Linda'))
        self.assertTrue(build.same_member('Suozzi, Thomas R.', 'Suozzi, Thomas'))
        self.assertFalse(build.same_member('Sanchez, Linda', 'Sanchez, Loretta'))

    def test_delegates_in_national_json(self):
        rows, delegates, details, seats = self.parsed()
        norton = self.enrich(delegates[0], details, seats, clerk_page('N000147', 'Eleanor Holmes Norton', '2136 Rayburn House Office Building', '5101'))
        executive = [dict(id=id, name='A Person', level='federal', jurisdiction='United States', body=national.BODY, office=office, sources=[source('us-executive', national.URL)])
                     for id, office, *_ in national.OFFICES]
        national.validate(executive + [norton], build.source_allowed)
        self.assertEqual(national.coverage(executive + [norton])['delegates'], dict(status='collected', records=1))
        self.assertNotIn('delegates', national.coverage(executive))
        with self.assertRaises(AssertionError): national.validate(executive + [dict(norton, state='DC')], build.source_allowed)
        with self.assertRaises(AssertionError): national.validate(executive + [dict(norton, office='Resident Commissioner')], build.source_allowed)
        self.assertEqual(national.TERRITORIES, build.TERRITORIES)


class SenateTests(unittest.TestCase):
    def senate(self, address):
        raw = f'<contact_information><member><first_name>Jane</first_name><last_name>Doe</last_name><state>MD</state><bioguide_id>D123</bioguide_id><party>D</party><address>{address}</address></member></contact_information>'
        return build.parse_federal('senate', raw.encode(), source('senate', build.SOURCES['senate'][1]))

    def test_office_address(self):
        self.assertEqual(self.senate('127A Russell Senate Office Building Washington DC\n      20510')[0]['address'], '127A Russell Senate Office Building, Washington, DC 20510')

    def test_changed_address_stops(self):
        for address in ['', 'Russell Senate Office Building Washington DC 20510', '374 Russell Senate Office Building Washington DC 20002']:
            with self.subTest(address=address), self.assertRaises(AssertionError): self.senate(address)

    def test_address_is_a_published_field(self):
        self.assertIn('address', build.FIELDS)
        self.assertIn('address', build.CSV_COLUMNS)
        self.assertIn('address', build.EVIDENCED)


if __name__ == '__main__':
    unittest.main()
