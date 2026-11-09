# Roster-to-boundary links

`tools/district_links.py` joins official roster records to government-published geographic identifiers. It does not derive district boundaries from people, addresses, ZIP codes, or county names. The function is pure: `link(officials, collections)` returns a JSON-serializable object without changing either input.

## Inputs and output

The roster input is an array of records, or an object containing `officials`. Geographic collections are GeoJSON FeatureCollections keyed by:

| Key | Official geometry | Identifier |
| --- | --- | --- |
| `states` | State boundaries; `STUSAB` supplies the USPS/FIPS crosswalk | `GEOID` |
| `cd` | 119th Congressional Districts | `STATE`, `CD119`, `GEOID` |
| `sldu` | 2024 state legislative districts, upper chamber | `STATE`, `SLDU`, `BASENAME`, `GEOID` |
| `sldl` | 2024 state legislative districts, lower chamber | `STATE`, `SLDL`, `BASENAME`, `GEOID` |
| `sldl_floterial` | Derived New Hampshire House floterial polygons using the official Census component crosswalk | `STATE`, `NH_FLT`, `BASENAME`, `boundaryId` |

Each collection carries `source` or `sources` references. The collector is responsible for validating geographic vintage and source currency before invoking the join. The join additionally rejects congressional features labeled `CD120`. The join ignores the published `cd120` layer, and verification fails if any match uses it. A retrieval date alone does not establish that a boundary applies to a particular election or legislative session.

Each match preserves `officialId`, the original roster district label, state, layer, `boundaryId`, and `districtKey`. Direct Census geometry retains its actual `GEOID`, with `districtKey=layer:GEOID`. Derived NH floterial geometry uses `districtKey=sldl_floterial:boundaryId` and `GEOID=null`; its application boundary identifier is not represented as a Census GEOID. Whole-state Senate joins use the output layer and key prefix `state`, while the input collection key is `states`. `sourceIds` references the roster inputs; `geometrySourceIds` references the polygon publication; `stateCrosswalkSourceIds` references the state-code crosswalk. `matchingRule` describes the join. The Census label remains in `geometryDistrictLabel` for comparison.

Unmatched rows preserve identity and input references and give an explicit reason. Missing geometry is not classified as a vacancy. Several officeholders can correctly reference one polygon, including multi-member state districts and both U.S. senators.

## Exact matching rules

State and chamber scope are mandatory: identical district numbers in different states or chambers never join. Nebraska's unicameral legislature uses the upper-chamber Census collection. U.S. senators join their whole state, explicitly distinguished from legislative district polygons. U.S. House districts join the `CD119` numeric code; official roster district `0` matches Census `00` for at-large seats.

State legislators join Census `BASENAME`. Formatting normalization is limited to Unicode NFKC, letter case, whitespace, and leading numeric zeroes. Examples: `Strafford 4` equals `Strafford 04`; `7A` equals `07A`; Maryland `37B` remains distinct from `37A`. Alaska Senate `A` matches Census literal `A` (`SLDU=00A`); letters are never converted to ordinal numbers.

Vermont Senate roster labels omit the trailing generic word `District` when matching a Census basename. Nine literal naming correspondences are enumerated in `LABEL_ALIASES`, rather than applying approximate matching:

| Official roster label | Census `BASENAME` |
| --- | --- |
| MA House: Barnstable, Dukes and Nantucket | Barnstable-Dukes-Nantucket |
| MA Senate: Berkshire, Hampden, Franklin and Hampshire | Berkshire-Hampden-Franklin-Hampshire |
| MA Senate: Hampden, Hampshire and Worcester | Hampden-Hampshire-Worcester |
| MA Senate: Hampshire, Franklin and Worcester | Hampshire-Franklin-Worcester |
| MA Senate: Norfolk, Plymouth and Bristol | Norfolk-Plymouth-Bristol |
| MA Senate: Norfolk, Worcester and Middlesex | Norfolk-Worcester-Middlesex |
| VT Senate: Chittenden-Central District | Chittenden Central |
| VT Senate: Chittenden-North District | Chittenden North |
| VT Senate: Chittenden-Southeast District | Chittenden South East |

These correspondences compare the names in the official [Massachusetts House roster](https://malegislature.gov/Legislators/Members/House), [Massachusetts Senate roster](https://malegislature.gov/Legislators/Members/Senate), and [Vermont Senate roster](https://legislature.vermont.gov/people/loadAll/2026/Senate) with the [Census upper-chamber layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/5) and [Census lower-chamber layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/6). The label join performs no geographic union, district renumbering, or edit-distance matching. The separate NH floterial derivation is described below. Both publications remain referenced by each resulting record.

Ambiguous canonical labels remain unmatched. Duplicate GEOIDs within a layer cause a failure. Unrecognized offices, absent district labels, unavailable layers, and missing state crosswalk entries have separate unmatched reasons.

## Additional primary evidence and unresolved inputs

Kentucky's official county/district roster displays the actual district number separately from the internal member profile query parameter. The source parser reads that displayed number. The join never subtracts a numerical offset from an internal identifier.

The current North Dakota House roster's broad district `4` label is refined to the government-published `4A` or `4B` using the same current session's official directory by district. The transformation requires an exact member name and biography URL match, preserves both publications, and records the district field's evidence. The join subsequently matches the published subdistrict label directly to Census.

New Hampshire floterial districts are overlapping representation units made up of component House districts. Their polygons are derived separately by unioning the exact components enumerated in the official Census floterial CSV. The derivation validates component codes and full names against the current-cycle polygons and preserves each component geometry response reference. It fails on missing or conflicting inputs and does not repair invalid geometry. See [GEOGRAPHY-EXCEPTIONS.md](GEOGRAPHY-EXCEPTIONS.md) for the direct official sources, transformations, and provenance schema.

For an NH House record, the join first checks the ordinary `sldl` index. If that index has no matching label, it checks `sldl_floterial` for the exact canonical full district name. Successful supplemental matches explicitly report `layer=sldl_floterial`, retain the derived `boundaryId`, leave `GEOID` null, and reference the official component crosswalk and the precise component polygon responses. Several members can share the same derived polygon. These supplemental units must not be treated as a disjoint partition alongside ordinary House districts.

Unsupported district labels, missing supplemental evidence, and ambiguous inputs remain unmatched. Missing rows do not establish vacancies. The join establishes a documented identifier relationship; it does not establish legal boundary accuracy, address eligibility, or a population overlap percentage. Those require separately documented geometry, time alignment, and spatial calculations.

## Validation

Run `python3 -m unittest discover -s tools -p test_district_links.py -v`. Tests cover state/chamber collisions, multi-member districts, source references, input immutability, alphabetical and named districts, Maryland subdistricts, at-large representatives, statewide senators, unresolved district labels, successful NH floterial matches without fabricated Census GEOIDs, ambiguous labels, duplicate IDs, and rejection of future congressional fields.
