# OpenBasis Data

Open data on U.S. elected officials, state by state, and on how their districts overlap. It covers members of Congress, state legislators, statewide executives, and selected city councils.

**Coverage: all 50 states.** Federal officials, state legislators, governors and available statewide executives are included nationwide. City coverage remains limited to San Francisco, Oakland and San Jose.

Each state has a quality record in [`data/coverage.json`](data/coverage.json). The national expansion passes automated checks; this does **not** mean every state has had a fresh manual roster review. California, Maryland, New Hampshire and Texas retain their historical review dates. Seat shortfalls remain unconfirmed until checked against the chamber's own roster.

Every record links back to the public source it came from, and the methodology below explains how the derived numbers (district overlaps) are computed. The data powers OpenBasis, and you're free to use it for anything else too (see [License](#license)).

## Files

| File | What it is |
|---|---|
| [`data/officials.json`](data/officials.json) | Every official, with contact info, cross-reference IDs, and the source of each record |
| [`data/officials.csv`](data/officials.csv) | A flat export of the main directory fields; includes `state`, `seat` and `voting` |
| [`data/seat-reviews.json`](data/seat-reviews.json) | Dated official-source vacancy checks, historical evidence and unresolved issues |
| `data/states/<st>/assignment-audit.json` | Exact Census point recovery audit for states rebuilt with that method |
| [`data/coverage.json`](data/coverage.json) | Per-state validation status, findings, unmatched officials, seat shortfalls, population differences and source versions |
| [`data/states/index.json`](data/states/index.json) | One summary row per state: population, block count, and district count per layer |
| `data/states/<st>/districts.json` | The state's district layers. Each district has its 2020 population and the districts in other layers it shares residents with |
| `data/states/<st>/overlaps.csv` | The state's overlaps as a flat table: one row per pair of districts |
| `data/states/<st>/boundaries/*.geojson` | Simplified district boundaries, one file per layer, meant for maps rather than analysis |
| [`seeds/<st>/*.yml`](seeds) | Hand-maintained rosters and temporary official-source corrections |

`<st>` is the lowercase postal code, for example `data/states/ca/districts.json`.

To use the data without cloning, read it straight from GitHub, e.g.
`https://raw.githubusercontent.com/edamame-labs/openbasis-data/main/data/officials.csv`.
To pin a version, put a commit SHA in place of `main`.

## Coverage

| Level | Officials | District boundaries |
|---|---|---|
| Federal | U.S. senators and representatives from each published state | Congressional districts (119th Congress, current), plus 2027 maps where a state redrew mid-decade |
| State | State legislators, governors and other statewide executives | Upper- and lower-chamber districts |
| City | Mayors and councils of San Francisco, Oakland, San Jose | Council districts |

DC and the territories aren't included.

## Sources

| Data | Source | How it's collected |
|---|---|---|
| Members of Congress | [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators) | JSON download |
| State legislators | [Open States](https://open.pluralpolicy.com/data/) bulk CSV, one per state | CSV download |
| State executives, mayors | [openstates/people](https://github.com/openstates/people) | YAML from GitHub |
| SF Board of Supervisors | [sf.gov](https://www.sf.gov/departments--board-supervisors) | Scraped from the board page and profiles |
| Oakland, San Jose councils | [oaklandca.gov](https://www.oaklandca.gov/Government/City-Council-Leadership/Council-Members), [sanjoseca.gov](https://www.sanjoseca.gov/your-government/departments-offices/mayor-and-city-council) | **By hand** in `seeds/ca/` (both sites return HTTP 403 to scripts) |
| Congressional and legislative boundaries | U.S. Census [TIGERweb](https://tigerweb.geo.census.gov/) (analysis) and [cartographic boundary files](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) (display) | ArcGIS REST / shapefile |
| 2027 congressional boundaries | U.S. Census TIGERweb "120th Congressional Districts" (January 1, 2026 vintage) | ArcGIS REST |
| City council boundaries | [DataSF](https://data.sfgov.org/d/f2zs-jevy), [Oakland GIS](https://services.arcgis.com/9tC74aDHuml0x5Yz/arcgis/rest/services/CouncilDistrict_2022_Revised/FeatureServer/0), [San Jose GIS](https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/120) | GeoJSON / ArcGIS REST |
| Population | 2020 Census blocks (P.L. 94-171 `POP100`) via TIGERweb | ArcGIS REST |

Each official carries a `sources` list with the URL and retrieval date of every record merged into it.

## Methodology

### Merging officials

When two sources describe the same person, records are matched on level + state + jurisdiction + body + canonical district + normalized name. Two people with the same name in different chambers or districts remain separate. Ambiguous conflicting Open States identities cause ingestion to fail rather than silently merge. Source-run IDs are reconciled with final record IDs after merging. Sources are applied in a fixed priority order: earlier ones win on conflicting fields, and later ones only fill gaps. For local offices, official city websites outrank Open States.

### When a source breaks

Websites go down, change their HTML, or serve bot challenges. Each source has a sanity check. Most check a minimum record count; the SF scraper must find exactly one supervisor for each of districts 1–11. When a source fails its check, its records from the previous run are **carried forward** rather than dropped, so nobody disappears from the dataset because a website was down. The failure is recorded in `runs` in `officials.json` (`error`, `carriedForward: true`), and carried-forward records keep their original `retrievedAt` dates.

### Matching officials to districts

District names differ between sources ("Coos 05" vs "Coos 5", "Third Middlesex" vs "3rd Middlesex", "Norfolk, Worcester and Middlesex" vs "Norfolk-Worcester-Middlesex"). Both sides are reduced to a canonical key: lowercase, ordinals as digits, leading zeros dropped, separators and "and" removed. Congressional at-large seats are district `0`. Multi-member districts (common in Arizona, Maryland, New Hampshire, Vermont and elsewhere) map to several officials.

### District overlaps

Overlap is measured in **people, not area**. For every populated 2020 Census block (about 5.8 million across the 50 states), the block's interior point is assigned to the district containing it in each layer. Two districts overlap by the total population of the blocks they share. Blocks never cross state lines, so each state is computed on its own.

- Legislative districts are drawn from whole Census blocks. If an interior point falls outside the generalized analysis polygons, the pipeline queries Census's exact server-side point intersection for that point. Only one unambiguous, known district is accepted; no nearest-district or proportional allocation is used. Rebuilt states publish `assignment-audit.json` with every recovered point, population and query URL. City council lines may occasionally split a block; in that case the whole block goes to the district containing its interior point.
- Pairs that share fewer than 100 people, or under 0.1% of the smaller district, are dropped as boundary noise.
- Sanity check: each state's congressional layer sums to its 2020 Census population, and every other statewide layer sums to the same total.

`share_of_district` in `overlaps.csv` answers "what fraction of this district's residents also live in the other one?" Each pair appears twice, once from each side.

### Boundaries

Overlaps are computed from TIGERweb geometry at about 10 m precision. The files under `boundaries/` are for display only: they come from Census cartographic boundary files, which are clipped to the shoreline. The 2027 congressional layer has no cartographic file yet, so its display boundaries are clipped to the 119th Congress outline instead. All layers are simplified with [mapshaper](https://github.com/mbloch/mapshaper) using topology-preserving simplification, so neighboring districts still share edges.

## Quality and review status

`data/coverage.json` is the machine-readable quality report for this snapshot:

- `collected`: collected data has unresolved automated errors. The publication gate rejects this status.
- `auto-validated`: automated checks passed. Warnings, including apparent vacancies, still require official-source review.
- `reviewed`: automated checks passed and a historical manual-review date exists. `reviewedAt` is that historical date, not a claim that the current snapshot was manually reviewed again.

Checks compare each state's House and legislative member counts to independent chamber-size references, require two U.S. senators and one governor, match officials to analysis districts, compare display and analysis district keys, and verify symmetric population overlaps. Every statewide layer is compared independently with the state's **2020 resident population**, rather than only with another computed layer. Every statewide layer must equal the independent Census total exactly; any difference fails. Unmatched geographic members over 10% fail unless an explicitly documented exception applies. Smaller mismatches remain visible as warnings.

The report includes `inputSha256`, a fingerprint of the exact officials, CSV, geometry and index files checked; changing any input requires a new report before publication.

Each layer's report lists unmatched officials and districts without matched officials. `seats[].confirmedVacancies` counts only applicable, dated official evidence; `seats[].unconfirmedShortfall` is the remaining count requiring investigation, **not** a confirmed vacancy count. Non-voting Maine tribal representatives are excluded from voting-seat totals and kept in the directory. Citywide council members are reported separately from ward-based members.

[`data/seat-reviews.json`](data/seat-reviews.json) records the evidence behind seat checks: explicit vacancy confirmations, historical confirmations, confirmed departures, unresolved conflicts, and resolved data errors. A departure notice alone is not automatically counted as a currently vacant seat. Each confirmation expires after its `validUntil` date and stops applying if the chamber roster fingerprint changes. District subjects and observed empty districts are not automatically confirmed vacancies. Historical NH Clerk figures remain historical evidence.

Temporary statewide corrections may be maintained in `seeds/<st>/*.yml` with an explicit `level`, stable member `id`, official source, verification date and `expiresAt`. They only fill an unoccupied seat and yield to an automatically collected successor. The current NM District 41 correction expires on December 1, 2026 unless reverified.

The report records official-data and geometry generation times separately, independent Census/NCSL reference URLs, geometry vintages and analysis endpoints. Congressional `cd120` reflects the Census January 1, 2026 vintage and may omit later changes. Display state-legislative boundaries use GENZ2024; mismatches with analysis boundaries fail validation.

## Known limitations

- **2027 congressional maps.** `cd` is the 119th Congress map that current members represent. `cd120`, present only for states whose lines changed, is the map used in the November 3, 2026 election (California's comes from Proposition 50), effective January 3, 2027. Its seats have no officials attached until the winners are seated.
- **New Hampshire floterial districts.** These are House districts layered on top of base districts. Census publishes no separate boundaries for them, so members elected from floterial districts aren't linked to a district shape.
- **Hand-maintained seeds.** The Oakland and San Jose rosters are hand-maintained, and each file records the date it was last checked against the city site.
- **SF in CI.** sf.gov blocks GitHub Actions, so the weekly refresh carries the SF supervisor roster forward. It is refreshed whenever the pipeline runs from an ordinary network.
- **Vacancies.** Empty seats appear as districts with no official.
- **Idaho House positions.** `district` is the shared geographic district; `seat` preserves the A/B position from the upstream district label. These are not separate geographic subdistricts.
- **Maine tribal representatives.** Non-voting representatives are included with `voting: false` and office `Non-voting Tribal Representative`. They represent tribal communities, have no Census legislative-district polygon, and do not count against the 151 voting seats.
- **Unconfirmed shortfalls.** The nationwide roster may contain fewer members than statutory seats. Consult `coverage.json` and the chamber's own current roster before interpreting a gap as a vacancy.
- **Boundary precision.** Generalized analysis geometry can miss block interior points. Exact Census point intersection resolves these cases, with a public audit trail; unresolved or ambiguous assignments block publication. Display GeoJSON remains simplified and should not be used for precision analysis.
- **Population vintage.** Population is from the 2020 Census, not current estimates.

## Corrections

Spotted something wrong? Open an issue or a pull request.

- **Hand-maintained rosters.** Edit `seeds/<st>/*.yml`, include the official source URL, and bump `verifiedAt`.
- **Automated sources.** Most errors there come from upstream (Open States, congress-legislators), and fixing them there helps everyone. Link the upstream fix in your issue.

## Updates

The data is refreshed weekly. A national quality gate runs before publication; a failed check prevents that refresh from replacing the published snapshot. A commit is made only when the data actually changes, so the git history doubles as a changelog of who held which office when. `runs` in `officials.json` records each source's result for the latest refresh.

## Schema

**`officials.json`**: `{ generatedAt, officials: Official[], runs }`. Each `Official` has:

| Field | Notes |
|---|---|
| `id` | Stable slug that includes the state, e.g. `us-house-ca-james-gallagher`, `md-house-of-delegates-aletheia-mccaskill` |
| `name`, `givenName`, `familyName` | |
| `level` | `federal`, `state`, or `local` |
| `state` | Two-letter postal code |
| `jurisdiction` | State name, or city for local offices |
| `office`, `body`, `district` | e.g. `Delegate`, `Maryland House of Delegates`, `44B`. Congressional at-large seats use district `0` |
| `party`, `gender` | When the source provides them |
| `seat` | Position within a shared district, e.g. Idaho House `A` / `B`; `district` remains the geographic district number |
| `voting` | `false` for Maine non-voting tribal representatives; otherwise omitted |
| `email`, `phone`, `address`, `website`, `contactForm`, `photo`, `socials` | Public office contact info |
| `termEnd` | ISO date, when known |
| `ids` | Cross-references: `bioguide`, `fec`, `opensecrets`, `wikidata`, `govtrack`, `openstates` |
| `sources` | `{ name, url, retrievedAt }` for every record merged into this one |

**`states/<st>/districts.json`**: `{ generatedAt, state, blocks, layers, districts }`. `districts` is keyed by `<layer>:<key>`, where `key` is the canonical district name (e.g. `sldl:44b`, `cd:0`). Each entry has `district` (display name), `pop` (2020 population), `bbox`, and `overlaps: { key, pop }[]` sorted largest first. Each layer's `body` matches `Official.body`, which links districts to the officials who hold them.

Layers:

| Layer | Meaning |
|---|---|
| `cd` | U.S. House, current (119th Congress) |
| `cd120` | U.S. House from Jan 2027, only where the lines changed |
| `sldu` | State Senate (Nebraska: the unicameral Legislature) |
| `sldl` | Lower chamber: House, Assembly, or House of Delegates |
| `sf`, `oak`, `sj` | San Francisco, Oakland, San Jose councils (California only) |

## License

Everything in this repository is dedicated to the public domain under [CC0 1.0](LICENSE). Attribution is appreciated but not required.

Upstream sources are public domain (U.S. Census, congress-legislators, Open States) or public records published by state and city governments.
