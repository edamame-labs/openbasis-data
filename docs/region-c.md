# Official legislative roster adapters: region C

`tools/regions/region_c.py` collects only responses issued by state legislatures.
The November 2, 2026 validation collected **1,812 people** from 28 roster HTTP responses plus 32 field-join responses (Oregon OData, Washington sponsors, 30 Texas Senate member pages).
Counts describe included people, not statutory seats. Omitted rows never establish
vacancies. Ohio and Pennsylvania are implemented separately in `region_d.py`.

| State | Senate | Lower chamber | Direct government source and inclusion rule |
|---|---:|---:|---|
| Oklahoma | Not collected by this adapter | 99 | [House current directory](https://www.okhouse.gov/representatives): server-published `__NEXT_DATA__`, `isCurrent=true`, `selectedLegislature.current=true`, 60th Legislature; `legislatureMembers`, excluding explicit vacant placeholders. |
| Oregon | 30 | 60 | [Senate CSV](https://www.oregonlegislature.gov/senate/Documents/senate.csv), [House CSV](https://www.oregonlegislature.gov/house/Documents/house.csv), linked by the respective [Senate](https://www.oregonlegislature.gov/senate/Pages/SenatorsAll.aspx) and [House](https://www.oregonlegislature.gov/house/Pages/RepresentativesAll.aspx) current directories; email and phone from the CSVs. Party and `LegislatorCode` from the Legislature's [OData API](https://api.oregonlegislature.gov/odata/odataservice.svc/Legislators?$filter=SessionKey%20eq%20'2025I1'&$format=json) (2025–2026 interim, the API's default session), joined only on exact chamber, district and first/last name; three unmatched spellings (e.g. `Muñoz`/`Munoz`) stay without party. |
| Rhode Island | 38 | 74 | [Official roster list](https://www.rilegislature.gov/Lists/legislationInformation/AllItems.aspx): follow its exact next-page URLs; include only `ActiveFlag=Yes`, with the explicit `chamber`, `district`, `legislator_name`, `political_party`, biography URL and list ID. Five pages checked. |
| South Carolina | 46 | 124 | [Senate](https://www.scstatehouse.gov/member.php?chamber=S), [House](https://www.scstatehouse.gov/member.php?chamber=H): the pages explicitly identify “Current Session By Last Name”; one `memberOutline` per person. |
| South Dakota | 35 | 70 | [Official sessions API](https://sdlegislature.gov/api/Sessions) explicitly identifies 2026, SessionId 71, as `CurrentSession=true`; [official address-list CSV](https://sdlegislature.gov/api/SessionMembers/71.csv) provides `Body`, names, party and district. Future visible 2027 session excluded. |
| Tennessee | 33 | 97 | [Senate](https://wapp.capitol.tn.gov/apps/LegislatorInfo/Directory?chamber=S&ga=114), [House](https://wapp.capitol.tn.gov/apps/LegislatorInfo/Directory?chamber=H&ga=114): explicitly select 114th General Assembly, 2025–2026. Exclude vacant placeholders. Default directory now selects 115, while the [official homepage](https://www.capitol.tn.gov/) says the 115th convenes January 12, 2027; therefore the default future session is not used. |
| Texas | 30 | 148 | [Senate](https://senate.texas.gov/members.php) explicitly identifies 89th Legislature and defines `*` as a currently vacant seat; starred placeholders are excluded; [House](https://house.texas.gov/members) embeds structured `get-members` data; only `active=1`. |
| Utah | 29 | 74 | [Government legislator JSON](https://le.utah.gov/data/legislators.json), directly requested by the [Senate roster](https://senate.utah.gov/senate-roster/) page's published JavaScript. Require each record's legislation link to identify `sess=2026GS`; split explicit `house=S/H`. |
| Vermont | 30 | 150 | [Senate JSON](https://legislature.vermont.gov/people/loadAll/2026/Senate), [House JSON](https://legislature.vermont.gov/people/loadAll/2026/House), exact AJAX URLs from [Senate directory](https://legislature.vermont.gov/people/all/2026/Senate) and [House directory](https://legislature.vermont.gov/people/all/2026/House), labeled 2025–2026 session. Exclude nonempty `TerminationReason`: 2 former senators and 8 former representatives. |
| Virginia | 40 | 99 | [Senate directory](https://apps.senate.virginia.gov/Senator/index.php), [House directory](https://house.vga.virginia.gov/members), the latter explicitly headed “Members of the 2026 Virginia House of Delegates.” Parse directory member cards; do not extract unrelated staff. |
| Washington | 49 | 98 | [Live legislator directory](https://leg.wa.gov/legislators/?chamber=senate), linked by the [Senate chamber page](https://leg.wa.gov/about-the-legislature/senate/), explicitly references 2025–26 biennium. The response contains both chambers, so split explicit `data-chamber`, not the URL filter. Email and phone from the official [sponsor web service](https://wslwebservices.leg.wa.gov/SponsorService.asmx/GetSponsors?biennium=2025-26), joined by member `Id` and requiring the current chamber (`Agency`) and district, since the biennium list keeps prior-chamber entries. |
| West Virginia | 34 | 100 | [Senate roster](https://www.wvlegislature.gov/Senate1/roster.cfm), [House roster](https://www.wvlegislature.gov/House/roster.cfm): named lawmaker link and adjacent party/district cells. Senate districts have multiple people; retain each person. |
| Wisconsin | 33 | 99 | [Senate](https://docs.legis.wisconsin.gov/2025/legislators/senate), [Assembly](https://docs.legis.wisconsin.gov/2025/legislators/assembly): explicit 2025 session directories for 2025–2026 biennium; parse district cards and official Details links. |
| Wyoming | 31 | 62 | [Senate API](https://api.wyoleg.gov/v1/Legislator/2026/S), [House API](https://api.wyoleg.gov/v1/Legislator/2026/H): year-specific roster with explicit chamber and `legStatus=C`. API URL is published in the legislature application's [configuration](https://www.wyoleg.gov/assets/config/config.jsonc); the roster URL pattern is in its legislator service JavaScript. |

## Reproduction and validation

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools -p test_region_c.py -v
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import sys, collections
sys.path.insert(0, 'tools')
from build import fetch
from regions.region_c import collect
rows, sources = collect(fetch)
print(collections.Counter(row['state'] for row in rows))
print(len(rows), len(sources))
PY
```

`collect(fetch, offline=True)` uses checksummed local snapshots without network
access. The shared fetcher records the exact URL, retrieval time, final URL and
SHA-256 of response bytes; each record references the particular response that
supports it. Rhode Island pagination uses distinct references per page. A fresh
run requires direct government responses; no third-party or old dataset input is
read. Retrieval time is not a publication date. Live directories without a dated
publication are labeled as live directories rather than assigned invented dates.

Names retain source spelling. Directories formatted `family, given` are reordered
for display, preserving a final recognized suffix; Oregon's explicit first/last
fields are joined. Numeric leading zeros are removed only where the publisher's
field includes them; alphanumeric and named districts are retained. Derived IDs
hash explicit publisher person IDs or biography links; named and multi-member
districts never become person identifiers. Only government-hosted biography URLs
are retained. Addresses and other fine-grained details are omitted.

Contacts (`build.contact`) and `ids` are copied only where the same roster
publishes them: email/phone/photo/ids for UT, WY, WI and WA (photo/ids), VA
(Senate: Capitol Office phone; House: Capitol Phone, mailto), WV, RI (email, phone,
list `ID`), VT (`Email`, `HomePhone`, `PersonID`), SD (`Phone`), TN (capitol phone
column), OK/SC/TX (portraits; OK/SC/TX House ids). District-office numbers are
never substituted for a missing capitol line. Wyoming `legPhoto` paths resolve
against `siteURL` from the application's published configuration, as its own
JavaScript does. A photo URL shown for more than one person is dropped as a
placeholder. Fields from a second response carry `fieldEvidence` and reference
that response.

Texas Senate party comes from each district's official member page
(`https://senate.texas.gov/member.php?d=N`, labeled `Party:`), fetched only for
districts with a roster row (the vacant seat's page is never requested), each a
separate source `tx-upper-member-dN`. It is used only when the page's portrait
name (`#memhead` alt, whitespace/entities normalized) equals the roster name
exactly; Borris L. Miles (13) and Lois W. Kolkhorst (18) carry a middle initial
on the page, so they have no party. The Virginia House directory shows party
only as an unlabeled initial in each card's search index (`name room party
phones ...`); that initial is interpreted as party (D/R/I via
`build.party_name`) only when it directly follows the card's own name and
Capitol Office room, otherwise left empty. No official list found publishes
Texas House party; those rows have no party.

Tests cover terminated members, inactive Texas placeholders, Rhode Island active
flags and pagination, future-session rejection, named multi-member districts,
source-distinct person IDs, suffix placement, unknown active flags, conflicting
single-member district occupants, fail-closed structural errors, contact
extraction, exact-match party/contact joins and placeholder-photo removal.
Size bounds detect selector failures; they are not proof that all legal seats
are occupied. Source disagreement or stale-looking official downloads require
review; no source is described as infallible.

## Access limitation

Both `https://oksenate.gov/senators` and
`https://www.oksenate.gov/senators` returned an HTTP 307 Sucuri JavaScript cookie
challenge to the HTTP collector. This adapter imports no Oklahoma senators and
has no secondary-source fallback. The [browser-DOM adapter](region-d.md) supplies 47 named senators from the
validated official rendered roster; national coverage includes both chambers.

Rhode Island's anonymous REST API and XML export were inaccessible; the public
HTML list view remains accessible and supplies active flags and pagination.
The downloadable XLS/XLSX contact files are not used: they lack the live list's
explicit active-state filtering.
