import sys,types,unittest
from unittest.mock import patch
from temporal.media_ap_midwest import collect,SOURCES,STATES


def fetch(key,publisher,url,offline):
    state=url.split('/')[-2]
    return state.encode(),dict(id=key,name=publisher,url=url,finalUrl=url,sha256='fixture-'+key,retrievedAt='2026-11-05T06:00:00Z')

class APMidwestTests(unittest.TestCase):
    def run_parser(self,parser,fetcher=fetch):
        with patch.dict(sys.modules,{'temporal.media_ap':types.SimpleNamespace(parse_state=parser,collect_context=lambda *a:[])}):return collect(fetcher,True)

    def test_exact_catalog_twelve_states_twentyfour_sources(self):
        self.assertEqual(len(STATES),12);self.assertEqual(len([k for k in SOURCES if k.startswith('media-ap-midwest-')]),24)
        for key,(publisher,url) in SOURCES.items():
            if not key.startswith('media-ap-midwest-'):continue
            self.assertTrue(key.startswith('media-ap-midwest-'));self.assertEqual(publisher,'Associated Press')
            self.assertTrue(url.startswith('https://interactives.apelections.org/election-results/data-live/2026-11-03/results/races/'))

    def test_multiwinner_records_not_collapsed_into_races(self):
        def parser(m,ms,p,ps,**kwargs):
            state=m.decode();race=dict(id='race-'+state,state=state,body='state-lower',called=True)
            return [dict(id='call-'+state+'-'+n,state=state,body='state-lower') for n in ['a','b']],[race]
        p=self.run_parser(parser)
        self.assertEqual((len(p['designations']),len(p['raceStatuses']),len(p['sourceObservations'])),(24,12,24))
        self.assertTrue(all(a['designationCount']==2 for a in p['stateAudits'] if a['body']=='state-lower'))

    def test_uncalled_races_are_retained(self):
        def parser(m,ms,p,ps,**kwargs):return [],[dict(id='race-'+m.decode(),state=m.decode(),body='state-upper',called=False)]
        p=self.run_parser(parser)
        self.assertEqual(p['designations'],[]);self.assertEqual(len(p['raceStatuses']),12)
        self.assertTrue(all(a['status']=='collected' and a['designationCount']==0 for a in p['stateAudits'] if a['body']=='state-upper'))

    def test_cross_state_error_fails_closed(self):
        def parser(*args,**kwargs):return [dict(id='x',state='XX',body='state-lower')],[]
        p=self.run_parser(parser)
        self.assertEqual(p['designations'],[]);self.assertEqual(len(p['coverage']['parserFailures']),12)

    def test_blocked_sources_keep_scope_audits_without_ballot_inference(self):
        def blocked(*args):raise FileNotFoundError()
        p=self.run_parser(lambda *a:([],[]),blocked)
        self.assertEqual(len(p['stateAudits']),24);self.assertEqual(len(p['coverage']['acquisitionFailures']),24)
        self.assertTrue(all(not a['missingRowsEstablishNotOnBallot'] for a in p['stateAudits']))

if __name__=='__main__':unittest.main()
