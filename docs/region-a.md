# Government roster adapters: region A

The adapters in `tools/regions/region_a.py` read government publishers directly. They do not read an aggregator, an archived dataset, or a previous output. The minimal record consists of the person's published name, chamber, district, party when supplied, and a direct reference to the response supporting those fields. Source snapshots retain SHA-256 checksums over their recorded evidence representation (HTTP response body or official browser DOM) and retrieval times. Retrieval confirms what the publisher returned; it is not an independent certification of the underlying facts.

## Implemented sources

Counts below were obtained from official responses retrieved on 2026-11-02 (UTC). Counts describe returned current person records, not inferred vacancies. Lower/upper counts are listed in that order.

| State | Lower / upper | Official source and current-member rule |
| --- | --- | --- |
| Alabama | 105 / 35 | [House directory](https://alison.legislature.state.al.us/house-leaders-members); public government GraphQL endpoint filters `active.eq=true` and `elected.eq=true`. |
| Alaska | 40 / 20 | [House](https://w3.akleg.gov/house.php), [Senate](https://w3.akleg.gov/senate.php). Current-member cards link to 34th Legislature member profiles. Leadership cards are not counted twice. Senate districts retain official letters. |
| Arizona | 60 / 30 | [Member roster](https://www.azleg.gov/MemberRoster/). `HouseRoster` and `SenateRoster` tables; rows explicitly marked `inactive` are excluded. Leadership titles following ` -- ` are removed from the name field. |
| Arkansas | 99 / 33 | [Legislators list](https://www.arkleg.state.ar.us/Legislators/List), explicitly 95th General Assembly, 2026 fiscal session. `(Resigned)` and `(Deceased)` records are excluded. |
| Colorado | 65 / 35 | [Legislators](https://leg.colorado.gov/legislators), 2026 regular session. Resignation/death notes in the name cell exclude departed members. |
| Connecticut | 151 / 36 | [House](https://www.cga.ct.gov/asp/menu/hlist.asp), [Senate](https://www.cga.ct.gov/asp/menu/slist.asp), current member lists. Senate `S01`-style district codes become `1`; caucus or personal websites are not used as independent sources. |
| Delaware | 41 / 21 | [House](https://legis.delaware.gov/Chambers/House/AssemblyMembers), [Senate](https://legis.delaware.gov/Chambers/Senate/AssemblyMembers), government Kendo grid JSON transport detailed below. Null person IDs do not create person records. |
| Idaho | 70 / 35 | [House](https://legislature.idaho.gov/house/membership/), [Senate](https://legislature.idaho.gov/senate/membership/), current 2026 directory. Per-member district links explicitly carry `yr=2026`. |
| Iowa | 99 / 49 | [House](https://www.legis.iowa.gov/legislators/house), [Senate](https://www.legis.iowa.gov/legislators/senate). Only current `sortableTable` is read; separate former-member tables are excluded. Official biography links must identify General Assembly 91. |
| Kansas | 125 / 40 | [Representatives](https://www.kslegislature.gov/b2025_26/house/representatives/?per_page=all), [Senators](https://www.kslegislature.gov/b2025_26/senate/senators/?per_page=all), 2025-2026 biennium. Each linked government member profile supplies its full name, chamber, district and party. Abbreviated directory labels are not expanded heuristically. |
| Kentucky | 100 / 38 | [House](https://apps.legislature.ky.gov/Legislators/hmembers_county.html), [Senate](https://apps.legislature.ky.gov/Legislators/smembers_county.html), current county-to-member directories. The displayed county/district cell supplies the district number; profile query parameters are internal identifiers. Repeated county references to the same person/district are deduplicated, and disagreements fail validation. |
| Florida | 116 / 39 | [House](https://www.flhouse.gov/representatives), [Senate](https://www.flsenate.gov/Senators), 2024-2026 directories. House pending-election placeholders and the partial-term section are excluded. Former senators have an additional person-ID URL component and are excluded; a `Vacant` label produces no person record. |
| Illinois | 118 / 59 | [House](https://www.ilga.gov/House/Members), [Senate](https://www.ilga.gov/Senate/Members), 104th General Assembly (2025-2026). Only cards before the explicit `Former Members` heading are read. Identical desktop/mobile cards are deduplicated. |
| Georgia | 180 / 56 | [House](https://www.legis.ga.gov/members/house), [Senate](https://www.legis.ga.gov/members/senate), 2025-2026 regular session explicitly labeled Current. `(Until MM/DD/YYYY)` dates before the source retrieval date exclude former members. |
| Indiana | 100 / 50 | [Current 2026 legislators](https://iga.in.gov/legislative/2026/legislators). Only cards with an explicit chamber, party and district are published. An additional Andy Zay card has no district and is excluded as unsupported; no departure status is inferred. |
| Hawaii | 51 / 25 | [House](https://www.capitol.hawaii.gov/legislature/legislators.aspx?chamber=H), [Senate](https://www.capitol.hawaii.gov/legislature/legislators.aspx?chamber=S), 2026 regular session. Cards labeled `Term of Office Ended:` are excluded, including Daniel Holt and Michelle Kidani in this snapshot. |

Names published as `Family, Given` are reordered to `Given Family`, preserving punctuation within the components. IDs contain a hash of the name as well as the chamber and district, so Arizona's and Idaho's two-member House districts retain distinct people. District cardinality checks reject conflicting occupants outside those chambers. Bounds on roster size detect selector failure and do not assert that absent districts are vacant.

## API discovery and reproduction

### Alabama

The official directory's Next.js runtime names `https://alison.legislature.state.al.us/graphql` as `NEXT_PUBLIC_FE_GRAPHQL_URL`. Its lazy-loaded `MemberGallery` query requests active elected `legislativeMembers`. The adapter issues a GET request with this URL-encoded GraphQL query:

```graphql
{legislativeMembers(where:{active:{eq:true},elected:{eq:true}}){data{id body fullName district honorificFullNameAffiliation}}}
```

It retains the government's `fullName`, extracts the district number from its explicit `House District N` or `Senate District N` label, and reads a party suffix only when supplied. No login, token or third-party service is required. The exact encoded query URL is retained in each record's source.

### Delaware

The official chamber HTML initializes the Kendo grid with these transports:

- `POST https://legis.delaware.gov/json/House/GetRepresentatives`
- `POST https://legis.delaware.gov/json/Senate/GetSenators`

The request body is `page=1&pageSize=100&sort=DistrictNumber-asc`. GET requests to those same routes return an error page. The snapshot source records the request method and body. The parser requires `Total == len(Data)`, no `Errors`, and the expected `ChamberId`. It reads `PersonFullName`, `DistrictNumber`, `PartyCode`, and `LegislatorDetailLink` directly.

### Kansas

The current directory's page-size selector explicitly offers `per_page=all`. The adapter requests that published option and still follows an official `Next` pagination link if one is present. It fetches only the directory's `data-href` member-profile links on `www.kslegislature.gov`, retaining a separate checksum and source for each profile. Full names are read from `leg-hero-title`; district and party are read from the adjacent official profile fields. Profile paths are not converted into names.

## Collection and verification

From the repository root:

```sh
python3 -m unittest discover -s tools -p test_region_a.py -v
python3 tools/build.py
python3 tools/build.py --verify
```

Florida House, Illinois, Hawaii, Georgia and Indiana use live official browser DOM snapshots because curl receives access blocks or an unrendered shell. These sources are explicitly labeled `representation: browser-dom`; their SHA-256 covers the serialized DOM, not an HTTP response body. `tools/import_snapshot.py` imports a complete DOM exported from the exact allowlisted official URL and requires its actual observation timestamp within 24 hours. An online curl refresh cannot replace this browser acquisition step. To reproduce this snapshot from saved evidence, use `python3 tools/build.py --offline`.

An offline rebuild uses the recorded snapshots. Missing snapshots, checksum mismatches, changed session markers, malformed responses, unhandled pagination, missing columns and incompatible district occupants stop collection. Tests cover inactive members, explicit resignations/deaths, current-versus-former tables, letter districts, multi-member district identity, and rejection of access-block pages.

## Source access and unresolved entries

Both chambers were collected for all 16 states covered by this adapter. Access blocks are handled by acquiring the exact government page through a browser; they are not handled by substituting another publisher or retaining legacy records. The API variants remain described above so acquisition can be reproduced without guessing endpoints.

Indiana's official current-session roster displays 151 entries. Exactly 150 cards supply districts: 100 House and 50 Senate, each district unique within its chamber. The additional [Andy Zay card](https://iga.in.gov/legislative/2026/legislators/legislator_andy_zay_1) says only `Sen. Andy Zay (R) Senate` and provides no district. The district-17 card explicitly names Nick McKinley. The district-less entry is excluded because its current district assignment is unsupported; absence of a district is not itself evidence of resignation or another departure. `sources.json` records the excluded source label and reason, and `COVERAGE` retains this limitation.

Direct curl acquisition of the Indiana client application returned an unrendered shell, including for its linked application script. Its government API root separately reports an API-key requirement. The live government browser page rendered the complete current-session roster without an account; the dataset uses that observed page, not the protected API or any secondary directory.
