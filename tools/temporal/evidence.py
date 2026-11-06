"""Acquire explicit primary publications and archive their exact observations locally."""
from copy import deepcopy
import datetime as dt
import hashlib
import gzip
import json
import re
from pathlib import Path
import tarfile
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin, urldefrag, parse_qs, unquote
import importlib
import importlib.util

import build as legacy


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def government_host(host):
    from .media_common import STATE_FIPS
    return bool(host and (host.endswith('.gov') or
                          any(host.endswith('.state.' + state.lower() + '.us') for state in STATE_FIPS)))


def validate_browser_download(source, *, delegated=False):
    """Validate a primary GET download without inventing response headers.

    The caller may set delegated only after validating the configured publisher
    authority chain. The value is never read from imported source metadata.
    """
    acquisition = source.get('acquisition') or {}
    filename = acquisition.get('observedFilename')
    parsed = urlparse(source.get('url', ''))
    if (source.get('representation') != 'browser-download-body' or
            parsed.scheme != 'https' or not parsed.hostname or (not government_host(parsed.hostname) and not delegated) or parsed.username or parsed.password or
            source.get('requestMethod') != 'GET' or source.get('requestBody') is not None or
            source.get('finalUrl') is not None or acquisition.get('finalResponseURL', 'missing') is not None or
            acquisition.get('method') != 'browser-download' or acquisition.get('requestedURL') != source['url'] or
            acquisition.get('timestampBasis') != 'local-download-write-time' or
            not isinstance(filename, str) or not filename or filename in {'.', '..'} or
            any(char in filename for char in '/\\:\x00\r\n') or
            any(key in acquisition for key in ['path', 'localPath', 'downloadPath', 'absolutePath'])):
        raise ValueError('Invalid source-specific government browser download observation')


def _validate_browser_snapshot(source, representation, method):
    """Validate browser-derived representations without relabeling their bytes."""
    acquisition = source.get('acquisition') or {}
    requested = urlparse(source.get('url', ''))
    final = urlparse(source.get('finalUrl') or '')
    if (source.get('representation') != representation or
            source.get('requestMethod') != 'GET' or source.get('requestBody') is not None or
            acquisition.get('method') != method or
            acquisition.get('requestedURL') != source.get('url') or
            requested.scheme != 'https' or not requested.hostname or final.scheme != 'https' or not final.hostname or
            requested.username or requested.password or final.username or final.password or
            requested.hostname.removeprefix('www.') != final.hostname.removeprefix('www.')):
        raise ValueError('Invalid configured primary browser snapshot observation')


def validate_browser_dom(source):
    _validate_browser_snapshot(source, 'browser-dom', 'browser-dom-snapshot')


def validate_browser_accessibility(source):
    _validate_browser_snapshot(source, 'browser-accessibility-tree', 'browser-accessibility-snapshot')


def validate_browser_snapshot(source):
    if source.get('representation') == 'browser-accessibility-tree':
        validate_browser_accessibility(source)
    else:
        validate_browser_dom(source)


def redirect_location(raw):
    """Read a preserved single redirect header response, without following it."""
    text = raw.decode('ascii').replace('\\r\\n', '\n').replace('\r\n', '\n')
    lines = text.strip().splitlines()
    if not lines or not re.fullmatch(r'HTTP/[0-9.]+ (301|302|303|307|308)(?: .*| )?', lines[0]):
        raise ValueError('Expected an actual HTTP redirect response')
    locations = [line.split(':', 1)[1].strip() for line in lines[1:] if line.lower().startswith('location:')]
    if len(locations) != 1:
        raise ValueError('Redirect requires exactly one Location header')
    target = urlparse(locations[0])
    if target.scheme != 'https' or not target.hostname or target.username or target.password:
        raise ValueError('Unsafe redirect target')
    return locations[0]


def accessibility_link_urls(text, authority_url):
    """Resolve only typed native AX link values, never prose URL mentions.

    Native AX may omit HTTPS from a link's Value. Restore that scheme only
    when the visible value begins with this HTTPS authority's exact host.
    The preserved accessibility bytes are never rewritten.
    """
    authority = urlparse(authority_url)
    result = []
    for line in text.splitlines():
        if line.count('Value:') != 1:
            continue
        match = re.fullmatch(r'\s*(?:\[\d+\]|\d+)\s+link Description: [^\r\n]*?, Value: (\S+)\s*', line)
        if not match:
            continue
        value = match[1]
        if value.startswith('https://'):
            result.append(value)
        elif (authority.scheme == 'https' and authority.hostname and not authority.username and not authority.password and
              value.split('/', 1)[0].casefold() == authority.netloc.casefold() and '/' in value):
            result.append('https://' + value)
    return result


def verify_delegation(raw, authority_url, artifact_url, rule, representation='http-response-body'):
    """Verify one explicit authority edge, bounded by path and query scope.

    Trust in a non-government authority must be established recursively by the
    caller. A JSON backend declaration does not authorize arbitrary API hosts.
    """
    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = []
        def handle_starttag(self, tag, attrs):
            for field, value in attrs:
                if field in {'href', 'src'} and value:
                    self.urls.append(urljoin(authority_url, value))
    service_url = rule['serviceUrl']
    text = (gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw).decode('utf-8-sig')
    if rule.get('redirectLocation'):
        if representation != 'http-redirect-response' or redirect_location(raw) != service_url:
            raise ValueError('Redirect authority does not prove the configured service')
    elif rule.get('javascriptURLLiteral'):
        if representation != 'http-response-body' or not re.search(r'''(["'])''' + re.escape(service_url) + r'''\1''', text):
            raise ValueError('Publisher script does not contain the exact quoted service URL')
    elif rule.get('jsonField'):
        field = rule['jsonField']
        if not isinstance(field, str) or not field:
            raise ValueError('Invalid delegation JSON field')
        try:
            declared = json.loads(text)[field]
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('Authority JSON does not declare the configured service field') from exc
        if declared != service_url:
            raise ValueError('Authority JSON service differs from configured service')
    else:
        links = Links()
        if representation == 'browser-accessibility-tree':
            links.urls = accessibility_link_urls(text, authority_url)
        elif representation == 'web-extracted-text':
            links.urls = re.findall(r'https://[^\s<>\[\]"()]+', text)
        else:
            links.feed(text)
        designated = service_url in links.urls
        if rule.get('dedicatedServiceHost'):
            designated = designated or any(urldefrag(url)[0] == urldefrag(service_url)[0] for url in links.urls)
        if not designated:
            raise ValueError('Government publication does not designate the configured results service')
    service, artifact = urlparse(service_url), urlparse(artifact_url)
    scope = urlparse(rule.get('scopeUrl', service_url))
    if (any(p.scheme != 'https' or not p.hostname or p.username or p.password for p in [service, artifact, scope]) or
            len({(p.hostname, p.port) for p in [service, artifact, scope]}) != 1):
        raise ValueError('Unsafe delegated publication scope')
    for parsed in [service, artifact, scope]:
        path = unquote(parsed.path)
        if '\\' in path or any(part in {'.', '..'} for part in path.split('/')):
            raise ValueError('Unsafe delegated publication path')
    if not scope.path.strip('/'):
        if not (rule.get('dedicatedServiceHost') is True and (government_host(urlparse(authority_url).hostname) or rule.get('redirectLocation') is True)
                and not rule.get('jsonField')):
            raise ValueError('Root delegation requires a government-designated dedicated service host')
    if rule.get('scopeUrl'):
        def within(path, parent):
            return path == parent.rstrip('/') or path.startswith(parent.rstrip('/') + '/')
        if not within(artifact.path, scope.path):
            raise ValueError('Result publication is outside its government-designated election scope')
        if rule.get('jsonField'):
            if not within(scope.path, service.path):
                raise ValueError('Configured API scope is outside its declared service base')
            if not rule.get('queryScope'):
                raise ValueError('Shared delegated API requires explicit query scope')
        elif not within(service.path, scope.path):
            raise ValueError('Result service is outside its government-designated scope')
    elif artifact_url != service_url:
        raise ValueError('Only the exact government-designated artifact is allowed')
    if rule.get('queryScope'):
        actual = {}
        for key, values in parse_qs(artifact.query, keep_blank_values=True).items():
            folded = key.casefold()
            if folded in actual or len(values) != 1:
                raise ValueError('Ambiguous delegated API query scope')
            actual[folded] = values[0]
        for key, value in rule['queryScope'].items():
            if not isinstance(value, str) or actual.get(key.casefold()) != value:
                raise ValueError('Delegated API state or election query scope mismatch')


def delegation_proof(authority, rule):
    """Preserve legacy direct-government metadata byte for byte in old archives."""
    if rule.get('governmentSourceId'):
        result = dict(governmentSourceId=rule['governmentSourceId'], governmentObservationId=observation_id(authority),
                      governmentSha256=authority['sha256'], serviceUrl=rule['serviceUrl'],
                      scopeUrl=rule.get('scopeUrl', rule['serviceUrl']))
    else:
        result = dict(authoritySourceId=rule['authoritySourceId'], authorityObservationId=observation_id(authority),
                      authoritySha256=authority['sha256'], serviceUrl=rule['serviceUrl'],
                      scopeUrl=rule.get('scopeUrl', rule['serviceUrl']),
                      authorityDelegation=deepcopy(authority.get('publisherDelegation')))
    for field in ['jsonField', 'queryScope', 'dedicatedServiceHost', 'redirectLocation', 'javascriptURLLiteral']:
        if field in rule:
            result[field] = deepcopy(rule[field])
    return result


def observation_id(source):
    from .media_common import observation
    return observation(source)


class EvidenceStore:
    """No discovery from previous outputs; only exact configured government URLs."""
    def __init__(self, root=None):
        self.root = Path(root or legacy.ROOT)
        self.archive = self.root / '.temporal-evidence'
        self.memo = {}
        self.observations = {}
        self._delegation_stack = set()

    def direct_publication(self,key,url):
        """Government authority by default; other source classes opt in separately."""
        return government_host(urlparse(url).hostname)

    @staticmethod
    def publications():
        # Acquisition is denied until a source-specific subclass registers URLs.
        return {}

    @staticmethod
    def delegations():
        return {}

    @staticmethod
    def post_keys():
        return set()

    @staticmethod
    def redirect_keys():
        return set()

    def _verify_redirect_authority(self, authority, rule):
        if rule.get('redirectLocation'):
            prior = authority.get('publisherDelegation') or {}
            if (authority['id'] not in self.redirect_keys() or
                    prior.get('dedicatedServiceHost') is not True or
                    not prior.get('governmentSourceId')):
                raise ValueError('Redirect requires a government-designated dedicated authority')

    def _delegation(self, key, url, offline):
        rule = self.delegations().get(key)
        if not rule:
            raise ValueError('A government-designated service requires an explicit publication delegation')
        authority_id = rule.get('governmentSourceId') or rule.get('authoritySourceId')
        if not authority_id or authority_id not in self.publications():
            raise ValueError('Delegation authority is not a configured publication')
        if key in self._delegation_stack:
            raise ValueError('Circular publication delegation')
        publisher, authority_url = self.publications()[authority_id]
        if rule.get('governmentSourceId') and not government_host(urlparse(authority_url).hostname):
            raise ValueError('Delegation must originate at an official government publication')
        self._delegation_stack.add(key)
        try:
            raw, authority = self.acquire(authority_id, publisher, authority_url, offline)
        finally:
            self._delegation_stack.remove(key)
        if not self.direct_publication(authority_id,authority_url) and not authority.get('publisherDelegation'):
            raise ValueError('Delegation authority lacks its government provenance chain')
        self._verify_redirect_authority(authority, rule)
        verify_delegation(raw, authority_url, url, rule, authority.get('representation', 'http-response-body'))
        return delegation_proof(authority, rule)

    def acquire(self, key, publisher, url, offline=False, *, method='GET', data=None):
        approved = self.publications()
        if approved.get(key) != (publisher, url):
            raise ValueError('Publication is not in the explicit temporal source catalog: ' + key)
        if not ((method == 'GET' and data is None) or
                (method == 'POST' and key in self.post_keys() and isinstance(data, str) and data)):
            raise ValueError('Unexpected publication request method or form body')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            raise ValueError('Expected an explicit HTTPS government publication')
        delegation = self._delegation(key, url, offline) if not self.direct_publication(key,url) else None
        download_path = self.root / '.source-cache' / 'browser-download' / (key + '.json')
        redirect_path = self.root / '.source-cache' / 'http-redirect' / (key + '.json')
        reader_path = self.root / '.source-cache' / 'web-reader' / (key + '.json')
        request = (key, url, method, data) if reader_path.is_file() or download_path.is_file() else (url, method, data)
        if request not in self.memo:
            if self.root != legacy.ROOT:
                raise ValueError('Acquisition must use the repository source-cache root')
            if download_path.is_file():
                metadata = json.loads(download_path.read_text())
                if (method != 'GET' or metadata.get('url') != url or
                        metadata.get('file') != metadata.get('sha256', '') + '.raw'):
                    raise ValueError('Invalid browser download cache metadata')
                validate_browser_download(metadata, delegated=delegation is not None)
                raw = (self.root / '.source-cache' / metadata['file']).read_bytes()
                source = {k: v for k, v in metadata.items() if k != 'file'}
            elif key in self.redirect_keys():
                if method != 'GET' or not redirect_path.is_file():
                    raise ValueError('Exact configured redirect response evidence unavailable')
                metadata = json.loads(redirect_path.read_text())
                if (metadata.get('url') != url or metadata.get('representation') != 'http-redirect-response' or
                        metadata.get('file') != metadata.get('sha256', '') + '.raw'):
                    raise ValueError('Invalid redirect response metadata')
                raw = (self.root / '.source-cache' / metadata['file']).read_bytes()
                redirect_location(raw)
                source = {k: v for k, v in metadata.items() if k != 'file'}
            elif reader_path.is_file():
                metadata = json.loads(reader_path.read_text())
                if (method != 'GET' or metadata.get('representation') != 'web-extracted-text' or
                        metadata.get('acquisition', {}).get('method') != 'web-reader' or metadata.get('url') != url or
                        metadata.get('file') != metadata.get('sha256', '') + '.raw' or not self.direct_publication(key,url)):
                    raise ValueError('Invalid source-specific government reader observation')
                raw = (self.root / '.source-cache' / metadata['file']).read_bytes()
                source = {k: v for k, v in metadata.items() if k != 'file'}
            else:
                cache_key = url if method == 'GET' else url + '\nPOST\n' + data
                cache_path = self.root / '.source-cache' / (digest(cache_key.encode()) + '.json')
                dom_cache = cache_path.is_file() and json.loads(cache_path.read_text()).get('representation') in {'browser-dom', 'browser-accessibility-tree'}
                if dom_cache:
                    metadata = json.loads(cache_path.read_text())
                    if metadata.get('file') != metadata.get('sha256', '') + '.raw' or metadata.get('url') != url:
                        raise ValueError('Invalid browser DOM cache metadata')
                    source = {k: v for k, v in metadata.items() if k != 'file'}
                    validate_browser_snapshot(source)
                    validate_observations([{**source, 'id': key}], require_fresh=not offline)
                    raw = (self.root / '.source-cache' / metadata['file']).read_bytes()
                else:
                    options={'user_agent':self.http_user_agent} if getattr(self,'http_user_agent',None) else {}
                    raw, source = legacy.fetch(key, publisher, url, offline, method=method, data=data, **options)
            if source.get('representation') == 'browser-download-body':
                validate_browser_download(source, delegated=delegation is not None)
            else:
                if source.get('representation') in {'browser-dom', 'browser-accessibility-tree'}:
                    validate_browser_snapshot(source)
                final_host = urlparse(source['finalUrl']).hostname
                if not final_host or final_host.removeprefix('www.') != parsed.hostname.removeprefix('www.'):
                    raise ValueError('Publisher changed during acquisition')
            if digest(raw) != source['sha256']:
                raise ValueError('Source observation hash mismatch')
            self.memo[request] = (raw, source)
        raw, original = self.memo[request]
        source = {**deepcopy(original), 'id': key, 'name': publisher}
        if delegation:
            source['publisherDelegation'] = delegation
        self.archive_observation(raw, source)
        self.observations[key] = source
        return raw, source

    def archive_observation(self, raw, source):
        source = deepcopy(source)
        source.pop('observationId', None)
        if digest(raw) != source['sha256']:
            raise ValueError('Cannot archive altered evidence')
        obj = self.archive / 'objects' / (source['sha256'] + '.raw')
        obj.parent.mkdir(parents=True, exist_ok=True)
        if obj.exists():
            if digest(obj.read_bytes()) != source['sha256']:
                raise ValueError('Archived object was altered')
        else:
            obj.write_bytes(raw)
        meta = self.archive / 'observations' / (observation_id(source) + '.json')
        meta.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(source, sort_keys=True, ensure_ascii=False, indent=2) + '\n'
        if meta.exists() and json.loads(meta.read_text()) != source:
            raise ValueError('An immutable observation already has different metadata')
        meta.write_text(encoded)

    def closure(self, sources):
        """Normalize immutable epochs and include their exact authority observations.

        Current source registries remain unique by source ID. Transfer/history
        collections are unique by observation ID and may retain older epochs.
        Raw availability is deliberately checked only by index/export.
        """
        found = {}
        pending = list(sources)
        while pending:
            source = deepcopy(pending.pop())
            derived = source.pop('observationId', None)
            identifier = observation_id(source)
            if derived is not None and derived != identifier:
                raise ValueError('Derived observation identifier mismatch')
            validate_observations([source])
            if identifier in found:
                if found[identifier] != source:
                    raise ValueError('Conflicting immutable observation metadata')
                continue
            path = self.archive / 'observations' / (identifier + '.json')
            if path.exists() and json.loads(path.read_text()) != source:
                raise ValueError('Conflicting immutable observation metadata')
            found[identifier] = source
            proof = source.get('publisherDelegation') or {}
            authority_id = proof.get('governmentObservationId') or proof.get('authorityObservationId')
            if authority_id:
                if not re.fullmatch(r'[a-z0-9:-]+', authority_id):
                    raise ValueError('Unsafe authority observation identifier')
                authority_path = self.archive / 'observations' / (authority_id + '.json')
                if not authority_path.is_file():
                    # Inputs may already include an authority absent from local archive.
                    candidates = [v for v in sources if observation_id(v) == authority_id]
                    if not candidates:
                        raise ValueError('Exact delegation authority metadata unavailable')
                    authority = candidates[0]
                else:
                    authority = json.loads(authority_path.read_text())
                if observation_id(authority) != authority_id:
                    raise ValueError('Delegation authority observation mismatch')
                pending.append(authority)
        return [found[key] for key in sorted(found)]

    def index(self, sources):
        entries = []
        for source in sources:
            sha = source['sha256']
            obj = self.archive / 'objects' / (sha + '.raw')
            cache = self.root / '.source-cache' / (sha + '.raw')
            available = obj if obj.exists() else cache
            present = available.is_file()
            if present and digest(available.read_bytes()) != sha:
                raise ValueError('Original source bytes do not match the registered checksum')
            entries.append(dict(sourceId=source['id'], observationId=observation_id(source),
                                sha256=sha, representation=source.get('representation'),
                                retrievedAt=source['retrievedAt'], url=source['url'],
                                rawAvailableAtBuild=present, objectId='sha256:' + sha))
        return dict(schemaVersion=1, entries=entries,
                    coverage=dict(observations=len(entries), rawAvailable=sum(e['rawAvailableAtBuild'] for e in entries)),
                    storage='Exact cached bytes are local evidence, not fabricated or refreshed timestamps. Export separately for transfer; publisher materials are not relicensed.')

    def export(self, sources, destination):
        """Export only evidence for this release; fail rather than make an incomplete bundle."""
        members = {}
        observations = []
        for source in self.closure(sources):
            sha = source['sha256']
            candidates = [self.archive / 'objects' / (sha + '.raw'), self.root / '.source-cache' / (sha + '.raw')]
            obj = next((p for p in candidates if p.is_file()), None)
            if obj is None or digest(obj.read_bytes()) != sha:
                raise ValueError('Exact evidence unavailable; bundle not exported: ' + source['id'])
            members['objects/' + sha + '.raw'] = obj
            observations.append(source)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        import io
        with tarfile.open(destination, 'w:gz') as archive:
            for name, obj in sorted(members.items()):
                archive.add(obj, arcname=name, recursive=False)
            raw = (json.dumps(dict(schemaVersion=1, observations=observations), indent=2, ensure_ascii=False) + '\n').encode()
            info = tarfile.TarInfo('observations.json')
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        return dict(path=str(destination), observations=len(observations), objects=len(members), sha256=digest(destination.read_bytes()))


    def import_bundle(self, bundle):
        """Import only configured temporal publications, never extract archive paths.

        Entire bundle is checked before mutation. Observation times are preserved;
        old evidence is importable for historical replay, not relabeled fresh.
        Baseline Census evidence is outside this transfer format's allowlist.
        """
        approved = self.publications()
        with tarfile.open(bundle, 'r:gz') as archive:
            members = {}
            for member in archive.getmembers():
                name = member.name
                if name in members or not member.isfile():
                    raise ValueError('Duplicate or nonregular evidence bundle member')
                if name != 'observations.json' and not re.fullmatch(r'objects/[0-9a-f]{64}\.raw', name):
                    raise ValueError('Unexpected evidence bundle path: ' + name)
                members[name] = member
            if 'observations.json' not in members or members['observations.json'].size > 16 * 1024 * 1024:
                raise ValueError('Missing or excessive observation metadata')
            metadata = json.loads(archive.extractfile(members['observations.json']).read())
            if set(metadata) != {'schemaVersion', 'observations'} or metadata['schemaVersion'] != 1:
                raise ValueError('Unsupported evidence bundle schema')
            if not isinstance(metadata['observations'], list) or not metadata['observations']:
                raise ValueError('Expected nonempty observation list')
            sources = []
            for value in metadata['observations']:
                if not isinstance(value, dict):
                    raise ValueError('Malformed observation metadata')
                source = deepcopy(value)
                derived = source.pop('observationId', None)
                if derived is not None and derived != observation_id(source):
                    raise ValueError('Derived observation identifier mismatch')
                if approved.get(source.get('id')) != (source.get('name'), source.get('url')):
                    raise ValueError('Unconfigured primary publication in evidence bundle')
                parsed = urlparse(source['url'])
                download = source.get('representation') == 'browser-download-body'
                if download:
                    # Validate shape now; publisher authority is verified recursively
                    # below before downloaded evidence can be imported.
                    validate_browser_download(source, delegated=source['id'] in self.delegations())
                if source.get('representation') in {'browser-dom', 'browser-accessibility-tree'}:
                    validate_browser_snapshot(source)
                final = urlparse(source['url'] if download else source.get('finalUrl', source['url']))
                if (parsed.scheme != 'https' or not (self.direct_publication(source['id'],source['url']) or source['id'] in self.delegations())
                        or parsed.username or parsed.password or final.scheme != 'https' or final.username or final.password
                        or not final.hostname or final.hostname.removeprefix('www.') != parsed.hostname.removeprefix('www.')
                        or source.get('representation') not in {'http-response-body', 'web-extracted-text', 'http-redirect-response', 'browser-download-body', 'browser-dom', 'browser-accessibility-tree'}
                        or not ((source.get('requestMethod', 'GET') == 'GET' and source.get('requestBody') is None) or
                                (source.get('requestMethod') == 'POST' and source['id'] in self.post_keys() and
                                 isinstance(source.get('requestBody'), str) and source['requestBody']))):
                    raise ValueError('Unsafe or unsupported publication observation')
                if source.get('representation') == 'http-redirect-response' and source['id'] not in self.redirect_keys():
                    raise ValueError('Unconfigured redirect response publication')
                sources.append(source)
                if source.get('representation') == 'web-extracted-text' and (
                        not self.direct_publication(source['id'],source['url']) or source.get('acquisition', {}).get('method') != 'web-reader'):
                    raise ValueError('Reader extracts require explicit government-source acquisition metadata')
            clean_by_id = {}
            for source in sources:
                validate_observations([source])
                identifier = observation_id(source)
                if identifier in clean_by_id:
                    raise ValueError('Duplicate source observation in evidence bundle')
                clean_by_id[identifier] = source
            clean = [clean_by_id[key] for key in sorted(clean_by_id)]
            if len(clean) != len(sources):
                raise ValueError('Duplicate source observation in evidence bundle')
            expected = {'objects/' + s['sha256'] + '.raw' for s in clean} | {'observations.json'}
            if set(members) != expected:
                raise ValueError('Evidence objects do not exactly match observations')
            # Hash streams before writing, including any local immutable object.
            for name in sorted(expected - {'observations.json'}):
                hasher = hashlib.sha256()
                handle = archive.extractfile(members[name])
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    hasher.update(chunk)
                sha = name[8:-4]
                if hasher.hexdigest() != sha:
                    raise ValueError('Bundle object checksum mismatch')
                local = self.archive / name
                if local.exists() and digest(local.read_bytes()) != sha:
                    raise ValueError('Archived object was altered')
            source_index = {observation_id(s): s for s in clean}
            verified = set()
            def verify_chain(source, pending):
                key = source['id']
                epoch = observation_id(source)
                if epoch in verified or self.direct_publication(key,source['url']):
                    return
                if epoch in pending:
                    raise ValueError('Circular publication delegation in evidence bundle')
                rule = self.delegations()[key]
                authority_id = rule.get('governmentSourceId') or rule.get('authoritySourceId')
                proof = source.get('publisherDelegation') or {}
                authority = source_index.get(proof.get('governmentObservationId') or proof.get('authorityObservationId'))
                if authority and authority['id'] != authority_id:
                    raise ValueError('Delegation authority source mismatch')
                if not authority:
                    raise ValueError('Evidence bundle lacks the delegation authority observation')
                if rule.get('governmentSourceId') and not government_host(urlparse(authority['url']).hostname):
                    raise ValueError('Delegation must originate at an official government publication')
                verify_chain(authority, pending | {epoch})
                if source.get('publisherDelegation') != delegation_proof(authority, rule):
                    raise ValueError('Delegation evidence metadata mismatch')
                raw = archive.extractfile(members['objects/' + authority['sha256'] + '.raw']).read()
                self._verify_redirect_authority(authority, rule)
                verify_delegation(raw, authority['url'], source['url'], rule, authority.get('representation', 'http-response-body'))
                verified.add(epoch)
            for source in clean:
                verify_chain(source, set())
                if source.get('representation') == 'browser-download-body':
                    validate_browser_download(source, delegated=observation_id(source) in verified)
            cache_updates = []
            newest = {}
            for source in clean:
                path = self.archive / 'observations' / (observation_id(source) + '.json')
                if path.exists() and json.loads(path.read_text()) != source:
                    raise ValueError('Conflicting immutable observation metadata')
                request_key = source['url'] if source.get('requestMethod', 'GET') == 'GET' else source['url'] + '\nPOST\n' + source['requestBody']
                path = self.root / '.source-cache' / (digest(request_key.encode()) + '.json')
                if source.get('representation') == 'web-extracted-text':
                    path = self.root / '.source-cache' / 'web-reader' / (source['id'] + '.json')
                elif source.get('representation') == 'browser-download-body':
                    path = self.root / '.source-cache' / 'browser-download' / (source['id'] + '.json')
                elif source.get('representation') == 'http-redirect-response':
                    redirect_location(archive.extractfile(members['objects/' + source['sha256'] + '.raw']).read())
                    path = self.root / '.source-cache' / 'http-redirect' / (source['id'] + '.json')
                update = True
                prior = newest.get(path)
                if prior is None and path.exists():
                    prior = json.loads(path.read_text())
                if prior is not None:
                    if prior.get('url') != source['url']:
                        raise ValueError('Source cache URL conflict')
                    old_time = dt.datetime.fromisoformat(prior['retrievedAt'].replace('Z', '+00:00'))
                    new_time = dt.datetime.fromisoformat(source['retrievedAt'].replace('Z', '+00:00'))
                    if old_time == new_time and prior['sha256'] != source['sha256']:
                        raise ValueError('Conflicting observation at identical acquisition time')
                    update = new_time >= old_time
                cached_object = self.root / '.source-cache' / (source['sha256'] + '.raw')
                if update and cached_object.exists() and digest(cached_object.read_bytes()) != source['sha256']:
                    raise ValueError('Source cache object was altered')
                if update:
                    newest[path] = source
                cache_updates.append((source, path))
            for source, path in cache_updates:
                update = newest.get(path) is source
                raw = archive.extractfile(members['objects/' + source['sha256'] + '.raw']).read()
                self.archive_observation(raw, source)
                if update:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    filename = source['sha256'] + '.raw'
                    obj = self.root / '.source-cache' / filename
                    if obj.exists() and digest(obj.read_bytes()) != source['sha256']:
                        raise ValueError('Source cache object was altered')
                    obj.write_bytes(raw)
                    metadata = {k: deepcopy(v) for k, v in source.items() if k not in {'id', 'name'}}
                    metadata['file'] = filename
                    if source.get('representation') == 'web-extracted-text':
                        path = self.root / '.source-cache' / 'web-reader' / (source['id'] + '.json')
                        path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + '\n')
        return {'observations': len(clean), 'objects': len(expected) - 1,
                'timestampsPreserved': True, 'scope': 'configured-temporal-publications-only'}


def validate_observations(sources, require_fresh=False):
    now = dt.datetime.now(dt.timezone.utc)
    seen = {}
    for source in sources:
        identifier = source['id']
        if identifier in seen and seen[identifier] != source:
            raise ValueError('Conflicting source observations: ' + identifier)
        seen[identifier] = source
        sha = source['sha256']
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('Invalid source checksum')
        observed = dt.datetime.fromisoformat(source['retrievedAt'].replace('Z', '+00:00'))
        if observed.tzinfo is None or observed > now:
            raise ValueError('Invalid source observation time')
        if require_fresh and now - observed > dt.timedelta(hours=24):
            raise ValueError('New acquisition evidence exceeds 24 hours: ' + identifier)
    return [seen[k] for k in sorted(seen)]
