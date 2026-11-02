# Census legislative district polygons

`tools/district_sources.py` collects polygon geometry directly from the U.S.
Census Bureau [TIGERweb legislative service](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer).
It also acquires original [state and county polygons](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer) from layers 0 and 1. No third-party boundary files or earlier published polygons are collection inputs.

| Output key | Census layer | Layer cycle | Geographic vintage |
| --- | --- | --- | --- |
| `state` | [State_County 0](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/0) | State boundaries | January 1, 2026 |
| `county` | [State_County 1](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1) | County boundaries | January 1, 2026 |
| `cd` | [4](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/4) | 119th Congress | January 1, 2026 |
| `sldu` | [5](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/5) | 2024 upper-chamber districts | January 1, 2026 |
| `sldl` | [6](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/6) | 2024 lower-chamber districts | January 1, 2026 |

## Acquisition and verification

The public builder supplies its `fetch` function to
`district_sources.collect(fetch, offline=False)`. The return value is a pair:
`({'state': FeatureCollection, 'county': FeatureCollection, 'cd': FeatureCollection, 'sldu': FeatureCollection, 'sldl': FeatureCollection}, sources)`.
`district_sources.iter_collect(fetch, offline=False)` yields one
`(layerKey, FeatureCollection, layerSources)` tuple at a time and is preferred
for national builds. Write each layer as per-state files and release the
collection before acquiring the next: original national polygons can exceed
Git hosting file limits and require substantial memory.
Python 3.9+ and curl are sufficient for acquisition. The builder's snapshot cache
retains response bytes, SHA-256 hashes, observation times, and exact request URLs.
Offline replay retains those times and hashes.

For each layer, the collector checks metadata, obtains an independent feature count
for each of the 50 state FIPS codes, then downloads pages of 100 features ordered
by `OBJECTID`. Up to four state requests run concurrently; state-sized queries
avoid the service gateway rejecting large national geometry requests. Queries explicitly list every non-geometry metadata field and use `outSR=4326`,
`resultOffset`, `resultRecordCount`, and `f=geojson`. They request no
`maxAllowableOffset`, `geometryPrecision`, or quantization. The output is therefore
unsimplified geometry as returned by Census, in longitude/latitude coordinates.
It remains Census's geographic representation, not a survey or legal boundary
adjudication.

Every feature preserves Census properties, including `GEOID`, `STATE`, the
layer-specific district code (`CD119`, `SLDU`, or `SLDL`), and `OBJECTID`.
`sourceId` links to the exact response in the collection's `sources` array.
Layer metadata and count responses are also referenced. `districtKind` is a
classification described below; it is not an additional Census source field.

Checks reject changed layer names/vintages, missing identifiers or polygons,
short pages, unexpected transfer limits, duplicate district/object identifiers,
count mismatches, and unexpected state coverage. Nebraska has upper/unicameral
polygons and no lower-chamber layer records. Collection fails rather than
fabricating a lower chamber.

Run focused checks with:

```sh
python3 -m unittest discover -s tools -p test_district_sources.py
```

## Non-seat areas and joins

Census codes `ZZ` and `ZZZ` identify unassigned areas; these are retained and
labeled `districtKind: unassigned-area`, not linked to legislators.
Other functional-status codes are preserved without inferring a governing body.
The default legislative classification is `district`; state and county features
receive no `districtKind` property. See the [Census functional-status definition](https://www.census.gov/library/reference/code-lists/functional-status-codes.html) when interpreting raw `FUNCSTAT` values. Alphanumeric and named Census codes
are preserved verbatim. A district can have multiple representatives. Neither a
missing roster row nor a missing geometry join establishes a vacancy.

The layer cycle and geographic vintage are separate from a person's term.
119th-Congress geometry must not be joined to the 120th Congress. The service's
120th-Congress and 2026 state-legislative layers are deliberately excluded from
this collection. For state legislative districts, Census's 2024 plan label is
preserved; matching a current roster requires verifying the relevant chamber's
plan and resolving named-district identifiers. A new retrieval does not prove
that a court order, mid-cycle redistricting, or forthcoming election map already
applies to current officeholders.

These polygons support reproducible geometric intersections. Geometric area
fractions are not population, voter, household, ZIP-code, or address coverage.
Any derived intersection must cite input geometries, state the area projection
and repair/tolerance rules, and avoid presenting boundary-touching or tiny
rounding slivers as substantive overlaps without an explicit rule.
