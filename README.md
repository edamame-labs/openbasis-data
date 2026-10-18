# OpenBasis Data

Open data on U.S. elected officials, state by state, and on how their districts overlap. It covers members of Congress, state legislators, statewide executives, and selected city councils.

**Currently published: California, Maryland, New Hampshire, Texas.** A state is added once its data has been checked against the legislature's and Congress's official rosters (seat counts, vacancies, district matching). More states follow as each is reviewed.

Every record links back to the public source it came from, and the methodology below explains how the derived numbers (district overlaps) are computed. The data powers OpenBasis, and you're free to use it for anything else too (see [License](#license)).

## Files

| File | What it is |
|---|---|
| [`data/officials.json`](data/officials.json) | Every official, with contact info, cross-reference IDs, and the source of each record |
| [`data/officials.csv`](data/officials.csv) | The same as a flat table |
| [`data/states/index.json`](data/states/index.json) | One summary row per state: population, block count, and district count per layer |
| `data/states/<st>/districts.json` | The state's district layers. Each district has its 2020 population and the districts in other layers it shares residents with |
| `data/states/<st>/overlaps.csv` | The state's overlaps as a flat table: one row per pair of districts |
| `data/states/<st>/boundaries/*.geojson` | Simplified district boundaries, one file per layer, meant for maps rather than analysis |
| [`seeds/<st>/*.yml`](seeds) | Hand-maintained rosters for sites that can't be fetched automatically |

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

When two sources describe the same person, records are matched on level + state + jurisdiction + normalized name. Sources are applied in a fixed priority order: earlier ones win on conflicting fields, and later ones only fill gaps. For local offices, official city websites outrank Open States.

### When a source breaks

Websites go down, change their HTML, or serve bot challenges. Each source has a sanity check. Most check a minimum record count; the SF scraper must find exactly one supervisor for each of districts 1–11. When a source fails its check, its records from the previous run are **carried forward** rather than dropped, so nobody disappears from the dataset because a website was down. The failure is recorded in `runs` in `officials.json` (`error`, `carriedForward: true`), and carried-forward records keep their original `retrievedAt` dates.

### Matching officials to districts

District names differ between sources ("Coos 05" vs "Coos 5", "Third Middlesex" vs "3rd Middlesex", "Norfolk, Worcester and Middlesex" vs "Norfolk-Worcester-Middlesex"). Both sides are reduced to a canonical key: lowercase, ordinals as digits, leading zeros dropped, separators and "and" removed. Congressional at-large seats are district `0`. Multi-member districts (common in Arizona, Maryland, New Hampshire, Vermont and elsewhere) map to several officials.

### District overlaps

Overlap is measured in **people, not area**. For every populated 2020 Census block (about 8 million nationwide), the block's interior point is assigned to the district containing it in each layer. Two districts overlap by the total population of the blocks they share. Blocks never cross state lines, so each state is computed on its own.

- Legislative districts are drawn from whole Census blocks, so this is essentially exact for them. City council lines may occasionally split a block; in that case the whole block goes to the district containing its interior point.
- Pairs that share fewer than 100 people, or under 0.1% of the smaller district, are dropped as boundary noise.
- Sanity check: each state's congressional layer sums to its 2020 Census population, and every other statewide layer sums to the same total.

`share_of_district` in `overlaps.csv` answers "what fraction of this district's residents also live in the other one?" Each pair appears twice, once from each side.

### Boundaries

Overlaps are computed from TIGERweb geometry at about 10 m precision. The files under `boundaries/` are for display only: they come from Census cartographic boundary files, which are clipped to the shoreline. The 2027 congressional layer has no cartographic file yet, so its display boundaries are clipped to the 119th Congress outline instead. All layers are simplified with [mapshaper](https://github.com/mbloch/mapshaper) using topology-preserving simplification, so neighboring districts still share edges.

## Known limitations

- **2027 congressional maps.** `cd` is the 119th Congress map that current members represent. `cd120`, present only for states whose lines changed, is the map used in the November 3, 2026 election (California's comes from Proposition 50), effective January 3, 2027. Its seats have no officials attached until the winners are seated.
- **New Hampshire floterial districts.** These are House districts layered on top of base districts. Census publishes no separate boundaries for them, so members elected from floterial districts aren't linked to a district shape.
- **Hand-maintained seeds.** The Oakland and San Jose rosters are hand-maintained, and each file records the date it was last checked against the city site.
- **SF in CI.** sf.gov blocks GitHub Actions, so the weekly refresh carries the SF supervisor roster forward. It is refreshed whenever the pipeline runs from an ordinary network.
- **Vacancies.** Empty seats appear as districts with no official.
- **Population vintage.** Population is from the 2020 Census, not current estimates.

## Corrections

Spotted something wrong? Open an issue or a pull request.

- **Hand-maintained rosters.** Edit `seeds/<st>/*.yml`, include the official source URL, and bump `verifiedAt`.
- **Automated sources.** Most errors there come from upstream (Open States, congress-legislators), and fixing them there helps everyone. Link the upstream fix in your issue.

## Updates

The data is refreshed weekly. A commit is made only when the data actually changes, so the git history doubles as a changelog of who held which office when. `runs` in `officials.json` records each source's result for the latest refresh.

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
