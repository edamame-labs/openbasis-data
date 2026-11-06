# Separate media outcome master

`tools/temporal_media.py` assembles explicit media election calls into `temporal-data/media-results/results.json.gz`, a flat `results.csv`, and a SHA-256 `manifest.json`. Government results and certification records remain separate.

All 50 states' directly published AP metadata and progress feeds have been collected. The assembled snapshot has 6,262 distinct race rows: 435 House, 35 Senate and 36 governor races carried by NPR, plus 5,756 AP state legislative contests. There are 5,819 explicit candidate winner markers across 5,586 races, including 1,655 explicitly marked uncontested wins. Another 676 races have no winner marker. Twenty races have at least one called candidate while the separately observed publisher race status remains uncalled. The New Jersey publication has no legislative rows; missing rows do not establish that no election occurred.

Multiwinner contests retain every explicitly marked candidate in `winners`; `winner` is a convenience field populated only when exactly one candidate is marked. `called` means at least one candidate has a winner marker. `fullyCalled` preserves the separate AP race status, and `partially-called` distinguishes positive candidate calls in races without a complete race call. CSV exports one row per explicitly marked candidate, or one empty-candidate row for a contest without a winner marker. Named districts, separate House positions and 26 special elections retain their original publisher identifiers. Candidate calls do not establish vacancies or serving membership.

The main legislative table uses direct AP observations once. Duplicate partner representations do not add races or winners to its totals. Another 161 independent newsroom assertions from Texas Tribune, Wisconsin Public Radio, WHQR and Alabama Political Reporter remain standalone observations; they are not silently merged across publisher race identities or added to canonical candidate totals. The public distribution contains only the latest outcome snapshot. Historical and geographic work is outside this distribution.

The aggregator requires the observed NPR coverage of exactly 435 House races across 50 states, 35 Senate races and 36 governor races. Additional publisher races remain source scoped. It joins a designation to a race by exact publisher source, office, district and source contest identifier where supplied. It never joins by candidate name. Publishers without race identifiers retain null IDs and their original district/office labels. Article statements without districts remain separate; no district is guessed.

Each row carries the exact primary URL, response checksum, observation ID and actual acquisition time, plus context references. Call time is preserved only when provided; future machine-readable call times fail. Publisher literal times without an established timezone remain raw, while the machine-readable call time stays null. Acquisition errors, parser errors, missing evidence, conflicting observations and call/designation inconsistencies stop assembly. Official certification, legal service and current membership are never inferred.

```sh
# Default: deterministic offline replay of existing observations.
.venv-geo/bin/python tools/temporal_media.py

# Optional: include exact transferable evidence.
.venv-geo/bin/python tools/temporal_media.py --export-evidence /tmp/media-evidence.tar.gz

# Explicitly request fresh actual HTTP responses.
.venv-geo/bin/python tools/temporal_media.py --online
```

`MediaEvidenceStore` uses an explicit media catalog, separate from the official-source catalog. Shared storage artifacts require an exact publisher delegation; a hostname alone does not establish authority. The national bundle has 127 observations and 126 unique byte objects. Importing it into an empty cache and replaying produced an identical assembled result, with all original observation timestamps preserved. Repeated gzip JSON/CSV builds are deterministic; manifest hashes verify their bytes. Media HTTP acquisition uses an ordinary `Mozilla/5.0` User-Agent recorded in acquisition metadata, with no account credentials.

Parser-specific semantics and limits are documented in [MEDIA-AP.md](MEDIA-AP.md), [MEDIA-FEDERAL.md](MEDIA-FEDERAL.md), and the regional adapter notes. All 50 state publications have been checked, but publisher coverage is not an independently established census of every election or occupied seat. Pending results remain pending; no vote-ranking or chamber-control inference supplies a missing winner.

The manifest reports office-level called/uncalled counts and a histogram of positive publisher outcome types. Explicit uncontested-win narratives are counted separately. New publication requires all source observations to be no older than 24 hours; historical offline parsing remains available. The dataset ID hashes the entire assembled content, so corrected parser output changes its identity even when source bytes remain unchanged. Source-specific accessibility representations are retained without relabeling them as HTTP or complete DOM bodies.

The gzip JSON decompresses losslessly to the original source-referenced result object. The media collectors use the Python standard library and curl; no geographical runtime or map release is required. The plain-JSON variant is available with `--uncompressed-json`.
