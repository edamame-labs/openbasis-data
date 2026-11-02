#!/usr/bin/env python3
"""Import a newly observed official browser DOM snapshot; never marks it as HTTP bytes."""
import argparse
import datetime as dt
import json
from pathlib import Path
import build


def import_snapshot(path, url, observed_at):
    assert build.source_allowed({'url':url}), 'Only allowlisted official URLs can be imported'
    observed=dt.datetime.fromisoformat(observed_at.replace('Z','+00:00'))
    assert observed.tzinfo is not None
    assert dt.timedelta(0)<=dt.datetime.now(dt.timezone.utc)-observed<=dt.timedelta(hours=24), 'Snapshot must be observed within 24 hours'
    raw=Path(path).read_bytes()
    assert raw.rstrip().lower().endswith(b'</html>'), 'Incomplete browser DOM export'
    cache=build.ROOT/'.source-cache'
    cache.mkdir(exist_ok=True)
    filename=build.digest(raw)+'.raw'
    (cache/filename).write_bytes(raw)
    evidence=dict(url=url,finalUrl=url,retrievedAt=observed.isoformat(),sha256=build.digest(raw),file=filename,representation='browser-dom',acquisition='Live official page serialized from document.documentElement.outerHTML; operator-supplied observation time')
    (cache/(build.digest(url.encode())+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
    print('Imported browser DOM evidence:',url,len(raw),'bytes')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True)
    p.add_argument('--url',required=True)
    p.add_argument('--observed-at',required=True)
    args=p.parse_args()
    import_snapshot(args.input,args.url,args.observed_at)
