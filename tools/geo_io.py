"""Lossless UTF-8 JSON/GZip artifacts; compression does not simplify geometry."""
import gzip
import json
from pathlib import Path


def read_json(path):
    path=Path(path)
    raw=path.read_bytes()
    if path.suffix=='.gz':raw=gzip.decompress(raw)
    return json.loads(raw)


def write_json(path,value,compact=False):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,
                    **({'separators':(',',':')} if compact else {'indent':2}))+'\n').encode()
    if path.suffix=='.gz':raw=gzip.compress(raw,compresslevel=6,mtime=0)
    path.write_bytes(raw)
