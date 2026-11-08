# Geographic overlap method

Boundary intersections describe geographic relationships. They do not establish
shared residents, registered voters, legislative authority, or an officeholder's
current constituency unless the corresponding population, legal, or roster
evidence is also linked.

## Official boundary inputs

The Census Bureau's [TIGERweb Legislative service](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer)
publishes several legislative vintages side by side. The relevant BAS 2026 layers
are [119th Congressional Districts, layer 4](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/4),
[2024 State Legislative Districts—Upper, layer 5](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/5),
and [2024 State Legislative Districts—Lower, layer 6](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/6).
Their metadata describes a January 1, 2026 geographic vintage. That date is
distinct from the congressional session or state legislative district plan.
The 120th Congress and 2026 state legislative layers are separate plans; a newer
plan must not silently replace the plan associated with an earlier roster.

State and county polygons come from the same publisher's
[State/County service](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer).
County equivalents remain Census geographic entities; their presence does not
establish a county government or supervisory district.

Every analytical collection must retain its complete source query, retrieval
timestamp, response checksum, source identifiers, metadata reference, geographic
vintage, and plan label. Reject truncated responses, duplicate identifiers,
missing geometry, or an unexpected layer description. Query analytical geometry
without server generalization or coordinate rounding. Independently simplified
polygons can introduce artificial gaps and intersections.

`tools/district_sources.py` fetches all six analytical layers separately by
state, orders paginated features by `OBJECTID`, checks an independent feature
count, and rejects duplicate identifiers. All 50 states are required; Nebraska
has no lower-chamber layer. Census pseudo-districts such as `ZZZ` remain in the
geometry and area calculations as unassigned areas, but are excluded from
officeholder matching.

Display geometry must be distinguished from analytical geometry. Census
[cartographic boundary files](https://www.census.gov/programs-surveys/geography/technical-documentation/naming-convention/cartographic-boundary-file.html)
are generalized and may omit small parts and offshore areas. Census explicitly
excludes area calculations, address geocoding, and precise geographic
relationships from their appropriate uses. A generalization tolerance expressed
in degrees also does not represent a constant distance throughout the country.

## Area intersections

For two polygonal entities A and B, compute the polygonal intersection and its
area in square metres in an equal-area coordinate reference system. Longitude
and latitude degrees, and Web Mercator square metres, are unsuitable area units
for this calculation. The output records the actual projection and software
versions so that a consumer can reproduce the result. Alaska's antimeridian
geometry requires explicit handling or a suitable Alaska projection; it must not
be interpreted as a polygon crossing almost the entire world.

`tools/overlaps.py` transforms vertices from EPSG:4326 with
`pyproj.Transformer(..., always_xy=True)` and performs planar GEOS intersections.
The WGS84 equal-area projections used are:

| States | Projection | Parameters |
| --- | --- | --- |
| Contiguous 48 | Albers Equal Area | `lat_1=29.5 lat_2=45.5 lat_0=23 lon_0=-96` |
| Alaska | Albers Equal Area | `lat_1=55 lat_2=65 lat_0=50 lon_0=-154` |
| Hawaii | Lambert Azimuthal Equal Area | `lat_0=20 lon_0=-157` |

Each result includes the complete PROJ definition, WKT, axis-order setting, and
installed Shapely, GEOS, pyproj, and PROJ versions. Intersections use the
straight segments connecting transformed vertices, without geodesic edge
densification. These are reproducible planar area measurements of supplied
geometry, not legally exact boundary determinations. Alaska has a dedicated
projection and an antimeridian regression test.

The two useful ratios have different denominators:

```
shareOfA = area(A intersect B) / area(A)
shareOfB = area(A intersect B) / area(B)
```

Both fractions concern the supplied polygon area. TIGER polygons can include
water: these are **total polygon area shares**, not land shares or population
shares. Source AREALAND and AREAWATER attributes cannot determine the land area
of an arbitrary intersection. Computing land-only intersections requires a
separate documented land mask with compatible vintage and geometry.

Boundary-only contact has zero polygon area and is not an area-overlap row.
Any positive-area threshold, rounding, topology repair, or omitted numerical
sliver must be documented and counted. A small positive intersection may be
numerical or source-boundary noise; it is not evidence that an address or a
resident falls in both jurisdictions.

The implementation emits every strictly positive cross-layer area, with no
minimum-area filter, snapping, or coordinate rounding. It emits one row per
unordered feature pair; reversing the pair exchanges the two shares. A row's
`geometryRepaired` flag identifies whether either analytical input required
repair after projection. This permits a consumer to separate repaired inputs
and small slivers instead of silently dropping them.

## Geometry repairs and overlapping districts

Original acquired geometry is preserved in the published analytical GeoJSON
files. If a projected polygon is invalid, the calculation explicitly applies
GEOS `make_valid` using linework, retains its polygonal components, and rejects
an empty or still-invalid result. It records the original coordinate checksum,
projected WKB checksums before and after repair, GEOS validity reason, method,
and areas before and after repair in `geometryRepairs`. Area fields for invalid
input do not constitute an independent accuracy bound. Analytical repairs do
not overwrite the source polygons.

New Hampshire House floterial districts are a separate derived layer,
`sldl_floterial`. `tools/geography_exceptions.py` unions component polygons
explicitly enumerated by the
[Census New Hampshire floterial crosswalk](https://www2.census.gov/programs-surveys/decennial/rdo/mapping-files/2023/2022-state-legislative-bef/NH_Floterial_2022.csv).
It checks component codes and published names against the acquired Census layer,
requires valid inputs and a valid union, and records component keys and sources.
The union introduces no simplification or geometry repair. Derived boundaries
have explicit `boundaryId` values; no synthetic Census GEOID is assigned.
Floterial areas are overlapping representation units and must not be interpreted
as an additional disjoint statewide partition.

## Quality checks

- Require finite coordinates, polygonal geometry, nonempty positive areas, and
  unique state-scoped identifiers. Fail on invalid geometry unless a documented
  repair is explicitly recorded; do not silently buffer polygons into validity.
- Match only entities within the same state. Preserve Census identifiers,
  alphanumeric district codes, and the district plan version.
- Check that intersection area is nonnegative and does not exceed either input
  area beyond the stated numerical tolerance. Reversing A and B must preserve
  the area and exchange the two shares.
- Test containment, disjoint polygons, shared edges, holes, multipart polygons,
  and antimeridian handling. A hole must not become covered area.
- For a pair of layers intended to partition the same state, report coverage
  residuals and duplicated area. Sums should approach one within the published
  tolerance. Excluded unassigned/water features can leave real residuals and
  must remain explicit rather than being renormalized away.
- Do not infer a missing chamber or a vacant seat from a missing polygon or an
  unmatched person. Nebraska's unicameral legislature and multi-member districts
  require explicit matching rules.

The implementation requires one official state polygon and matches its
`STUSAB` and FIPS code to the requested state before calculation. Every feature
must belong to that state and carry explicit un-generalized layer provenance.
Intersection shares may exceed one only within a numerical bound of `1e-8`;
larger values fail the calculation.

`coverageResiduals` reports any per-feature sum of cross-layer areas differing
from that feature's area by more than `1e-6` relative. It records the target
layer, summed area, signed residual, ratio, and over-/under-coverage status.
`sameLayerIntersections` separately reports same-layer positive intersections
larger than `1e-6` of the smaller polygon's area. These are diagnostics, not
automatic declarations of source error or proof of full coverage. Some layers
overlap by design. No residual is redistributed or renormalized.

## Files and reproduction

Install Python 3.12 or newer and the pinned analytical dependencies:

```sh
python3 -m venv .venv-geo
.venv-geo/bin/python -m pip install -r requirements-geo.txt
.venv-geo/bin/python -m unittest discover -s tools -p 'test_*.py'
.venv-geo/bin/python tools/build.py --offline
.venv-geo/bin/python tools/build.py --verify
```

The tested dependency pins are Shapely 2.2.0, pyproj 3.8.0, and NumPy 2.5.4.
The offline build requires the checksum-verified raw source cache, including
explicit browser observations for sources collected through a browser. It
preserves the original observation times. For live acquisition with recently
imported browser evidence, use `tools/build.py --browser-snapshots --fresh`;
the 24-hour source-age gate concerns observation, not publication currency.

`tools/geography.py` writes these artifacts inside `data/`:

| Path | Contents |
| --- | --- |
| `geography/regions/<state>/<layer>.geojson.gz` | State-scoped analytical polygons; layers `state`, `county`, `cd`, `sldu`, `sldl`, `cd120`, plus NH `sldl_floterial` |
| `geography/index.json` | Layer metadata, source IDs, per-state paths and counts |
| `overlaps/<state>.json` | Areas, pairwise shares, projections, input references, repairs and diagnostics |
| `overlaps/<state>.csv` | Flat positive-area intersection rows |
| `district-links.json` | Exact district-label joins and explicit unmatched records |
| `geography-report.json` | National counts, linkage summary and state diagnostics |

State directory and file names use lowercase USPS abbreviations. GZip is
lossless compression with a deterministic header timestamp; it changes neither
coordinates nor properties. The smaller national `geography/states.geojson`
and `geography/counties.geojson` remain generalized display products and are
not analytical inputs.

`tools/verify_geography.py`, invoked by `tools/build.py --verify`, checks
state coverage, source references, analytical provenance, unique boundary IDs,
positive finite areas, both share denominators, JSON/CSV agreement, residual
arithmetic, and official-to-boundary links. It does not independently re-fetch
sources or recompute every intersection. The overlap unit tests exercise
denominators, touching boundaries, holes, partition conservation, reversed
pairs, invalid-input repair, mixed-state rejection, generalized-input rejection,
and Alaska antimeridian behavior.

## Population is a separate product

The Census Bureau notes that [TIGER/Line geometry does not itself include
demographic data](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html).
Population overlap requires an independently cited population dataset and a
documented geographic crosswalk. Assigning a whole 2020 Census block's population
to a later district using its interior point assumes that the block is not split
by that district plan. It is an allocation method, not an exact observation of
the population inside every intersection, and it represents 2020 counts rather
than current residents. Area fractions must never be substituted for resident
fractions without an explicit estimation model.
