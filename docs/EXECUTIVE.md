# State executive officers

`tools/regions/executive.py` collects sitting governors from each state's own governor website. Lieutenant governors, secretaries of state, attorneys general and other statewide offices are not collected yet, and `coverage.json` lists them under `stateExecutive.notCollected`.

Governor records enter `data/` the next time the release is rebuilt and published with `--browser-snapshots --fresh`. Until then the checked-in snapshot has none.

## Sources and extraction

There is one source per state: the governor's official homepage, or a governor biography page on that site where the homepage names the governor only inside news items (North Dakota, South Dakota). Each rule in `RULES` names a single element that identifies the officeholder: the page `<title>`, a heading, or a meta description. Its pattern runs on the HTML-unescaped page with whitespace collapsed.

- The pattern must match at least once and produce exactly one distinct name. Zero matches or two different names stop the build.
- A name must have two to five words and must not contain `Office`, `Governor`, `Home`, `Welcome` or `State`.
- The North Dakota source URL contains the governor's name. When the office changes hands that page disappears, the fetch fails, and the rule needs review.
- Records carry `office: "Governor"`, `body: "<State> Executive"`, `level: "state"`, and `website` set to the source page. Contact details and term dates are not published in these elements and are not added from other directories. `party` comes from a second page, described under [Party](#party).
- HTTP requests use the user agent `Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)`, recorded in each source's `acquisition.requestHeaders`. Several state sites reject curl's default agent.

A homepage reports the officeholder its publisher currently shows. After the November 2026 elections, governors-elect take office on dates set by each state. Until a site changes, the record continues to name the sitting governor, and the record does not establish a term end.

## Party

The governor sites don't state a party. For 49 states, `party` comes from a second page or PDF published by a government body of the same state that states a party beside a person's name (`PARTY_RULES`). The publisher is a state body, except in Ohio, where it is a county board of elections. The document is one of:

- a roster of current officeholders, or a list of the state's governors, including those printed in a state manual or blue book;
- the official results, or the official candidate list or record, of the election that began the governor's term. Arkansas's and New Hampshire's are the results declared before the legislature, as printed in the House Journal.

Each rule's pattern lists the people the document names, with `name` and `party` groups. It runs on the HTML-unescaped page with whitespace collapsed; JSON bodies are read as served. The governor's party is the party of the entries that name the governor.

A response that is a PDF is read as the text `pypdf` extracts (`pdf_text`), page by page, with whitespace collapsed. `pypdf` is pinned in `requirements-geo.txt`. The checksum in the source record is of the PDF as served. Extracted text can split a word where the PDF kerns it (`T erry E. Branstad`), so a name split that way matches no governor and stops the build.

Party values enter `data/` the next time the release is rebuilt and published with `--browser-snapshots --fresh`. Until then the checked-in governor records have none.

- **Matching.** An entry names the governor when the family names (the last word, after dropping `Jr.`, `Sr.`, `II`, `III`, `IV`) are equal and one name's first given name is among the other's given names. Case, accents and punctuation are ignored, and `Family, Given` order is accepted. Two given names agree when they are equal or one is a prefix of the other of at least three letters (`Dan` / `Daniel`, `Josh` / `Joshua`). Nothing else is treated as a nickname: `Mike` does not match `Michael`, and an entry that gives only a family name does not match.
- **Fail closed.** The build stops when the pattern matches nothing, when no entry names the governor, when the governor's entries state two different parties, or when the label is not in `PARTY_LABELS`.
- **Labels.** `R`, `REP` and `Republican` are published as `Republican`; `D`, `DEM`, `Democrat` and `Democratic` as `Democratic`; a trailing `Party` is dropped. Minnesota's `Democratic-Farmer-Labor` is kept.
- **Provenance.** The record's `sources` lists the governor site and the party page (`gov-party-<st>`), and `fieldEvidence.party` names the party page. Sources read from an election carry `effectivePeriod`.

A party read from election results or a candidate record is the party the governor was listed under at that election. A list of governors or a roster states the party its publisher currently shows. Neither establishes that the affiliation has not changed since.

| State | Publisher | Page | Basis | Listed as |
| --- | --- | --- | --- | --- |
| AK | Alaska Division of Elections | [www.elections.alaska.gov](https://www.elections.alaska.gov/candidates/?election=22genr) | 2022-11-08 general election candidate list | `Dunleavy, Mike`, `Registered Republican` |
| AL | Alabama Department of Archives and History | [archives.alabama.gov](https://archives.alabama.gov/research/guidance/fast-facts/officials/governor.aspx) | list of governors | `Kay Ivey`, `Republican` |
| AR | Arkansas House of Representatives | [www.arkleg.state.ar.us](https://www.arkleg.state.ar.us/Home/FTPDocument?path=%2Fassembly%2F2023%2F2023R%2FDocuments%2F2023R+House+Journal.pdf) (PDF) | 2022-11-08 general election | `Sarah Huckabee Sanders`, `REP` |
| AZ | Arizona Citizens Clean Elections Commission | [www.azcleanelections.gov](https://www.azcleanelections.gov/Custom/ElectionDataSearch?type=G&sw=A&part=A&inc=A&win=A&cycles=18&offices=2&page=1) | 2022-11-08 general election candidate record | `Katie Hobbs`, `Democratic` |
| CA | California State Library | [governors.library.ca.gov](https://governors.library.ca.gov/40-Newsom.html) | governor's page in the Governors' Gallery | `Gavin Newsom`, `Democrat` |
| CO | Colorado Secretary of State | [www.sos.state.co.us](https://www.sos.state.co.us/pubs/elections/Results/Abstract/2022/general/governor.html) | 2022-11-08 general election | `Jared Polis`, `DEM` |
| CT | Connecticut Secretary of the State | [portal.ct.gov](https://portal.ct.gov/sots/register-manual/section-iv/dept-of-social-services--dept-of-veterans-affairs-and-unaffiliated) | list of governors (State Register and Manual) | `Ned Lamont`, `D` |
| DE | Delaware Department of Elections | [elections.delaware.gov](https://elections.delaware.gov/reports/GE2024.html) | 2024-11-05 general election | `MATT MEYER`, `Democratic Party` |
| FL | Florida Division of Elections | [dos.elections.myflorida.com](https://dos.elections.myflorida.com/candidates/CanDetail.asp?account=79799) | 2022-11-08 general election candidate record | `Ron DeSantis`, `Republican` |
| GA | Georgia Secretary of State | [results.sos.ga.gov](https://results.sos.ga.gov/cdn/results/Georgia/export-2022NovGen.json) | 2022-11-08 general election | `Brian Kemp`, `REP` |
| HI | Hawaii Office of Elections | [elections.hawaii.gov](https://elections.hawaii.gov/governor-and-lieutenant-governor/) | current officeholders | `Josh Green`, `D` |
| IA | Iowa Legislative Services Agency | [www.legis.iowa.gov](https://www.legis.iowa.gov/docs/publications/RDBKI/1597053.pdf) (PDF) | list of governors in the Iowa Official Register 2025-2026, chapter 7 | `Kim Reynolds`, `R` |
| ID | Idaho Secretary of State | [voteidaho.gov](https://voteidaho.gov/idaho-elected-officials/) | current elected officials | `Brad Little`, `R` |
| IL | Illinois State Board of Elections | [www.elections.il.gov](https://www.elections.il.gov/ElectionOperations/ElectionVoteTotals.aspx?ID=62) | 2022-11-08 general election | `JB PRITZKER`, `DEMOCRATIC` |
| IN | Indiana Election Division | [indianavoters.in.gov](https://indianavoters.in.gov/ENRHistorical/ExportElectionsToCSV?year=2024&electionType=General&candidateName=&county=&office=Governor%20%26%20Lt.%20Governor&party=&sortBy=&sortDir=&filterCandidateName=&filterElectionType=false) | 2024-11-05 general election | `Mike Braun`, `Republican` |
| KS | Kansas Historical Society | [www.kansashistory.gov](https://www.kansashistory.gov/kansapedia/laura-kelly/20157) | governor's Kansapedia entry | `Laura Kelly`, `Democrat` |
| KY | Kentucky State Board of Elections | [elect.ky.gov](https://elect.ky.gov/results/2020-2029/Documents/Certification%20of%20Election%20Results%20for%202023%20General%20Election%20Final.pdf) (PDF) | 2023-11-07 general election | `Andy BESHEAR`, `Democratic` |
| LA | Louisiana Secretary of State | [voterportal.sos.la.gov](https://voterportal.sos.la.gov/ElectionResults/ElectionResults/Data?blob=20231014/RacesCandidates_Multiparish.htm) | 2023-10-14 gubernatorial primary election | `"Jeff" Landry`, `REP` |
| MA | Secretary of the Commonwealth of Massachusetts | [electionstats.state.ma.us](https://electionstats.state.ma.us/elections/view/154338/) | 2022-11-08 general election | `Maura Healey`, `Democratic` |
| MD | Maryland State Board of Elections | [elections.maryland.gov](https://elections.maryland.gov/elections/archive/2022/general_results/gen_results_2022_1.html) | 2022-11-08 general election | `Wes Moore`, `Democratic` |
| ME | Maine State Law and Legislative Reference Library | [legislature.maine.gov](https://legislature.maine.gov/lawlibrary/governors-of-maine-1820/9197) | list of governors | `JANET T. MILLS`, `Democrat` |
| MI | Michigan Legislative Service Bureau | [legislature.mi.gov](https://legislature.mi.gov/documents/2025-2026/michiganmanual/Chapter%204.pdf) (PDF) | list of governors in the Michigan Manual 2025-2026, chapter IV | `Gretchen Whitmer`, `D` |
| MN | Minnesota Legislative Reference Library | [www.lrl.mn.gov](https://www.lrl.mn.gov/mngov/gov) | list of governors | `Tim Walz`, `Democratic-Farmer-Labor` |
| MO | Missouri State Archives | [www.sos.mo.gov](https://www.sos.mo.gov/archives/history/historicallistings/governors) | list of governors | `Mike Kehoe`, `R` |
| MS | Mississippi Secretary of State | [www.sos.ms.gov](https://www.sos.ms.gov/elections/electionresults/2023General/State%20Certified%20Results/2023%20Statewide%20Recapitulation%20Sheet.pdf) (PDF) | 2023-11-07 general election | `Tate Reeves`, `Republican` |
| MT | Montana Historical Society | [mhs.mt.gov](https://mhs.mt.gov/Research/Compass/Facts) | list of officeholders | `Greg Gianforte`, `Republican` |
| NC | North Carolina State Board of Elections | [er.ncsbe.gov](https://er.ncsbe.gov/enr/20241105/data/results_0.txt) | 2024-11-05 general election | `Josh Stein`, `DEM` |
| ND | State Historical Society of North Dakota | [www.history.nd.gov](https://www.history.nd.gov/exhibits/governors/index.html) | list of governors | `Kelly Armstrong`, `R` |
| NE | Nebraska Legislature | [nebraskalegislature.gov](https://nebraskalegislature.gov/pdf/bluebook/407-431.pdf) (PDF) | list of governors in the Nebraska Blue Book | `Jim Pillen`, `R` |
| NH | New Hampshire House of Representatives | [gc.nh.gov](https://gc.nh.gov/house/calendars_journals/journals/2025/HJ%2002%20January%208,%202025.pdf) (PDF) | 2024-11-05 general election | `Kelly Ayotte`, `r` |
| NJ | New Jersey Division of Elections | [www.nj.gov](https://www.nj.gov/state/elections/assets/pdf/election-results/2025/2025-official-general-results-governor.pdf) (PDF) | 2025-11-04 general election | `MIKIE SHERRILL`, `Democratic` |
| NM | New Mexico Secretary of State | [electionresults.sos.nm.gov](https://electionresults.sos.nm.gov/resultsSW.aspx?type=SW&map=CTY&eid=2838) | 2022-11-08 general election | `MICHELLE LUJAN GRISHAM`, `Democrat` |
| NV | Nevada State Library, Archives and Public Records | [nsla.nv.gov](https://nsla.nv.gov/archives-governor) | list of governors | `Joe Lombardo`, `Republican` |
| OH | Logan County Board of Elections | [www.boe.ohio.gov](https://www.boe.ohio.gov/logan/c/elecres/20221108results.pdf) (PDF) | 2022-11-08 general election | `Mike DeWine`, `REP` |
| OK | Oklahoma Historical Society | [www.okhistory.org](https://www.okhistory.org/research/governors) | list of governors | `Kevin Stitt`, `Republican` |
| OR | Oregon Secretary of State | [sos.oregon.gov](https://sos.oregon.gov/blue-book/government/Pages/governor-bio.aspx) | Oregon Blue Book governor entry | `Tina Kotek`, `Democrat` |
| PA | Pennsylvania Department of State | [www.electionreturns.pa.gov](https://www.electionreturns.pa.gov/api/ElectionReturn/GET?methodName=GetSummaryData&electionid=94&electiontype=G&isactive=0) | 2022-11-08 general election | `SHAPIRO, JOSHUA D`, `DEM` |
| RI | Rhode Island Board of Elections | [www.ri.gov](https://www.ri.gov/election/results/2022/general_election/races/3.html) | 2022-11-08 general election | `Daniel J. McKee`, `DEM` |
| SC | South Carolina Legislature | [www.scstatehouse.gov](https://www.scstatehouse.gov/man26/04_Gov.pdf) (PDF) | governor's entry in the 2026 Legislative Manual | `McMASTER, Henry D.`, `R` |
| SD | South Dakota Secretary of State | [sdsos.gov](https://sdsos.gov/elections-voting/election-resources/current-elected-officials.aspx) | current elected officials | `Larry Rhoden`, `R` |
| TN | Tennessee Secretary of State | [publications.tnsosfiles.com](https://publications.tnsosfiles.com/pub/blue_book/25-26/25-26_Executive.pdf) (PDF) | governor's entry in the Tennessee Blue Book 2025-2026 | `Bill Lee`, `R` |
| TX | Legislative Reference Library of Texas | [lrl.texas.gov](https://lrl.texas.gov/legeLeaders/governors/govBrowse.cfm) | list of governors | `Greg Abbott`, `R` |
| UT | Utah Historical Society | [historytogo.utah.gov](https://historytogo.utah.gov/post/governors/) | list of governors | `Spencer J. Cox`, `Republican Party` |
| VA | Virginia Department of Elections | [historical.elections.virginia.gov](https://historical.elections.virginia.gov/contest/164996) | 2025-11-04 general election | `Abigail D. Spanberger`, `Democratic` |
| VT | Vermont Secretary of State | [electionarchive.vermont.gov](https://electionarchive.vermont.gov/contest/160972) | 2024-11-05 general election | `Phil Scott`, `Republican` |
| WA | Washington State Library | [www.sos.wa.gov](https://www.sos.wa.gov/library/research-collections/washington-territorial-and-state-governors) | list of governors | `Bob Ferguson`, `Democrat` |
| WI | Wisconsin Legislative Reference Bureau | [docs.legis.wisconsin.gov](https://docs.legis.wisconsin.gov/misc/lrb/blue_book/2025_2026/020_elected_officials.pdf) (PDF) | elected officials in the Wisconsin Blue Book 2025-2026 | `Tony Evers`, `Democrat` |
| WV | West Virginia Secretary of State | [apps.sos.wv.gov](https://apps.sos.wv.gov/elections/candidate-search/candidate.aspx?candidate=22761) | 2024 election candidate record | `Patrick Morrisey`, `Republican` |
| WY | Wyoming Secretary of State | [sos.wyo.gov](https://sos.wyo.gov/Services/docs/GovernorRoster.pdf) (PDF) | roster of governors | `Mark Gordon`, `R` |

Alaska and Florida publish their results under family names only (`Dunleavy/Dahlstrom`, `DeSantis / Nuñez`), so those rules read the Division of Elections candidate list and candidate record instead. The California, Kansas, Florida and West Virginia pages are about one person, and the Oregon page is the Blue Book's entry for the current governor. When one of those offices changes hands the rule stops the build and needs a new page.

Notes on the PDF sources:

- **Editions.** The Iowa, Michigan, South Carolina, Tennessee and Wisconsin documents are chapters of a dated edition of the state's manual or blue book. A later edition has a new address, and the rule keeps reading the old one until it is updated. The Nebraska address is a page range of the online Blue Book and can change when the book is repaginated. The South Carolina and Tennessee rules read the governor's own entry, so they list one person.
- **Kentucky.** The certification prints the party headings above the slates (`Democratic Party  Republican Party  Write-In`, then the names in the same column order). The rule reads the first heading with the first slate of each contest, which are adjacent in the extracted text, and lists nobody from the other columns. It stops the build if the governor is not the first-column candidate.
- **New Jersey.** Each page of the official list has one candidate, with the party on the line after the address.
- **New Hampshire.** The House Journal of 8 January 2025 prints the return of votes for governor that the Secretary of State presented to the joint convention. It marks candidates `r`, `d` and `i`.
- **Arkansas.** The House Journal of the 2023 regular session prints the results of the general election for governor as declared before the joint session on 10 January 2023. The journal has 3,547 pages, and the rule reads the first 200 (`PDF_PAGES`).
- **Ohio.** The Secretary of State's site answers `USER_AGENT` with a JavaScript security check, and the General Assembly's journals print the canvass for governor without parties. The rule reads the official canvass of one county board of elections (Logan County), which prints the ballot's party label beside each statewide candidate. Only the label is used, not the county's vote counts. The canvass also lists `Pat DeWine`, whom the given-name rule keeps apart from the governor.

### Party not collected

This governor has no `party`. No page or PDF of the state's government that states it could be read over plain HTTP with `USER_AGENT` in November 2026, and no association, encyclopedia, news or party source substitutes for one. The reasons are also in `PARTY_NOT_COLLECTED`.

| State | Reason |
| --- | --- |
| NY | State Board of Elections hosts returned a Cloudflare challenge (HTTP 403); the State Library's list of governors, the Governor's site and the open-data campaign filer records name no party. |

## Boundary links

Governors link to their state's Census feature with `matchingRule: "statewide-governor-state-fips"`, the same way U.S. senators link (`statewide-senate-state-fips`). `district_links.target_layer` checks for the governor office before the Nebraska unicameral rule, so the Nebraska governor is never joined to a legislative district.

## Browser captures

Five official governor sites refuse automated retrieval but load in a normal browser: Kansas, Michigan, Minnesota, New Hampshire and Rhode Island. They answer `USER_AGENT` with HTTP 403 or a bot challenge. Each page was captured in a normal browser and imported with `tools/import_snapshot.py`, and these states are listed in `BROWSER`. Their sources are recorded with `representation: "browser-dom"` and the observation time. Like every browser-only source, they need captures from the last 24 hours before a `--browser-snapshots --fresh` publication. `import_snapshot.py --final-url` records a redirect, such as `governor.kansas.gov` → `www.governor.ks.gov`.

Massachusetts was a browser capture until November 2026. `mass.gov/orgs/office-of-the-governor` now answers `USER_AGENT` over HTTP, redirecting to a page named after the current governor, so it is read like the other HTTP sources. New York was one as well: its site answers `USER_AGENT` over HTTP, and the served tag ends ` />` where a serialized DOM's ends `>`. The rule accepts both.

## Colorado

`governor.colorado.gov` accepted no HTTPS connection from any network tried in November 2026. The source is therefore the governor's site as served on the state portal, `https://www.colorado.gov/governor/`. It is published by the State of Colorado and carries the same Governor's Office site. If the subdomain recovers, either URL is acceptable; record which one was used.

## Not collected

None as of November 2026. A state that can't be read on a run is moved to `BLOCKED`, recorded as `not-collected` with its URL in `stateExecutive.blockers`, and never filled from another publisher.

## Network egress

Reachability depends on the network a request leaves from. From a hosting-provider address (a VPN exit), Connecticut and Tennessee refused or dropped connections. From a residential connection, both returned their pages over HTTP to `USER_AGENT`. A state that fails from one network is recorded as blocked for that run. Its status is never changed by retrying through proxies or other networks chosen to get around the block.

## Refreshing

The repeatable procedure (schedule, commands, failure handling, and the rule against evading access controls) is in [skills/refresh-governors/SKILL.md](../skills/refresh-governors/SKILL.md).

## Tests

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_executive.py'
```
