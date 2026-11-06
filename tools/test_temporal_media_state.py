import gzip,json,unittest
from temporal.media_state import parse_governors,parse_mpr_legislative,collect,SOURCES
S=dict(id='media-state-npr-governor-data',sha256='fixture',retrievedAt='2026-11-05T03:00:00Z')

def fixture(called=True,winner='X',votes=0):
    row=dict(test=False,id='1019',office='G',officeName='Governor',resultsType='live',type='General',level='state',state='AL',
             updated=1793840630945,raceCallStatus='Called' if called else 'Too Early to Call',called=called,
             candidates=[dict(first='Example',last='Name',id='123',party='GOP',votes=votes,winner=winner,winnerDateTime='2026-11-04T06:36:23.346Z')])
    return json.dumps(dict(results=[row])).encode()

class MediaStateTests(unittest.TestCase):
    def test_explicit_call_independent_of_votes(self):
        d,r=parse_governors(fixture(votes=0),S)
        self.assertEqual(d[0]['designationStatus'],'media-called-winner');self.assertEqual(d[0]['callingOrganization'],'Associated Press')
        self.assertEqual(d[0]['callTime'],'2026-11-04T06:36:23.346Z');self.assertEqual(d[0]['sourceProof']['value'],'X')
        self.assertEqual(d[0]['certificationStatus'],'not-established');self.assertEqual(r[0]['sourceRaceId'],'1019')
        self.assertIsNone(r[0]['specialElection'])

    def test_largest_vote_uncalled_no_designation(self):
        d,r=parse_governors(fixture(called=False,winner='',votes=9999999),S)
        self.assertEqual(d,[]);self.assertEqual(r[0]['status'],'uncalled')

    def test_gzip_source_lossless_decode(self):
        self.assertEqual(parse_governors(gzip.compress(fixture()),S),parse_governors(fixture(),S))

    def test_runoff_is_not_a_called_winner(self):
        self.assertEqual(parse_governors(fixture(called=False,winner='R'),S)[0],[])

    def test_inconsistent_flags_fail_closed(self):
        with self.assertRaisesRegex(AssertionError,'Inconsistent'):parse_governors(fixture(called=False),S)
        with self.assertRaisesRegex(AssertionError,'without explicit'):parse_governors(fixture(called=True,winner=''),S)

    def test_test_election_rejected(self):
        with self.assertRaises(AssertionError):parse_governors(fixture().replace(b'"test": false',b'"test": true'),S)

    def test_duplicate_state_rejected(self):
        p=json.loads(fixture());p['results']*=2
        with self.assertRaisesRegex(AssertionError,'Duplicate'):parse_governors(json.dumps(p).encode(),S)

    def test_blocked_feed_retains_stateleg_pending(self):
        def f(*args):raise FileNotFoundError()
        p=collect(f,True)
        self.assertEqual(p['designations'],[]);self.assertEqual(p['raceStatuses'],[])
        self.assertEqual(len([r for r in p['stateAudits'] if r['body'].startswith('state-')]),100)
        self.assertTrue(all(not r['missingRowsEstablishNotOnBallot'] for r in p['stateAudits']))

class MPRLegislativeTests(unittest.TestCase):
    def fixture(self,winner=True,source='ap'):
        return json.dumps(dict(mnHouse=[dict(type='Race',source=source,apOfficeId='Y',name='State House District 1A',district='District 1A',
            candidates=[dict(type='Candidate',id='2026-11-03-polid-123',candidateId='123',name='Example Name',party='Dem',winner=winner,
                             votecount=0,lastUpdated='2026-11-04T19:06:25.000Z')])])).encode()

    def test_candidate_level_ap_flag_and_no_invented_call_time(self):
        d,a=parse_mpr_legislative(self.fixture(),S,'state-lower','mnHouse','Y')
        self.assertEqual(len(d),1);self.assertEqual(d[0]['district'],'1A')
        self.assertEqual(d[0]['sourceProof']['value'],True)
        self.assertEqual(d[0]['sourceCandidateId'],'123');self.assertIsNone(d[0]['sourceContestId'])
        self.assertIsNone(d[0]['callTime']);self.assertEqual(d[0]['publisherUpdatedAt'],'2026-11-04T19:06:25.000Z')
        self.assertEqual(a[0]['status'],'called')

    def test_false_flag_does_not_call(self):
        d,a=parse_mpr_legislative(self.fixture(False),S,'state-lower','mnHouse','Y')
        self.assertEqual(d,[]);self.assertEqual(a[0]['status'],'uncalled')

    def test_non_ap_source_not_misattributed(self):
        with self.assertRaisesRegex(AssertionError,'source/office'):parse_mpr_legislative(self.fixture(source='sos'),S,'state-lower','mnHouse','Y')

    def test_future_governor_call_rejected(self):
        early=dict(S,retrievedAt='2026-11-04T00:00:00Z')
        with self.assertRaisesRegex(AssertionError,'after source'):parse_governors(fixture(),early)

if __name__=='__main__':unittest.main()
