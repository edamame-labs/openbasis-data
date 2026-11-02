"""Regression tests for government roster extraction and fail-closed behavior."""
import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import json
import datetime as dt
import build

SOURCE = {'id':'test','url':'https://www.ncleg.gov/Members/MemberTable/S','name':'Official publisher','retrievedAt':'2026-11-01T00:00:00+00:00','sha256':'a'*64}

class RosterTests(unittest.TestCase):
    def test_html_nested_text(self):
        self.assertEqual(build.HTML(b'<div><b>Jane</b> Doe &amp; Co.</div>').root.text(),'Jane Doe & Co.')

    def test_empty_roster_is_rejected(self):
        for key in ['ca-upper','ca-lower','nc-upper','nc-lower']:
            with self.subTest(key=key), self.assertRaises((AssertionError,ValueError)):
                build.parse_state(key,b'<html><p>No roster available</p></html>',SOURCE)

    def test_nc_former_members_excluded_and_duplicates_rejected(self):
        def row(d,name,note=''):
            return f'<tr><td>D</td><td>{d}</td><td>{d}</td><td>Surname</td><td><a href="/Members/Biography/S/{d}">{name}</a><span>{note}</span></td><td>County</td></tr>'
        rows=''.join(row(i,f'Member {i}') for i in range(1,51))
        text='2025-2026 Session<table id="memberTable">'+rows+row(1,'Former Member','(Resigned 3/26/25)')+'</table>'
        parsed=build.parse_state('nc-upper',text.encode(),SOURCE)
        self.assertEqual(len(parsed),50)
        self.assertNotIn('Former Member',[r['name'] for r in parsed])
        duplicate='2025-2026 Session<table id="memberTable">'+''.join(row(i if i<50 else 1,f'Member {i}') for i in range(1,51))+'</table>'
        with self.assertRaises(AssertionError):
            build.parse_state('nc-upper',duplicate.encode(),SOURCE)

    def test_senate_email_field_is_not_published_as_email(self):
        raw=b'<contact_information><member><first_name>Jane</first_name><last_name>Doe</last_name><state>CA</state><bioguide_id>D123</bioguide_id><party>D</party><email>https://example.gov/</email></member></contact_information>'
        r=build.parse_federal('senate',raw,SOURCE)[0]
        self.assertNotIn('email',r)
        self.assertEqual(r['sources'],[SOURCE])

    def test_named_and_alphanumeric_districts_are_preserved(self):
        for district in ['7A','Chittenden Central','Windsor-1']:
            row=build.record(SOURCE,'id','Jane Doe','VT','state','Vermont House',district)
            self.assertEqual(row['district'],district)

    def test_no_municipal_or_territory_records(self):
        with self.assertRaises(AssertionError):
            build.record(SOURCE,'id','Person','DC','federal','U.S. House')

class FailureTests(unittest.TestCase):
    def test_failed_source_keeps_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'data').mkdir()
            (root/'data/sentinel').write_text('previous snapshot')
            with patch.object(build,'ROOT',root), patch.object(build,'fetch',side_effect=RuntimeError('source unavailable')):
                with self.assertRaises(RuntimeError): build.build()
            self.assertEqual((root/'data/sentinel').read_text(),'previous snapshot')
            self.assertEqual(list(root.glob('primary-data-*')),[])

    def browser_cache(self, root, observed):
        cache=root/'.source-cache'
        cache.mkdir()
        url='https://www.ohiohouse.gov/members/directory'
        raw=b'<html>Live official directory</html>'
        (cache/'snapshot.raw').write_bytes(raw)
        (cache/(build.digest(url.encode())+'.json')).write_text(json.dumps(dict(url=url,file='snapshot.raw',sha256=build.digest(raw),retrievedAt=observed.isoformat(),representation='browser-dom')))
        return url

    def test_browser_evidence_requires_explicit_acquisition_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            url=self.browser_cache(root,dt.datetime.now(dt.timezone.utc))
            with patch.object(build,'ROOT',root), patch.object(build.subprocess,'run') as network:
                with self.assertRaises(RuntimeError): build.fetch('oh-lower','Ohio House',url)
                network.assert_not_called()

    def test_explicit_browser_evidence_preserves_observation_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            observed=dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=30)
            url=self.browser_cache(root,observed)
            with patch.object(build,'ROOT',root), patch.object(build.subprocess,'run') as network:
                _,source=build.fetch('oh-lower','Ohio House',url,browser_snapshots=True)
                self.assertEqual(source['retrievedAt'],observed.isoformat())
                self.assertEqual(source['representation'],'browser-dom')
                network.assert_not_called()

    def test_expired_browser_observation_cannot_enter_live_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            url=self.browser_cache(root,dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=25))
            with patch.object(build,'ROOT',root), self.assertRaises(AssertionError):
                build.fetch('oh-lower','Ohio House',url,browser_snapshots=True)

    def test_offline_response_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            cache=root/'.source-cache'
            cache.mkdir()
            url='https://clerk.house.gov/xml/lists/MemberData.xml'
            (cache/'snapshot.raw').write_bytes(b'changed')
            (cache/(build.digest(url.encode())+'.json')).write_text(json.dumps(dict(url=url,file='snapshot.raw',sha256=build.digest(b'original'))))
            with patch.object(build,'ROOT',root), self.assertRaises(AssertionError):
                build.fetch('house','House Clerk',url,True)

if __name__=='__main__':
    unittest.main()
