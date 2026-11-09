import copy
import unittest
import json
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
import district_sources as districts


def feature(code='001', state='06'):
    return dict(type='Feature', properties=dict(STATE=state, GEOID=state+code, SLDU=code, OBJECTID=1), geometry=dict(type='Polygon', coordinates=[[[0,0],[1,0],[1,1],[0,0]]]))


class CensusDistrictTests(unittest.TestCase):
    def test_gateway_html_response_is_rejected_with_source_reference(self):
        with self.assertRaisesRegex(ValueError, 'https://tigerweb'):
            districts.decode_source(b'<html>Request Rejected</html>',dict(id='probe',url='https://tigerweb.geo.census.gov/probe'))

    def test_metadata_rejects_future_congress_and_vintage(self):
        metadata = dict(name='119th Congressional Districts', description='January 1, 2026 vintage', fields=[dict(name=n) for n in ['GEOID','STATE','OBJECTID','CD119']], advancedQueryCapabilities=dict(supportsPagination=True))
        districts.check_metadata(metadata, metadata['name'], 'CD119')
        future = copy.deepcopy(metadata); future['name']='120th Congressional Districts'
        with self.assertRaisesRegex(AssertionError, 'layer name'): districts.check_metadata(future, metadata['name'], 'CD119')
        future = copy.deepcopy(metadata); future['description']='January 1, 2027 vintage'
        with self.assertRaisesRegex(AssertionError, 'vintage'): districts.check_metadata(future, metadata['name'], 'CD119')

    def test_short_page_and_transfer_limit_fail_closed(self):
        page = dict(type='FeatureCollection', features=[feature()])
        with self.assertRaisesRegex(AssertionError, 'incomplete'): districts.check_page(page,'SLDU',0,2)
        page['exceededTransferLimit']=True
        with self.assertRaisesRegex(AssertionError,'transfer limit'): districts.check_page(page,'SLDU',0,1)
        page['exceededTransferLimit']=False
        self.assertEqual(len(districts.check_page(page,'SLDU',0,1)),1)

    def test_pseudo_districts_are_retained_and_labeled(self):
        self.assertEqual(districts.district_kind(dict(SLDU='ZZZ'),'SLDU'),'unassigned-area')
        self.assertEqual(districts.district_kind(dict(SLDU='001', FUNCSTAT='F'),'SLDU'),'district')
        self.assertEqual(districts.district_kind(dict(SLDU='001'),'SLDU'),'district')


    def test_collector_rejects_duplicate_districts_and_omits_generalization(self):
        seen_urls=[]
        def fetch(key, publisher, url, offline):
            seen_urls.append(url)
            if key.endswith('-metadata'):
                payload=dict(name='119th Congressional Districts',description='January 1, 2026 vintage',fields=[dict(name=n) for n in ['GEOID','STATE','OBJECTID','CD119']],advancedQueryCapabilities=dict(supportsPagination=True))
            elif key.endswith('-count'): payload={'count':2}
            else:
                one=feature();one['properties']['CD119']=one['properties'].pop('SLDU')
                two=copy.deepcopy(one);two['properties']['OBJECTID']=2
                payload=dict(type='FeatureCollection',features=[one,two])
            return json.dumps(payload).encode(),dict(id=key)
        with patch.dict(districts.LAYERS,{'cd':districts.LAYERS['cd']},clear=True), patch.dict(districts.AREA_LAYERS,{},clear=True), patch.object(districts,'STATE_FIPS',{'06'}):
            with self.assertRaisesRegex(AssertionError,'Duplicate district GEOID'):
                districts.collect(fetch)
        geometry_query=parse_qs(urlparse(seen_urls[-1]).query)
        self.assertEqual(geometry_query['outSR'],['4326'])
        self.assertFalse({'maxAllowableOffset','geometryPrecision','quantizationParameters'} & set(geometry_query))

    def test_iterator_yields_first_layer_before_fetching_second(self):
        calls=[]
        def fetch(key, publisher, url, offline):
            calls.append(key)
            self.assertTrue(key.startswith('census-state-'))
            if key.endswith('-metadata'):
                payload=dict(name='States',description='January 1, 2026 vintage',fields=[dict(name=n) for n in ['GEOID','STATE','OBJECTID']],advancedQueryCapabilities=dict(supportsPagination=True))
            elif key.endswith('-count'): payload={'count':1}
            else:
                one=feature();one['properties']['GEOID']='06'
                payload=dict(type='FeatureCollection',features=[one])
            return json.dumps(payload).encode(),dict(id=key)
        with patch.object(districts,'STATE_FIPS',{'06'}):
            iterator=districts.iter_collect(fetch)
            key,geo,evidence=next(iterator)
            self.assertEqual(key,'state')
            self.assertEqual(len(geo['features']),1)
            self.assertEqual(len(calls),3)
            iterator.close()

    def cd120_fetch(self, calls, notes):
        def fetch(key, publisher, url, offline):
            calls.append(key)
            if key.endswith('-withheld'):
                self.assertEqual(url, districts.CENSUS_CD120_NOTES)
                return notes, dict(id=key, url=url)
            if key.endswith('-metadata'):
                payload=dict(name='120th Congressional Districts',description='120th Congressional Districts; January 1, 2026 vintage',fields=[dict(name=n) for n in ['GEOID','STATE','OBJECTID','CD120']],advancedQueryCapabilities=dict(supportsPagination=True))
            elif key.endswith('-count'): payload={'count':1}
            else:
                one=feature('01','06');one['properties']['CD120']=one['properties'].pop('SLDU')
                payload=dict(type='FeatureCollection',features=[one])
            return json.dumps(payload).encode(),dict(id=key)
        return fetch

    def test_cd120_withholds_states_census_reports_as_not_in_effect(self):
        calls=[]
        notes=b'<p>*IMPORTANT NOTE: ...  The Missouri plan now remains unchanged from the plans used in the 2022 and 2024 elections.</p>'
        with patch.dict(districts.LAYERS,{'cd120':districts.LAYERS['cd120']},clear=True), patch.dict(districts.AREA_LAYERS,{},clear=True), patch.object(districts,'STATE_FIPS',{'06','29'}):
            collections,sources=districts.collect(self.cd120_fetch(calls,notes))
        fc=collections['cd120']
        self.assertEqual({f['properties']['STATE'] for f in fc['features']},{'06'})
        self.assertFalse(any(k.startswith('census-cd120-29-') and not k.endswith('-withheld') for k in calls),'Missouri geometry must not be requested')
        self.assertEqual([w['state'] for w in fc['layer']['withheldStates']],['29'])
        evidence=next(s for s in sources if s['id']=='census-cd120-29-withheld')
        self.assertEqual(evidence['withholdsState'],'29')
        self.assertIn('not joined to current officeholders',fc['layer']['applicability'])

    def test_cd120_exclusion_fails_when_census_statement_is_gone(self):
        with patch.dict(districts.LAYERS,{'cd120':districts.LAYERS['cd120']},clear=True), patch.dict(districts.AREA_LAYERS,{},clear=True), patch.object(districts,'STATE_FIPS',{'06','29'}):
            with self.assertRaisesRegex(AssertionError,'applicability statement changed'):
                districts.collect(self.cd120_fetch([],b'<p>Missouri products have been regenerated.</p>'))

    def test_only_withheld_layers_carry_withheld_metadata(self):
        calls=[]
        def fetch(key, publisher, url, offline):
            calls.append(key)
            if key.endswith('-metadata'):
                payload=dict(name='119th Congressional Districts',description='January 1, 2026 vintage',fields=[dict(name=n) for n in ['GEOID','STATE','OBJECTID','CD119']],advancedQueryCapabilities=dict(supportsPagination=True))
            elif key.endswith('-count'): payload={'count':1}
            else:
                one=feature('01','29');one['properties']['CD119']=one['properties'].pop('SLDU')
                payload=dict(type='FeatureCollection',features=[one])
            return json.dumps(payload).encode(),dict(id=key)
        with patch.dict(districts.LAYERS,{'cd':districts.LAYERS['cd']},clear=True), patch.dict(districts.AREA_LAYERS,{},clear=True), patch.object(districts,'STATE_FIPS',{'29'}):
            collections,_=districts.collect(fetch)
        self.assertNotIn('withheldStates',collections['cd']['layer'])
        self.assertEqual(len(collections['cd']['features']),1)

    def test_geometry_and_source_identifiers_required(self):
        page = dict(type='FeatureCollection',features=[feature()])
        page['features'][0]['geometry']=None
        with self.assertRaises((AssertionError, AttributeError)): districts.check_page(page,'SLDU',0,1)
        page['features'][0]=feature(); page['features'][0]['properties']['GEOID']='99999'
        with self.assertRaises(AssertionError): districts.check_page(page,'SLDU',0,1)


if __name__ == '__main__': unittest.main()
