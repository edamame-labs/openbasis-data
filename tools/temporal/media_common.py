"""Stable election identifiers and evidence hashes for media observations."""
import hashlib
import json

ELECTION_ID = "us-2026-general"
ELECTION_DATE = "2026-11-03"
STATE_FIPS=dict(zip('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split(),'01 02 04 05 06 08 09 10 12 13 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 54 55 56'.split()))

def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def observation(source):
    assert source.get("sha256") and source.get("retrievedAt") and source.get("id"), "Incomplete observation provenance"
    return "observation:" + digest([source["id"], source["sha256"], source["retrievedAt"]])
