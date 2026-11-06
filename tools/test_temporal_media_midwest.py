import unittest
from temporal.media_midwest import parse_wpr,WI_STATEMENTS,collect
S=dict(id='media-midwest-wpr-legislative-story',sha256='fixture',retrievedAt='2026-11-05T00:00:00Z')

def fixture():
    s='<h1>Democrats flip Wisconsin Legislature, setting up single-party control</h1><meta property="article:published_time" content="2026-11-04T07:09:29+00:00">'
    for body,district,name,verb,direction,party in WI_STATEMENTS:
        label=('D-City' if party=='D' else party or '')
        clause=(name+' '+label+' '+verb+' Opponent') if direction=='before' else ('Opponent '+verb+' '+label+' '+name)
        s+='<p>In the '+district+'th '+('Senate' if body=='state-upper' else 'Assembly')+' District, '+clause+'.</p>'
    return s.encode()

class MidwestTests(unittest.TestCase):
    def test_thirteen_exact_outcomes_and_both_voice_directions(self):
        d,r=parse_wpr(fixture(),S)
        self.assertEqual((len(d),len(r)),(13,13));self.assertEqual(len({v['id'] for v in d}),13)
        self.assertTrue(all(v['callingOrganization']=='Wisconsin Public Radio' and v['certificationStatus']=='not-established' and v['callTime'] is None for v in d))
        self.assertEqual(next(v for v in d if v['name']=='Ben Gruber')['sourceProof']['winnerDirection'],'after')
        self.assertIsNone(next(v for v in d if v['name']=='Ryan Spaude')['partyLabel'])

    def test_missing_explicit_verb_not_replaced_by_votes(self):
        with self.assertRaises(AssertionError):parse_wpr(fixture().replace(b'Robyn Vining D-City defeated',b'Robyn Vining D-City leads with 100% reporting'),S)

    def test_conditional_and_concession_rejected(self):
        with self.assertRaisesRegex(AssertionError,'explicit outcome'):parse_wpr(fixture().replace(b'Robyn Vining D-City defeated',b'Robyn Vining D-City could defeated'),S)

    def test_loser_not_mistaken_for_winner(self):
        with self.assertRaisesRegex(AssertionError,'direction'):parse_wpr(fixture().replace(b'Robyn Vining D-City defeated Opponent',b'Opponent defeated Robyn Vining D-City'),S)

    def test_wrong_district_rejected(self):
        with self.assertRaisesRegex(AssertionError,'missing or ambiguous'):parse_wpr(fixture().replace(b'5th Senate',b'6th Senate'),S)

    def test_block_retains_all_six_state_scope_audits(self):
        def blocked(*args):raise FileNotFoundError()
        p=collect(blocked,True)
        self.assertEqual(len(p['stateAudits']),12);self.assertEqual(p['designations'],[])
        self.assertTrue(all(not r['missingRowsEstablishNotOnBallot'] for r in p['stateAudits']))

if __name__=='__main__':unittest.main()
