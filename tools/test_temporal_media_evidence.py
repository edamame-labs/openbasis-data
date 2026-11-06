from unittest.mock import patch
import tempfile
import unittest
from temporal.evidence import EvidenceStore,verify_delegation
import gzip
from temporal.media_evidence import MediaEvidenceStore
from temporal.media_federal import SOURCES


class MediaEvidenceBoundaryTests(unittest.TestCase):
 def test_script_delegation_requires_exact_quoted_artifact_and_keeps_scope(self):
  authority='https://apps.texastribune.org/published.js';artifact='https://s3.amazonaws.com/publisher-election/results.json'
  rule=dict(authoritySourceId='media-script',serviceUrl=artifact,javascriptURLLiteral=True)
  raw=('const results="'+artifact+'";').encode()
  verify_delegation(gzip.compress(raw),authority,artifact,rule)
  with self.assertRaisesRegex(ValueError,'exact quoted'):
   verify_delegation(artifact.encode(),authority,artifact,rule)
  with self.assertRaisesRegex(ValueError,'exact government-designated artifact'):
   verify_delegation(raw,authority,artifact+'?different-election=1',rule)
 def test_official_catalog_does_not_accept_media_publication(self):
  key='media-federal-npr-house-data';publisher,url=SOURCES[key]
  self.assertNotIn(key,EvidenceStore.publications())
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaisesRegex(ValueError,'explicit temporal source catalog'):
    EvidenceStore(td).acquire(key,publisher,url,True)
 def test_media_exact_known_publication_allowed_unknown_url_rejected(self):
  key='media-federal-npr-house-data';publisher,url=SOURCES[key];store=MediaEvidenceStore()
  self.assertTrue(store.direct_publication(key,url))
  self.assertFalse(store.direct_publication(key,url+'?unobserved=1'))
  self.assertFalse(store.direct_publication('media-unconfigured',url))
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaisesRegex(ValueError,'explicit temporal source catalog'):
    MediaEvidenceStore(td).acquire(key,publisher,url+'?unobserved=1',True)
 def test_configured_arbitrary_host_is_not_implicitly_trusted(self):
  key='media-unknown-source';url='https://untrusted.example/results.json'
  with patch.object(MediaEvidenceStore,'publications',return_value={key:('Publisher',url)}):
   store=MediaEvidenceStore();self.assertFalse(store.direct_publication(key,url))
   with self.assertRaisesRegex(ValueError,'explicit publication delegation'):
    store.acquire(key,'Publisher',url,True)
 def test_california_ap_exact_host_is_media_only(self):
  key='media-california-ap-senate-ax';store=MediaEvidenceStore();publisher,url=store.publications()[key]
  self.assertTrue(store.direct_publication(key,url));self.assertNotIn(key,EvidenceStore.publications())
  self.assertFalse(store.direct_publication(key,url.replace('interactives.apelections.org','other.apelections.org')))

if __name__=='__main__':unittest.main()
