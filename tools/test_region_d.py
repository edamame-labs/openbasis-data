"""Regression checks for browser-compatible government roster card parsing."""
import unittest
from unittest.mock import patch
import build
from regions import region_d as region


def source(key):
    pub,url=region.SOURCES[key]
    return dict(id=key,name=pub,url=url,retrievedAt='2026-11-02T01:00:00+00:00',sha256='a'*64,representation='browser-dom')


class OhioTests(unittest.TestCase):
    def cards(self, duplicate=False):
        cards=[]
        for i in range(1,34):
            district=1 if duplicate and i==33 else i
            name='Vacant' if i==13 else f'Member {i}'
            cards.append(f'<div class="media-container-portrait"><a href="/members/{i}"><div class="media-overlay-caption-text-line-1">{name}</div><div class="media-overlay-caption-text-line-2">District {district} | R</div></a></div>')
        return ('136th General Assembly'+''.join(cards)).encode()

    def test_vacant_card_is_not_a_person(self):
        rows=region.parse('oh-upper',self.cards(),source('oh-upper'))
        self.assertEqual(len(rows),32)
        self.assertNotIn('Vacant',[r['name'] for r in rows])
        self.assertTrue(all(r['website'].startswith('https://www.ohiosenate.gov/members/') for r in rows))

    def test_duplicate_occupied_district_rejected(self):
        with self.assertRaises(AssertionError):
            region.parse('oh-upper',self.cards(True),source('oh-upper'))

    def test_changed_general_assembly_rejected(self):
        with self.assertRaises(AssertionError):
            region.parse('oh-upper',self.cards().replace(b'136th',b'137th'),source('oh-upper'))


class PennsylvaniaTests(unittest.TestCase):
    def cards(self, count=50):
        return ('2025-2026 Session'+''.join(f'<div class="member" data-district="{i:03d}" data-party="D"><a class="thumb-info-wrapper" href=" /senate/members/bio/{i}/member"><span class="thumb-info-inner">Member {i}</span></a></div>' for i in range(1,count+1))).encode()

    def test_source_district_and_profile_are_preserved(self):
        rows=region.parse('pa-upper',self.cards(),source('pa-upper'))
        self.assertEqual(len(rows),50)
        self.assertEqual(rows[0]['district'],'1')
        self.assertEqual(rows[0]['website'],'https://www.palegis.us/senate/members/bio/1/member')

    def test_truncated_capture_is_rejected(self):
        with self.assertRaises(AssertionError):
            region.parse('pa-upper',self.cards(20),source('pa-upper'))

    def test_changed_session_is_rejected(self):
        with self.assertRaises(AssertionError):
            region.parse('pa-upper',self.cards().replace(b'2025-2026',b'2027-2028'),source('pa-upper'))


class OklahomaTests(unittest.TestCase):
    def test_district_placeholder_does_not_become_a_person(self):
        cards=[]
        for i in range(1,49):
            name=f'District {i}' if i==24 else f'Member {i}'
            party='' if i==24 else 'r'
            cards.append(f'<div class="sSen__item"><a class="sSen__sLink" href="/senators/{i}"><span class="sSen__sName">{name}</span><span class="sSen__sDis">District {i}</span><span class="sSen__sMaskText">{party}</span></a></div>')
        rows=region.parse('ok-upper',''.join(cards).encode(),source('ok-upper'))
        self.assertEqual(len(rows),47)
        self.assertNotIn('24',[r['district'] for r in rows])

class CollectTests(unittest.TestCase):
    def test_ohio_and_pennsylvania_are_requested_with_the_project_user_agent(self):
        requests={}
        def fetch(key, publisher, url, offline, **kwargs):
            requests[key]=kwargs
            return b'', dict(id=key)
        with patch.object(region,'parse',lambda key,raw,source:[dict(id=key)]):
            rows,sources=region.collect(fetch)
        self.assertEqual([r['id'] for r in rows],list(region.SOURCES))
        self.assertEqual([s['id'] for s in sources],list(region.SOURCES))
        for key in ['oh-upper','oh-lower','pa-upper','pa-lower']:
            self.assertEqual(requests[key],dict(user_agent=build.USER_AGENT))
        self.assertEqual(requests['ok-upper'],{})


if __name__=='__main__': unittest.main()
