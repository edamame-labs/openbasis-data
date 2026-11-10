# State courts of last resort: Montana to Wyoming

`tools/regions/courts_b.py` collects the members of the courts of last resort for MT, NE, NV, NH, NJ, NM, NY, NC, ND, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI and WY. It reads each court's roster from that court's own judiciary website. Oklahoma and Texas each have two courts of last resort, one for civil and one for criminal cases, and both are declared. The module follows the interface in `tools/statewide.py` and declares `COURTS`, `SOURCES`, `BROWSER` (currently empty), `USER_AGENT`, `collect` and `parse`.

## Extraction rules

- Each rule in `RULES` names one repeated element of the roster page: a heading, table row, card title or list entry that carries a member's title and name. The pattern runs on the HTML-unescaped page with whitespace collapsed.
- The number of matches must equal the court's seat count (the rule's `seats` value, taken from the sources below). A vacancy counts toward the seats only when the rule declares a `vacancy` pattern for a marker the page itself shows. No current rule declares one. A page that lists fewer members than there are seats and shows no vacancy marker stops the build.
- Names must be distinct, two to six words long, and must not contain title words. The court must have exactly one `Chief Justice` or `Presiding Judge`, and every member's title must come from one family: Chief Justice/Justice, or Presiding Judge/Judge.
- Source titles map to row offices. `Associate Justice`, `Associate Chief Justice` (WA) and `Vice Chief Justice` become `Justice`. `Vice Presiding Judge` (OK) becomes `Judge`. `Interim Chief Justice` (UT) becomes `Chief Justice`.
- Rows: `id` is `<st>-court-<slug of the member's name>`, `body` is the court's name, `office` is the mapped title, `level` is `state`, and `website` is the source URL. Party, districts, contact details and terms are not taken.
- Utah and Washington print names in capitals. `display_name` converts them to title case but keeps initials, Roman numerals and the `Mc` prefix (`McCLOUD` becomes `McCloud`). Washington breaks names with `<br>` at varying points, and the rule reads each `<br>` as a space.
- Requests use the user agent `Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)`.

## Per-state sources

| State | Court (`body`) | Seats (source) | Source URL | Element read | Status |
|---|---|---|---|---|---|
| MT | Montana Supreme Court | 7: MCA 3-2-101 (mca.legmt.gov) | https://courts.mt.gov/Courts/Supreme/About/bios/ | Biography table cells: text after the photo link, `Chief Justice/Justice <name> is/was` | collected |
| NE | Nebraska Supreme Court | 7: Neb. Const. art. V, §2 (nebraskalegislature.gov) | https://nebraskajudicial.gov/courts/supreme-court/supreme-court-justices | `views-field-title` links `Hon. <name>[, Chief Justice]` | collected |
| NV | Supreme Court of Nevada | n/a | https://nvcourts.gov/supreme/justices | n/a | not collected: bot challenge (HTTP 403) |
| NH | New Hampshire Supreme Court | n/a | https://www.courts.nh.gov/our-courts/supreme-court | n/a | not collected: HTTP 403 Access Denied |
| NJ | Supreme Court of New Jersey | 7: N.J. Const. art. VI, §2 (njleg.state.nj.us) | https://www.njcourts.gov/courts/supreme/about | `<h2 class="mt-0">` headings of the meet-the-justices links | collected |
| NM | New Mexico Supreme Court | 5: stated on the source page ("consists of five Justices") | https://supremecourt.nmcourts.gov/about-this-court/supreme-court-justices/ | `<h2 class="wp-block-heading">` headings | collected |
| NY | New York Court of Appeals | n/a | https://www.nycourts.gov/ctapps/ | n/a | not collected: bot challenge (HTTP 403) |
| NC | Supreme Court of North Carolina | 7: G.S. 7A-10 (ncleg.gov) | https://www.nccourts.gov/courts/supreme-court/meet-the-justices | `judge__title` + `judge__full-name` spans | collected |
| ND | North Dakota Supreme Court | 5: ndcourts.gov/supreme-court ("has five justices") | https://www.ndcourts.gov/supreme-court/justices | `<h5 class="card-title">` | collected |
| OH | Supreme Court of Ohio | 7: stated on the source page (Ohio Constitution sets the size at seven) | https://www.supremecourt.ohio.gov/courts/judicial-system/supreme-court-of-ohio/justices-overview/ | "Supreme Court Justices" link list entries | collected |
| OK | Supreme Court of Oklahoma | n/a | https://www.oscn.net/static/JudicialDirectory.pdf | n/a | not collected: roster only in a PDF |
| OK | Oklahoma Court of Criminal Appeals | 5: 20 O.S. §31 (oscn.net) | https://www.okcca.net/judges/ | Photo caption links `Presiding Judge/Vice Presiding Judge/Judge <name>` | collected |
| OR | Oregon Supreme Court | 7: ORS 2.010 (oregonlegislature.gov) | `https://www.courts.oregon.gov/courts/_api/web/GetList('/courts/Lists/Judges')/items?$filter=Category eq 'Supreme'&$select=...` | The Judges list that the justices page renders, as XML: `FirstName`, `Middle_x0020_Initial`, `Title` (surname), `Suffix`, and `Job_x0020_Title` (`Supreme Court Chief Justice` / `Supreme Court Justice`); `Category` must be `Supreme` | collected |
| PA | Supreme Court of Pennsylvania | 7: pacourts.us/learn ("the seven justices") | https://www.pacourts.us/courts/supreme-court/supreme-court-justices | Portrait link spans `Chief Justice/Justice<br/> <name>` | collected |
| RI | Rhode Island Supreme Court | n/a | https://www.courts.ri.gov/Courts/SupremeCourt/Pages/default.aspx | n/a | not collected: no current roster in HTTP responses |
| SC | Supreme Court of South Carolina | 5: S.C. Code 14-3-10 (scstatehouse.gov) | https://www.sccourts.org/courts/supreme-court/justices/ | `small-title` headings | not collected: 4 members listed, no vacancy marker |
| SD | South Dakota Supreme Court | 5: stated on the source page ("comprised of five justices") | https://ujs.sd.gov/supreme-court/ | `profilepage__subhead` links followed by the matching role line | collected |
| TN | Tennessee Supreme Court | n/a | https://www.tncourts.gov/courts/supreme-court/judges | n/a | not collected: JavaScript challenge |
| TX | Supreme Court of Texas | 9: the source page numbers the seats (Chief Justice, Places 2 to 9) | https://www.txcourts.gov/supreme/about-the-court/justices/ | `span9 offset1` bio headings | collected |
| TX | Texas Court of Criminal Appeals | 9: the source page numbers the seats (Places 1 to 9) | https://www.txcourts.gov/cca/about-the-court/judges/ | `span9 offset1` bio headings | collected |
| UT | Utah Supreme Court | 7: Utah Code 78A-3-101(1), effective 1/31/2026 (le.utah.gov) | https://www.utcourts.gov/en/courts/other-court-info/judges-bios/appellate-courts/supreme-court.html | Teaser title on each card's `flip-card-back` (each card prints its title twice) | collected |
| VT | Vermont Supreme Court | 5: stated on the source page ("the chief justice and four associate justices") | https://www.vtcourts.gov/supreme-court | Justices table rows: `Honorable <name>` and the title cell | collected |
| VA | Supreme Court of Virginia | 7: Va. Code §17.1-300 (law.lis.virginia.gov) | https://www.vacourts.gov/courts/scv/home | Accordion entries `The Honorable <name>` followed by `Expiration of term`; the Chief Justice section names the chief. Senior Justices have no term line and are not read. | collected |
| WA | Washington Supreme Court | 9: stated on the source page ("The nine state Supreme Court justices") | https://www.courts.wa.gov/appellate_trial_courts/SupremeCourt/?fa=supremecourt.justices | Biography list links | collected |
| WV | Supreme Court of Appeals of West Virginia | 5: courtswv.gov about-the-court page ("five Supreme Court justices") | https://www.courtswv.gov/appellate-courts/supreme-court-of-appeals/justices-staff | First cell of each Justices & Staff table row | collected |
| WI | Wisconsin Supreme Court | 7: stated on the source page ("composed of seven justices") | https://www.wicourts.gov/courts/supreme/justices/index.htm | `team-title-heading` links | collected |
| WY | Wyoming Supreme Court | 5: stated on the source page ("There are five justices") | https://www.wyocourts.gov/supreme-court/ | `team-member-name` headings followed by the matching role line | collected |

20 of the 27 courts are collected. All 20 rules were checked against live pages on 9 November 2026, and each yielded its full seat count with one chief or presiding member.

## Not collected

These courts are recorded as `not-collected`, with the reason in `COURTS[st]['blockers']`. No other publisher is used for them.

- **Nevada, New York**: the court sites answered `USER_AGENT` with a Cloudflare bot challenge ("Just a moment...", HTTP 403). Both could become `BROWSER` sources if a person captures the page in a normal browser and a rule is written against that capture.
- **New Hampshire**: `courts.nh.gov` returned HTTP 403 "Access Denied" for every path tried.
- **Tennessee**: `tncourts.gov` returned a JavaScript challenge page instead of content. Solving it is not permitted.
- **Rhode Island**: the Supreme Court page builds its content with scripts, and no HTTP response from `courts.ri.gov` lists the current justices. The only roster document, `AboutTheSupremeCourt.pdf`, was last modified in 2023, so it doesn't establish current membership.
- **Oklahoma Supreme Court**: `oscn.net` publishes the current justices only in the PDF Judicial Directory (`/static/JudicialDirectory.pdf`), and the build has no PDF text extraction.
- **South Carolina**: the justices page listed four members, but S.C. Code 14-3-10 provides five seats, and the page shows no vacancy marker. Under the fail-closed rule the court is not collected. Once the page lists five members or marks the vacancy, move the court from `BLOCKED` to `RULES` with a rule for its `small-title` headings (`<h3 class="small-title"><span class="d-block">Chief Justice|Justice</span> <name></h3>`). If the page marks a vacancy, also add a `vacancy` pattern.

New York's Court of Appeals titles its members Chief Judge and Associate Judge. `statewide.COURT_OFFICES` has no `Chief Judge`, so the vocabulary needs that entry before New York can be collected.

## Tests

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_courts_b.py'
```

The fixture tests cover title extraction, the Presiding Judge family, a missing marker, a missing seat, conflicting and repeated names, two chiefs or none, the vacancy rule, capitalized names with line breaks, the separate chief rule (VA), the Oregon list, and the declarations and coverage check.
