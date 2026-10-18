# OpenBasis Data

Open data on California's elected officials, from Congress down to city councils, and on how their districts overlap.

Every record links back to the public source it came from, and the methodology below explains how the derived numbers (district overlaps) are computed. The data powers OpenBasis, and you're free to use it for anything else too (see [License](#license)).

## Files

| File | What it is |
|---|---|
| [`data/officials.json`](data/officials.json) | Every official, with contact info, cross-reference IDs, and the source of each record |
| [`data/officials.csv`](data/officials.csv) | The same as a flat table |
| [`data/districts.json`](data/districts.json) | Each district's 2020 population and the districts in other layers it shares residents with |
| [`data/overlaps.csv`](data/overlaps.csv) | The overlaps as a flat table: one row per pair of districts |
| [`data/boundaries/*.geojson`](data/boundaries) | Simplified district boundaries, one file per layer, meant for maps rather than analysis |
| [`seeds/*.yml`](seeds) | Hand-maintained rosters for sites that can't be fetched automatically |

To use the data without cloning, read it straight from GitHub, e.g.
`https://raw.githubusercontent.com/edamame-labs/openbasis-data/main/data/officials.csv`.
To pin a version, put a commit SHA in place of `main`.

## Coverage

| Level | Officials | Districts (boundaries) |
|---|---|---|
| Federal | 2 U.S. senators, 52 U.S. representatives | 52 congressional districts (119th Congress) |
| State | State Senate, Assembly, Governor, Lt. Governor, Attorney General, Secretary of State | 40 Senate, 80 Assembly districts |
| City | Mayors and councils of San Francisco, Oakland, San Jose | 11 + 7 + 10 council districts |

## Sources

| Data | Source | How it's collected |
|---|---|---|
| Members of Congress | [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators) | JSON download |
| State legislators | [Open States](https://open.pluralpolicy.com/data/) bulk CSV | CSV download |
| State executives, mayors | [openstates/people](https://github.com/openstates/people) | YAML from GitHub |
| SF Board of Supervisors | [sf.gov](https://www.sf.gov/departments--board-supervisors) | Scraped from the board page and profiles |
| Oakland, San Jose councils | [oaklandca.gov](https://www.oaklandca.gov/Government/City-Council-Leadership/Council-Members), [sanjoseca.gov](https://www.sanjoseca.gov/your-government/departments-offices/mayor-and-city-council) | **By hand** in `seeds/` (both sites return HTTP 403 to scripts) |
| Congressional and legislative boundaries | U.S. Census [TIGERweb](https://tigerweb.geo.census.gov/) (analysis) and [cartographic boundary files](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) (display) | ArcGIS REST / shapefile |
| SF supervisor districts | [DataSF](https://data.sfgov.org/d/f2zs-jevy) | GeoJSON |
| Oakland council districts | [City of Oakland GIS](https://services.arcgis.com/9tC74aDHuml0x5Yz/arcgis/rest/services/CouncilDistrict_2022_Revised/FeatureServer/0) | ArcGIS REST |
| San Jose council districts | [City of San Jose GIS](https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/120) | ArcGIS REST |
| Population | 2020 Census blocks (P.L. 94-171 `POP100`) via TIGERweb | ArcGIS REST |

Each official carries a `sources` list with the URL and retrieval date of every record merged into it.

## Methodology

### Merging officials

When two sources describe the same person, records are matched on level + jurisdiction + normalized name. Sources are applied in a fixed priority order: earlier ones win on conflicting fields, and later ones only fill gaps. For local offices, official city websites outrank Open States. Example: San Jose's site lists Mayor Mahan's term as ending 2028-12-31, where Open States had 2027.

### When a source breaks

Websites go down, change their HTML, or serve bot challenges. Each source has a sanity check. Most check a minimum record count; the SF scraper must find exactly one supervisor for each of districts 1–11. When a source fails its check, its records from the previous run are **carried forward** rather than dropped, so nobody disappears from the dataset because a website was down. The failure is recorded in `runs` in `officials.json` (`error`, `carriedForward: true`), and carried-forward records keep their original `retrievedAt` dates. If there's no previous data to fall back on, the run refuses to write anything.

### District overlaps

Overlap is measured in **people, not area**. For every populated 2020 Census block in California (377,591 of them), the block's interior point is assigned to the district containing it in each layer. Two districts overlap by the total population of the blocks they share.

- Legislative districts are drawn from whole Census blocks, so this is essentially exact for them. City council lines may occasionally split a block; in that case the whole block goes to the district containing its interior point.
- Pairs that share fewer than 100 people, or under 0.1% of the smaller district, are dropped as boundary noise.
- Sanity check: each statewide layer sums to 39,538,223, California's 2020 Census population.

`share_of_district` in `overlaps.csv` answers "what fraction of this district's residents also live in the other one?" Each pair appears twice, once from each side.

### Boundaries

Overlaps are computed from TIGERweb geometry at about 10 m precision. The files in `data/boundaries/` are for display only. Statewide layers come from Census cartographic boundary files, which are clipped to the shoreline. All layers are simplified with [mapshaper](https://github.com/mbloch/mapshaper) using topology-preserving simplification, so neighboring districts still share edges.

## Known limitations

- **Congressional lines.** These are the 119th Congress districts that current members represent. Under Proposition 50 (2025), new lines take effect with the 120th Congress in January 2027 and aren't included yet.
- **Hand-maintained seeds.** The Oakland and San Jose rosters are hand-maintained, and each file records the date it was last checked against the city site. They won't pick up mid-term changes automatically.
- **SF in CI.** sf.gov blocks GitHub Actions, so the weekly refresh carries the SF supervisor roster forward. It's refreshed whenever the pipeline runs from an ordinary network. `runs` in `officials.json` shows when.
- **Vacancies.** The State Legislature has 120 seats but the source lists 118 people, which likely reflects vacancies.
- **Population vintage.** Population is from the 2020 Census, not current estimates.

## Corrections

Spotted something wrong? Open an issue or a pull request.

- **Oakland and San Jose rosters.** Edit `seeds/*.yml`, include the official source URL, and bump `verifiedAt`.
- **Automated sources.** Most errors there come from upstream (Open States, congress-legislators), and fixing them there helps everyone. Link the upstream fix in your issue.

## Updates

The data is refreshed weekly. A commit is made only when the data actually changes, so the git history doubles as a changelog of who held which office when. `runs` in `officials.json` records each source's result for the latest refresh.

## Schema

**`officials.json`**: `{ generatedAt, officials: Official[], runs }`. Each `Official` has:

| Field | Notes |
|---|---|
| `id` | Stable slug, e.g. `ca-assembly-buffy-wicks` |
| `name`, `givenName`, `familyName` | |
| `level` | `federal`, `state`, or `local` |
| `jurisdiction` | `California`, `San Francisco`, `Oakland`, `San Jose` |
| `office`, `body`, `district` | e.g. `State Assemblymember`, `California State Assembly`, `14` |
| `party`, `gender` | When the source provides them |
| `email`, `phone`, `address`, `website`, `contactForm`, `photo`, `socials` | Public office contact info |
| `termEnd` | ISO date, when known |
| `ids` | Cross-references: `bioguide`, `fec`, `opensecrets`, `wikidata`, `govtrack`, `openstates` |
| `sources` | `{ name, url, retrievedAt }` for every record merged into this one |

**`districts.json`**: `{ generatedAt, blocks, layers, districts }`. `districts` is keyed by `<layer>:<district>` (e.g. `sldl:14`), and each entry has `pop` (2020 population), `bbox`, and `overlaps: { key, pop }[]` sorted largest first.

Layers:

| Layer | Meaning | Matches `Official.body` |
|---|---|---|
| `cd` | U.S. House | `U.S. House` |
| `sldu` | State Senate | `California State Senate` |
| `sldl` | State Assembly | `California State Assembly` |
| `sf` | SF Board of Supervisors | `San Francisco Board of Supervisors` |
| `oak` | Oakland City Council | `Oakland City Council` |
| `sj` | San Jose City Council | `San Jose City Council` |

## License

Everything in this repository is dedicated to the public domain under [CC0 1.0](LICENSE). Attribution is appreciated but not required.

Upstream sources are public domain (U.S. Census, congress-legislators, Open States) or public records published by the cities listed above.
