import json
import unittest
from temporal import media_additional as m


def fixture():
 metadata=dict(**{'@type':'Article'},headline='Democrats flip Texas House amid generational wave',datePublished='2026-11-03T21:23:04-06:00',dateModified='2026-11-04T14:00:00-06:00')
 paragraphs=['Democrat Kristian Carranza flipped a seat.', 'San Antonio Rep. Mark Dorazio won reelection, as did Houston Rep. Mano DeAyala.', 'University Park Rep. Morgan Meyer won by double digits.', 'Sen. Taylor Rehmet held his seat. Rehmet won a full four-year term.', 'Another candidate led with 100% reporting.']
 return ('<script type="application/ld+json">'+json.dumps(metadata)+'</script><article>'+''.join('<p>'+p+'</p>' for p in paragraphs)+'</article>').encode()


def source():return dict(id=m.KEY,url=m.SOURCES[m.KEY][1],sha256='a'*64,retrievedAt='2026-11-05T05:27:48Z')


class AdditionalMediaTests(unittest.TestCase):
 def test_explicit_named_article_outcomes_preserve_unknown_ids_districts(self):
  rows=m.parse_article(fixture(),source())
  self.assertEqual(len(rows),5)
  self.assertTrue(all(d['district'] is None and d['sourceCandidateId'] is None and d['sourceContestId'] is None for d in rows))
  self.assertTrue(all(d['designationStatus']=='media-called-winner' and d['certificationStatus']=='not-established' for d in rows))
  self.assertTrue(all(d['callingOrganization']=='The Texas Tribune' and d['mediaCalledAt'] is None for d in rows))
  self.assertEqual(rows[0]['observedAt'],source()['retrievedAt'])
  self.assertTrue(all(len(d['sourceProof']['paragraphSha256'])==64 for d in rows))
 def test_statement_removed_fails_closed_not_leading_candidate(self):
  with self.assertRaisesRegex(AssertionError,'outcome assertion changed'):
   m.parse_article(fixture().replace(b'Morgan Meyer won',b'Morgan Meyer led'),source())
 def test_elliptical_statement_requires_reelection_verb(self):
  with self.assertRaises(AssertionError):m.parse_article(fixture().replace(b'won reelection',b'led election'),source())
 def test_old_article_or_rebound_url_rejected(self):
  with self.assertRaises(AssertionError):m.parse_article(fixture().replace(b'2026-11-03',b'2024-11-03'),source())
  s=source();s['url']='https://www.texastribune.org/other'
  with self.assertRaises(AssertionError):m.parse_article(fixture(),s)
 def test_offline_time_preserved_and_failures_explicit(self):
  def fetch(key,publisher,url,offline):
   self.assertTrue(offline);return fixture(),source()
  p=m.collect(fetch,True);self.assertEqual(len(p['designations']),5)
  self.assertEqual(p['sourceObservations'][0]['retrievedAt'],source()['retrievedAt'])
  def missing(*args):raise FileNotFoundError('Missing observation')
  p=m.collect(missing,True);self.assertEqual(p['designations'],[])
  self.assertEqual(p['stateAudits'][0]['status'],'access-blocked')

if __name__=='__main__':unittest.main()
