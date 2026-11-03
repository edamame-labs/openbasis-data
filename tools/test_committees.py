"""Committee roster parsing: official-id joins, roles and fail-closed matching."""
import unittest
import committees

SOURCE = {'id': 'test'}
HOUSE = b'''<MemberData><title-info><congress-num>119</congress-num></title-info>
<members>
 <member><member-info><bioguideID>A1</bioguideID><party>R</party></member-info>
  <committee-assignments><committee comcode="WM00" rank="1" leadership="Chairman"/><committee comcode="JL00" rank="1"/></committee-assignments></member>
 <member><member-info><bioguideID>B2</bioguideID><party>D</party></member-info>
  <committee-assignments><committee comcode="WM00" rank="1"/></committee-assignments></member>
 <member><member-info><bioguideID>C3</bioguideID><party>R</party></member-info>
  <committee-assignments><committee comcode="WM00" rank="2"/></committee-assignments></member>
</members>
<committees>
 <committee type="standing" comcode="WM00"><committee-fullname>Committee on  Ways and Means</committee-fullname></committee>
 <committee type="joint" comcode="JL00"><committee-fullname>Joint Committee on the Library</committee-fullname></committee>
</committees></MemberData>'''

SENATE = b'''<committee_membership><committees><committee_name>Committee on Finance</committee_name><committee_code>SSFI00</committee_code><members>
 <member><name><first>Ben Ray</first><last>Lujan</last></name><state>NM</state><position>Ranking</position></member>
 <member><name><first>Jane</first><last>Doe</last></name><state>NM</state><position>Member</position></member>
</members></committees></committee_membership>'''
SENATORS = [dict(id='us-senate-L1', state='NM', name='Ben Ray Luján'), dict(id='us-senate-D1', state='NM', name='Jane Doe')]


class CommitteeTests(unittest.TestCase):
    def test_house_roles_and_scope(self):
        ids = {'us-house-A1', 'us-house-B2', 'us-house-C3'}
        [wm] = committees.parse_house(HOUSE, SOURCE, ids, minimum=1)
        self.assertEqual(wm['name'], 'Committee on Ways and Means')
        self.assertEqual([(m['officialId'], m['role']) for m in wm['members']], [('us-house-A1', 'Chair'), ('us-house-C3', None), ('us-house-B2', 'Ranking Member')])
        with self.assertRaises(AssertionError): committees.parse_house(HOUSE, SOURCE, ids)

    def test_senate_accent_folding(self):
        c = committees.parse_senate(SENATE, SOURCE, SENATORS)
        self.assertEqual((c['id'], c['type']), ('senate-SSFI', 'standing'))
        self.assertEqual([(m['officialId'], m['role']) for m in c['members']], [('us-senate-L1', 'Ranking Member'), ('us-senate-D1', None)])

    def test_unmatched_senator_fails(self):
        with self.assertRaises(AssertionError): committees.parse_senate(SENATE, SOURCE, SENATORS[:1])

    def test_allowed_urls(self):
        self.assertTrue(committees.allowed('https://www.senate.gov/general/committee_membership/committee_memberships_SSFI.xml'))
        self.assertFalse(committees.allowed('https://www.senate.gov/general/other.xml'))
        self.assertFalse(committees.allowed('http://www.senate.gov/committees/index.htm'))


if __name__ == '__main__':
    unittest.main()
