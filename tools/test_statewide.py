"""Checks for the shared statewide-office and high-court coverage rules."""
import unittest
import build
import statewide as v
from district_links import target_layer, statewide_rule


def row(st, office, body, id=None):
    return dict(id=id or f'{st.lower()}-{office}', name='Jane Doe', state=st, level='state', jurisdiction=st, body=body, office=office, sources=[])


class StatewideTests(unittest.TestCase):
    def test_single_office_needs_exactly_one_row(self):
        decl = {'lieutenantGovernor': 'collected'}
        rows = [row('TX', 'Lieutenant Governor', 'Texas Executive')]
        self.assertEqual(v.executive_offices('TX', decl, rows), {'lieutenantGovernor': dict(status='collected', records=1)})
        with self.assertRaises(AssertionError):
            v.executive_offices('TX', decl, rows * 2)
        with self.assertRaises(AssertionError):
            v.executive_offices('TX', decl, [])

    def test_multi_member_office_and_not_collected(self):
        decl = {'railroadCommissioner': 'collected', 'comptroller': 'not-collected', 'blockers': ['x']}
        rows = [row('TX', 'Railroad Commissioner', 'Texas Executive', f'tx-railroadCommissioner-{n}') for n in (1, 2, 3)]
        out = v.executive_offices('TX', decl, rows)
        self.assertEqual(out['railroadCommissioner']['records'], 3)
        self.assertEqual(out['comptroller'], dict(status='not-collected', records=0))

    def test_undeclared_office_rows_stop(self):
        with self.assertRaises(AssertionError):
            v.executive_offices('TX', {}, [row('TX', 'Treasurer', 'Texas Executive')])

    def test_declarations(self):
        v.check_declarations({'TX': {'treasurer': 'collected'}}, {'TX': {'Supreme Court of Texas': 'collected'}}, build.STATE_CODES)
        with self.assertRaises(AssertionError):
            v.check_declarations({'TX': {'dogCatcher': 'collected'}}, {}, build.STATE_CODES)
        with self.assertRaises(AssertionError):
            v.check_declarations({'TX': {'treasurer': 'not-collected'}}, {}, build.STATE_CODES)

    def test_courts(self):
        decl = {'Supreme Court of Texas': 'collected', 'Texas Court of Criminal Appeals': 'not-collected', 'blockers': ['x']}
        rows = [row('TX', 'Chief Justice', 'Supreme Court of Texas', 'tx-court-1'), row('TX', 'Justice', 'Supreme Court of Texas', 'tx-court-2')]
        out = v.court_coverage('TX', decl, rows)
        self.assertEqual(out['courts']['Supreme Court of Texas']['records'], 2)
        with self.assertRaises(AssertionError):
            v.court_coverage('TX', decl, rows + [row('TX', 'Senator', 'Supreme Court of Texas', 'tx-court-3')])

    def test_links_to_state(self):
        r = row('NE', 'Attorney General', 'Nebraska Executive')
        self.assertEqual((target_layer(r), statewide_rule(r)), ('states', 'statewide-executive-state-fips'))
        c = row('NE', 'Justice', 'Nebraska Supreme Court')
        self.assertEqual((target_layer(c), statewide_rule(c)), ('states', 'statewide-court-state-fips'))


if __name__ == '__main__':
    unittest.main()
