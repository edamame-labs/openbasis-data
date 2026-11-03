# OpenBasis Data

Primary government data for U.S. federal, state, and county jurisdictions. Schema version 2 replaces the former aggregated directory and district-overlap dataset.

## Included snapshot

Counts below describe source observations from November 2–3, 2026 (UTC). `data/coverage.json` is the authority for subsequent refreshes.

| Dataset | Coverage | Direct publisher |
| --- | --- | --- |
| U.S. House members | 433 records, 50 states | [House Clerk XML](https://clerk.house.gov/xml/lists/MemberData.xml) |
| U.S. senators | 100 records, 50 states | [Senate XML](https://www.senate.gov/general/contact_information/senators_cfm.xml) |
| State legislators | 7,321 people across all 50 states and 99 chambers | Direct official legislative websites; see [regional source notes](#state-source-notes) |
| Congressional and state legislative boundaries | Original Census polygons for all 50 states; Nebraska has no lower chamber | [Census Legislative service](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer) |
| State geography | 50 states | [Census TIGERweb](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer) |
| County and county-equivalent geography | 3,143 areas within the 50 states | Same Census service |

Counts describe the checked-in snapshot, not a guarantee that every occupied office is present. State executive officers and county officeholders are **not collected**. All state legislative chambers have a directly collected official roster; Nebraska has one unicameral chamber. `collected` means source extraction completed, not that a statutory seat shortfall is a verified vacancy. DC and territories are outside this release. County equivalents include entities such as independent cities and statistical areas; their inclusion does not establish a county government or supervisor district.

The current geography vintage is **January 1, 2026**, as reported in Census layer metadata. Source publication dates differ from retrieval dates: the House XML reports **October 1, 2026**. Sources without a publication date have `publishedAt: null`. A recently fetched page may still contain older information.

## Files and evidence

- `data/officials.json`: 7,854 source-backed records, with name, office/body, jurisdiction, state, and source-reported party/district/profile link where available.
- `data/officials.csv`: the same records, with provenance encoded as JSON in `sources`.
- `data/sources.json`: direct URLs, final URLs, publishers, retrieval timestamps, SHA-256 checksums of the acquired representation, and reported publication/session metadata. `representation` distinguishes HTTP response bodies from browser DOM captures; POST sources include their request method and body.
- `data/geography/{states,counties}.geojson`: Census features, source identifiers and names, with collection-level query URL, checksum, metadata reference and vintage.
- `data/coverage.json`: collected rosters, analytical boundary counts and explicitly uncollected offices by state.
- `data/geography/regions/<state>/<layer>.geojson.gz`: original analytical polygons, losslessly compressed. Layers are `state`, `county`, `cd` (119th Congress), `sldu`, `sldl`; NH additionally has a clearly labeled derived `sldl_floterial` layer.
- `data/geography/index.json`: per-state layer files, source IDs, plan labels and geometry linkage summary.
- `data/district-links.json`: explicit person-to-boundary joins with roster and geometry references. Multiple people can share a boundary; U.S. senators link to their state.
- `data/overlaps/<state>.{json,csv}`: positive-area cross-layer intersections, both input areas, both directional shares and geometry diagnostics. These are polygon areas, not residents or voters.
- `data/geography-report.json`: input counts, plan/vintage metadata, repairs, coverage residuals and linkage diagnostics.
- `data/manifest.json`: SHA-256 checksums for every other published data file. This detects accidental changes; it is not a digital signature or independent verification.

The top-level `geography/states.geojson` and `counties.geojson` are generalized display files. They are **not** used for analytical intersections. The per-state `.geojson.gz` files preserve the original Census coordinates without requested generalization or rounding; compression changes no coordinates. All geographic coordinates use EPSG:4326.

Analytical overlaps use original polygons projected into documented equal-area coordinate systems, with separate Alaska and Hawaii definitions. They include water wherever it is part of the source polygon. They do not measure shared population, registered voters, or land-only area. Unassigned areas, repairs and coverage differences remain visible; missing coverage is never renormalized away. See [the method](docs/OVERLAP-METHOD.md), [source acquisition](docs/DISTRICT-SOURCES.md), [joins](docs/DISTRICT-LINKS.md) and [special districts](docs/GEOGRAPHY-EXCEPTIONS.md).

The 119th Congress and Census 2024 state legislative plans are retained separately from future 120th Congress/2026 election plans. A matching label alone is not an independent legal determination of a map's applicability. No address database or ZIP-code layer is included.

## Build and verify

Full acquisition and analytical rebuilding requires Python 3.12+, curl, and `requirements-geo.txt`. Offline integrity verification can use Python 3.9+. No private application repository or user account is required. Some official sites require a normal browser to render their public directory; those source snapshots must be captured before replay, as documented below.

```sh
python3.12 -m venv .venv-geo
.venv-geo/bin/python -m pip install -r requirements-geo.txt
.venv-geo/bin/python -B tools/build.py --browser-snapshots
python3 -B tools/build.py --verify --fresh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_*.py'
```

The builder reads **only its explicit government source allowlist**, starts from those acquired responses, and replaces `data/` only after all fetches and checks succeed. It never reads a previous directory, third-party roster, manual correction seed, or legacy contact file. A failed source stops the build; the prior published snapshot remains intact with its original timestamps.

For the checked-in nationwide release, acquire HTTP sources and the required live browser DOM snapshots, then run `--browser-snapshots` to use those fresh observations while fetching the HTTP sources live. Use `--offline` to replay all exact observations. A missing or invalid source stops the build. Online fetching never substitutes browser challenge pages or a prior directory for a required live observation. See [browser acquisition instructions](docs/region-d.md#reproducing-browser-evidence).

`--fresh` requires every source and Census metadata response to have been retrieved within 24 hours. This is a retrieval-age check, not a claim that publishers updated the information within 24 hours. It must be run before publication.

Acquired source bytes and observation metadata are cached locally in ignored `.source-cache/`. To reproduce extraction from those exact checksum-verified HTTP responses and browser DOM observations:

```sh
.venv-geo/bin/python -B tools/build.py --offline
```

For comparison against a pinned release, first check out its Git commit. Fresh downloads can differ from the release because official endpoints change. Preserve `.source-cache/` separately when an exact historical source snapshot is needed; URLs and checksums alone cannot restore an overwritten official page. Offline generation retains original source retrieval timestamps.

## Extraction rules

- House identity uses the official Bioguide ID and `official-name`; Senate identity uses its XML Bioguide ID and first/last name fields. Only the 50 state postal codes are included. The House parser requires Congress 119 and stops for review when the congress changes.
- California records come from chamber roster cards. Assembly `Family, Given` names are reordered without enriching names. Explicitly labeled vacant cards are excluded.
- North Carolina records come from the official 2025–2026 session member tables. Explicit `Resigned` or `Deceased` entries are excluded; biography anchor text supplies the name. District duplicates or a changed session label stop the build.
- State record IDs identify source-specific roster entries, not permanent cross-release person identities. Multi-member districts use distinct source-person identifiers; CA/NC use chamber/district row IDs. Party labels preserve publisher wording and can differ between chambers.
- Display names decode HTML entities, collapse repeated whitespace, remove the enumerated trailing academic/professional credentials in `person_name`, and normalize trailing lowercase `ll`/`lll` to Roman `II`/`III`. These are documented text transformations; source checksums refer to the original acquired representation. Leading initials remain part of the name. Explicit vacancy placeholders are excluded rather than published as people.
- No missing member is automatically labeled a vacancy. No email addresses, telephone numbers, inferred contact routes, or third-party identifiers are added.
- Adapters for the other 48 states are in `tools/regions/`. Their source-specific eligibility rules, session checks, pagination and multi-seat handling are documented below. Party and name fields are not enriched from other directories.
- Geographic state codes, county codes, names, GEOIDs and geometry come directly from Census. Territories and DC are filtered out using Census state postal codes. Duplicate GEOIDs or a truncated server response stop the build.

### State source notes

- [AL, AK, AZ, AR, CO, CT, DE, FL, GA, HI, ID, IL, IN, IA, KS, KY](docs/region-a.md)
- [LA, ME, MD, MA, MI, MN, MS, MO, MT, NE, NV, NH, NJ, NM, NY, ND](docs/region-b.md)
- [OK House, OR, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY](docs/region-c.md)
- [OH, OK Senate and PA, including browser evidence reproduction](docs/region-d.md)

Each note lists direct government endpoints, parsed counts and exclusions. `data/coverage.json` has per-state, per-chamber record counts and collection status. The exact supporting references for each person are in `sources`; records relying on a separate current-membership index include both references. For New Hampshire, the TSV's `Former` label is not treated as resignation: House membership is joined to the chamber's actual current roster.

These checks verify extraction, scope, provenance and file consistency. They do not constitute an independent factual check of every government assertion. Conflicts and unsupported fields must remain unpublished until resolved against a suitable primary source.

## Drawing shapes and inspecting an overlap

Lossless decompression produces ordinary GeoJSON that GIS software and map libraries can read:

```sh
gzip -dc data/geography/regions/ca/sldu.geojson.gz > /tmp/ca-state-senate.geojson
```

To export the actual intersection polygon for two published boundaries:

```sh
.venv-geo/bin/python -B tools/overlap_shape.py --state CA \
  --a county:06013 --b sldu:06009 --output /tmp/contra-costa-senate-9.geojson
```

The exported GeoJSON records its source IDs, projection and area measure. An overlap table row can also be reproduced from the cited original layer files. Boundary IDs combine the layer with its Census GEOID; derived NH floterials use an explicit `boundaryId` instead of inventing a Census GEOID.

## Scope and compatibility

Secondary aggregators and city/town rosters are excluded. Prior contact enrichment, manual overrides, vacancy reviews and population-overlap products are removed rather than carried forward without current evidence. Analytical geometry is freshly acquired from government publishers; previous computed geometry and population products are not reused. Git history retains older releases; it is not a current source.

Schema 2 removes `data/states/`, contact/vacancy review files and enrichment fields. Consumers of the earlier map/overlap schema need to migrate: `intersectionAreaM2` and area shares must never be read as the former population fields. See [AGENTS.md](AGENTS.md) for repository source and communication requirements.

## License

Repository contributions are provided under [CC0](LICENSE). Source links identify the original publishers; their marks and linked website materials are not relicensed by this repository. This project is not affiliated with the publishing agencies.
