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

The governor sites don't state a party. For 36 states, `party` comes from a second page published by a government body of the same state that states a party beside a person's name (`PARTY_RULES`). The page is one of:

- a roster of current officeholders, or a list of the state's governors;
- the official results, or the official candidate list or record, of the election that began the governor's term.

Each rule's pattern lists the people the page names, with `name` and `party` groups. It runs on the HTML-unescaped page with whitespace collapsed; JSON bodies are read as served. The governor's party is the party of the entries that name the governor.

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
| AZ | Arizona Citizens Clean Elections Commission | [www.azcleanelections.gov](https://www.azcleanelections.gov/Custom/ElectionDataSearch?type=G&sw=A&part=A&inc=A&win=A&cycles=18&offices=2&page=1) | 2022-11-08 general election candidate record | `Katie Hobbs`, `Democratic` |
| CA | California State Library | [governors.library.ca.gov](https://governors.library.ca.gov/40-Newsom.html) | governor's page in the Governors' Gallery | `Gavin Newsom`, `Democrat` |
| CO | Colorado Secretary of State | [www.sos.state.co.us](https://www.sos.state.co.us/pubs/elections/Results/Abstract/2022/general/governor.html) | 2022-11-08 general election | `Jared Polis`, `DEM` |
| CT | Connecticut Secretary of the State | [portal.ct.gov](https://portal.ct.gov/sots/register-manual/section-iv/dept-of-social-services--dept-of-veterans-affairs-and-unaffiliated) | list of governors (State Register and Manual) | `Ned Lamont`, `D` |
| DE | Delaware Department of Elections | [elections.delaware.gov](https://elections.delaware.gov/reports/GE2024.html) | 2024-11-05 general election | `MATT MEYER`, `Democratic Party` |
| FL | Florida Division of Elections | [dos.elections.myflorida.com](https://dos.elections.myflorida.com/candidates/CanDetail.asp?account=79799) | 2022-11-08 general election candidate record | `Ron DeSantis`, `Republican` |
| GA | Georgia Secretary of State | [results.sos.ga.gov](https://results.sos.ga.gov/cdn/results/Georgia/export-2022NovGen.json) | 2022-11-08 general election | `Brian Kemp`, `REP` |
| HI | Hawaii Office of Elections | [elections.hawaii.gov](https://elections.hawaii.gov/governor-and-lieutenant-governor/) | current officeholders | `Josh Green`, `D` |
| ID | Idaho Secretary of State | [voteidaho.gov](https://voteidaho.gov/idaho-elected-officials/) | current elected officials | `Brad Little`, `R` |
| IL | Illinois State Board of Elections | [www.elections.il.gov](https://www.elections.il.gov/ElectionOperations/ElectionVoteTotals.aspx?ID=62) | 2022-11-08 general election | `JB PRITZKER`, `DEMOCRATIC` |
| IN | Indiana Election Division | [indianavoters.in.gov](https://indianavoters.in.gov/ENRHistorical/ExportElectionsToCSV?year=2024&electionType=General&candidateName=&county=&office=Governor%20%26%20Lt.%20Governor&party=&sortBy=&sortDir=&filterCandidateName=&filterElectionType=false) | 2024-11-05 general election | `Mike Braun`, `Republican` |
| KS | Kansas Historical Society | [www.kansashistory.gov](https://www.kansashistory.gov/kansapedia/laura-kelly/20157) | governor's Kansapedia entry | `Laura Kelly`, `Democrat` |
| LA | Louisiana Secretary of State | [voterportal.sos.la.gov](https://voterportal.sos.la.gov/ElectionResults/ElectionResults/Data?blob=20231014/RacesCandidates_Multiparish.htm) | 2023-10-14 gubernatorial primary election | `"Jeff" Landry`, `REP` |
| MA | Secretary of the Commonwealth of Massachusetts | [electionstats.state.ma.us](https://electionstats.state.ma.us/elections/view/154338/) | 2022-11-08 general election | `Maura Healey`, `Democratic` |
| MD | Maryland State Board of Elections | [elections.maryland.gov](https://elections.maryland.gov/elections/archive/2022/general_results/gen_results_2022_1.html) | 2022-11-08 general election | `Wes Moore`, `Democratic` |
| ME | Maine State Law and Legislative Reference Library | [legislature.maine.gov](https://legislature.maine.gov/lawlibrary/governors-of-maine-1820/9197) | list of governors | `JANET T. MILLS`, `Democrat` |
| MN | Minnesota Legislative Reference Library | [www.lrl.mn.gov](https://www.lrl.mn.gov/mngov/gov) | list of governors | `Tim Walz`, `Democratic-Farmer-Labor` |
| MO | Missouri State Archives | [www.sos.mo.gov](https://www.sos.mo.gov/archives/history/historicallistings/governors) | list of governors | `Mike Kehoe`, `R` |
| MT | Montana Historical Society | [mhs.mt.gov](https://mhs.mt.gov/Research/Compass/Facts) | list of officeholders | `Greg Gianforte`, `Republican` |
| NC | North Carolina State Board of Elections | [er.ncsbe.gov](https://er.ncsbe.gov/enr/20241105/data/results_0.txt) | 2024-11-05 general election | `Josh Stein`, `DEM` |
| ND | State Historical Society of North Dakota | [www.history.nd.gov](https://www.history.nd.gov/exhibits/governors/index.html) | list of governors | `Kelly Armstrong`, `R` |
| NM | New Mexico Secretary of State | [electionresults.sos.nm.gov](https://electionresults.sos.nm.gov/resultsSW.aspx?type=SW&map=CTY&eid=2838) | 2022-11-08 general election | `MICHELLE LUJAN GRISHAM`, `Democrat` |
| NV | Nevada State Library, Archives and Public Records | [nsla.nv.gov](https://nsla.nv.gov/archives-governor) | list of governors | `Joe Lombardo`, `Republican` |
| OK | Oklahoma Historical Society | [www.okhistory.org](https://www.okhistory.org/research/governors) | list of governors | `Kevin Stitt`, `Republican` |
| OR | Oregon Secretary of State | [sos.oregon.gov](https://sos.oregon.gov/blue-book/government/Pages/governor-bio.aspx) | Oregon Blue Book governor entry | `Tina Kotek`, `Democrat` |
| PA | Pennsylvania Department of State | [www.electionreturns.pa.gov](https://www.electionreturns.pa.gov/api/ElectionReturn/GET?methodName=GetSummaryData&electionid=94&electiontype=G&isactive=0) | 2022-11-08 general election | `SHAPIRO, JOSHUA D`, `DEM` |
| RI | Rhode Island Board of Elections | [www.ri.gov](https://www.ri.gov/election/results/2022/general_election/races/3.html) | 2022-11-08 general election | `Daniel J. McKee`, `DEM` |
| SD | South Dakota Secretary of State | [sdsos.gov](https://sdsos.gov/elections-voting/election-resources/current-elected-officials.aspx) | current elected officials | `Larry Rhoden`, `R` |
| TX | Legislative Reference Library of Texas | [lrl.texas.gov](https://lrl.texas.gov/legeLeaders/governors/govBrowse.cfm) | list of governors | `Greg Abbott`, `R` |
| UT | Utah Historical Society | [historytogo.utah.gov](https://historytogo.utah.gov/post/governors/) | list of governors | `Spencer J. Cox`, `Republican Party` |
| VA | Virginia Department of Elections | [historical.elections.virginia.gov](https://historical.elections.virginia.gov/contest/164996) | 2025-11-04 general election | `Abigail D. Spanberger`, `Democratic` |
| VT | Vermont Secretary of State | [electionarchive.vermont.gov](https://electionarchive.vermont.gov/contest/160972) | 2024-11-05 general election | `Phil Scott`, `Republican` |
| WA | Washington State Library | [www.sos.wa.gov](https://www.sos.wa.gov/library/research-collections/washington-territorial-and-state-governors) | list of governors | `Bob Ferguson`, `Democrat` |
| WV | West Virginia Secretary of State | [apps.sos.wv.gov](https://apps.sos.wv.gov/elections/candidate-search/candidate.aspx?candidate=22761) | 2024 election candidate record | `Patrick Morrisey`, `Republican` |

Alaska and Florida publish their results under family names only (`Dunleavy/Dahlstrom`, `DeSantis / Nuñez`), so those rules read the Division of Elections candidate list and candidate record instead. The California, Kansas, Florida and West Virginia pages are about one person, and the Oregon page is the Blue Book's entry for the current governor. When one of those offices changes hands the rule stops the build and needs a new page.

### Party not collected

These 14 governors have no `party`. No page of the state's government that states it could be read over plain HTTP with `USER_AGENT` in November 2026, and no association, encyclopedia, news or party source substitutes for one. The reasons are also in `PARTY_NOT_COLLECTED`.

| State | Reason |
| --- | --- |
| AR | Secretary of State results are PDFs or a script-rendered vendor application; its elected-officials page names no party. |
| IA | sos.iowa.gov answered USER_AGENT with a Cloudflare challenge (HTTP 403); the results site is script-rendered; the canvass and Official Register are PDFs. |
| KY | State Board of Elections results are PDFs; its live-results host returned HTTP 403. |
| MI | www.michigan.gov and mvic.sos.state.mi.us returned HTTP 403; the Michigan Manual is a PDF. |
| MS | The Secretary of State results application returned HTTP 403; certified results are PDFs. |
| NE | Certified 2022 results are PDFs; the Secretary of State results site serves only the latest election. |
| NH | www.nh.gov and www.sos.nh.gov returned HTTP 403. |
| NJ | Division of Elections 2025 results are PDFs; no readable state page names a party. |
| NY | State Board of Elections hosts returned a Cloudflare challenge (HTTP 403). |
| OH | ohiosos.gov returned a JavaScript security check (HTTP 403). |
| SC | State Election Commission results are on a vendor host that sends only gzip-encoded bodies; the Legislative Manual is a PDF. |
| TN | Results and the Blue Book are PDF or XLSX; the state roster names no party. |
| WI | The Elections Commission returned a bot challenge (HTTP 403); the Blue Book is a PDF. |
| WY | Secretary of State roster and 2022 results are PDFs; the state's list of governors gives no party for the incumbent. |

## Boundary links

Governors link to their state's Census feature with `matchingRule: "statewide-governor-state-fips"`, the same way U.S. senators link (`statewide-senate-state-fips`). `district_links.target_layer` checks for the governor office before the Nebraska unicameral rule, so the Nebraska governor is never joined to a legislative district.

## Browser captures

Seven official governor sites refuse automated retrieval but load in a normal browser: Kansas, Massachusetts, Michigan, Minnesota, New Hampshire, New York and Rhode Island. Each page was captured in a normal browser and imported with `tools/import_snapshot.py`, and these states are listed in `BROWSER`. Their sources are recorded with `representation: "browser-dom"` and the observation time. Like every browser-only source, they need captures from the last 24 hours before a `--browser-snapshots --fresh` publication. `import_snapshot.py --final-url` records a redirect, such as `governor.kansas.gov` → `www.governor.ks.gov` and `mass.gov/orgs/office-of-the-governor` → a page named after the current governor.

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
