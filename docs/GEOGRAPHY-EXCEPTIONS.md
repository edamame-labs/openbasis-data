# Official district exceptions

`tools/geography_exceptions.py` handles two distinctions that a generic roster-to-Census label join cannot resolve. All additional evidence is directly published by government. These transformations do not use names, locations, or district numbers from third-party directories.

## North Dakota House subdistricts

Source: North Dakota Legislative Assembly, [69th Assembly, September 2026 special session, members by district](https://ndlegis.gov/assembly/69-2025/special-2/members/members-by-district).

The same session's paginated member list labels both House members as district `4`. Its district directory gives the more specific, explicit labels:

| Official member | Published House district |
| --- | --- |
| Clayton Fegley | 4B |
| Lisa Finley-DeVille | 4A |

The parser reads each `li.member-item`, its `.member-name`, `.member-chamber`, `.district`, and official biography URL. The current directory must contain 141 distinct member profile URLs. A changed count requires review rather than silently treating the response as complete.

`apply_roster` copies input records. It modifies only North Dakota state House records whose original district label is `4`. It requires an exact name **and** official biography URL match to one current-session Representative record. The replacement must be a literal government-published `4A` or `4B`. It appends the district directory's complete source reference, preserves the original roster reference, and records the district field's source and transformation in `fieldEvidence`. Unrecognized identities or unexpected labels stop the build. U.S. House, state Senate, and all other records are unaffected.

## New Hampshire overlapping House districts

Source: U.S. Census Bureau, [2022 State Legislative Block Equivalency Files](https://www.census.gov/geographies/mapping-files/2023/dec/rdo/2022-state-legislative-bef.html), which directly links [NH_Floterial_2022.csv](https://www2.census.gov/programs-surveys/decennial/rdo/mapping-files/2023/2022-state-legislative-bef/NH_Floterial_2022.csv).

The Census explanation establishes that floterial districts overlay two or more component House districts. The ordinary Census House polygon layer depicts the components. The official CSV contains 39 floterial codes and 109 component relationships, with these literal headers:

```text
Floterial District,Component Census SLDL Code,Component Census SLDL Name
BE8,3,State House District Belknap 03
BE8,4,State House District Belknap 04
```

`floterials(base_fc, data)` requires the current-cycle Census New Hampshire lower-chamber polygons as its geometry input. For every CSV relationship it:

1. Pads the component Census code to three characters and matches `STATE=33`, `SLDL`, and the corresponding `GEOID`.
2. Requires the CSV component name to equal the Census feature's `NAME` exactly. Duplicate relations, missing codes, and name conflicts stop the build.
3. Requires at least two unique component districts for each floterial. The full county label is read from the official component names; all components must agree. The floterial number is read from the official floterial code. Thus `BE8` with Belknap components yields the displayed label `Belknap 8`, without assuming a county abbreviation crosswalk.
4. Validates every input polygon and runs Shapely `unary_union` on the enumerated component polygons. Invalid inputs stop the build. It does not repair geometry, simplify coordinates, create convex hulls, or fill gaps.
5. Validates that the resulting nonempty geometry is a Polygon or MultiPolygon. Disconnected units remain multipart.

The output is a separate `sldl_floterial` FeatureCollection. Its identifiers are explicitly different from Census GEOIDs:

```json
{
  "STATE": "33",
  "boundaryId": "33-floterial-BE8",
  "BASENAME": "Belknap 8",
  "NAME": "State House Floterial District Belknap 8",
  "NH_FLT": "BE8",
  "districtKind": "floterial",
  "sourceId": "nh-floterial-components",
  "componentKeys": ["sldl:33003", "sldl:33004"],
  "componentSourceIds": ["source IDs of the actual component polygon responses"],
  "derivation": "Shapely unary_union of enumerated official component polygons"
}
```

`boundaryId` is an application identifier containing the official floterial code. It must not be represented as a Census-assigned GEOID. The collection's `sourceIds` includes the CSV and every component response used. The layer declares `derived=true`, the 2022 New Hampshire House plan, `generalization="none requested"`, and copies the input component layer's metadata. Retrieval timestamps, checksums, and exact response URLs remain in the source registry.

This is a derived geometry based on an official component relationship, rather than a polygon directly supplied by Census. Applicability of the 2022 relationship to the selected current-cycle components is checked by exact code and name equality; this check does not independently establish legal boundary accuracy. The collector must retain and validate the component layer's geographic vintage and current legislative period.

Floterial units intentionally overlap ordinary House districts. Combined House and floterial units are **not a disjoint partition**: areas must not be summed across both layers as though every location belonged to exactly one House representation unit.

## APIs and validation

- `collect(fetch, offline=False) -> (data, sources)` uses the normal evidence-snapshot fetcher. Offline replay preserves the saved observation's timestamp and checksum. `data` contains `ndDistricts`, `nhComponents`, and full `sources`.
- `apply_roster(officials, data) -> new_records` preserves record IDs and all unrelated fields.
- `floterials(base_fc, data) -> derived_feature_collection` uses the pinned Shapely runtime from `requirements-geo.txt`.

Run `.venv-geo/bin/python -m unittest discover -s tools -p test_geography_exceptions.py -v`. Tests cover exact identity matching, field references, primary HTML extraction, input immutability, component source propagation, missing codes, conflicting names, duplicate relations, invalid geometry rejection, and disconnected multipart output.
