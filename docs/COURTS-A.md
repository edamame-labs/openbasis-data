# State courts of last resort, Alabama through Missouri

`tools/regions/courts_a.py` collects the current members of the court of last resort in 25 states (AL, AK, AZ, AR, CA, CO, CT, DE, FL, GA, HI, ID, IL, IN, IA, KS, KY, LA, ME, MD, MA, MI, MN, MS, MO). Every one of these states has a single court of last resort. Members are read only from the court's own website. All sitting members are included, whether they were elected or appointed.

## Records

- `body` is the court's name as declared in `COURT_NAMES`, for example `Supreme Court of Alabama` or `Maine Supreme Judicial Court`.
- `office` is `Chief Justice` for the chief justice and `Justice` for every other member. Source titles such as Associate Justice, Presiding Justice (GA, MS), Vice Chief Justice (AZ) and Deputy Chief Justice (KY) all map to `Justice`. Each rule lists the titles it accepts, and any other title stops the build.
- `id` is `<st>-court-<slug of the member's name>`, for example `al-court-sarah-h-stewart`.
- `level` is `state`, and `website` is the court page the member was read from. Party, contact details and term dates are not collected.

## Extraction rules

Each pattern runs on the page after HTML comments are removed, entities are unescaped and whitespace is collapsed. For each court:

- The rule's element must yield exactly the court's seat count, less any seats the same page marks with its own vacancy element. There must be exactly one chief justice, and names must be distinct.
- A name must have two to six words and must not contain words such as Justice, Court, Vacant or Clerk. If the same name appears under two titles, the build stops.
- Where a `block` is given, matches are read only between its start marker, which must occur once, and the next end marker.
- Where a `statement` is given, the page's own sentence about the court's size must be present. A changed court size then stops the build rather than silently changing the count.

HTTP requests send `USER_AGENT = Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)`.

| State | Court | Seats | Source URL | Element read | Status |
|---|---|---|---|---|---|
| AL | Supreme Court of Alabama | 9 (page: "a chief justice and eight associate justices") | https://judicial.alabama.gov/appellate/supremecourt | "Members of the Court" widget: `<b>Chief Justice</b>` / `<b>Associate Justices</b>` headings and the `/CourtMemberBio/ViewBio?id=` links under them, up to `<b>Clerk</b>` | collected |
| AK | Alaska Supreme Court | 5 | https://courts.alaska.gov/judges/index.htm | Rows of the judges table between `<a id="justices">` and `<a id="coa-judges">`; "Chief Justice" after `<br>` in the name cell | collected |
| AZ | Arizona Supreme Court | 7 (page: "Seven justices…") | https://www.azcourts.gov/meetthejustices | `<strong><span style="color:#002458; font-size:21px">` title + name | collected |
| AR | Arkansas Supreme Court | 7 | https://www.arcourts.gov/courts/supreme-court/justices | `views-field-title-1` link "<Title> <Name>, Position N" | collected |
| CA | Supreme Court of California | 7 (page: "the Chief Justice of California and six Associate Justices") | https://supreme.courts.ca.gov/about-court/justices-court | `jcc-sub-nav__item` links under "Justices of the Court"; the page's "Vacant Seat" card (`usa-card__brow-color`) counts one seat | collected (6 members, 1 page-marked vacancy) |
| CO | Colorado Supreme Court | 7 | https://www.coloradojudicial.gov/supreme-court/supreme-court-judges-and-staff | Contact teaser: `field--name-title` name followed by `field--name-field-contact-title` of "Chief Justice of the Supreme Court" / "Supreme Court Justice" | collected |
| CT | Connecticut Supreme Court | 7 | https://www.jud.ct.gov/external/supapp/supjustices.htm | "Biographies of Justices" list items `<li><a href="…justice….htm(l)">Title Name</a></li>` (commented-out former justices are removed first) | collected |
| DE | Delaware Supreme Court | 5 (page: "a chief justice and four justices") | https://courts.delaware.gov/supreme/justices.aspx | `<h3>Title Name</h3>` | collected |
| FL | Supreme Court of Florida | 7 | https://supremecourt.flcourts.gov/Justices | The page's embedded Next.js data: the Justices section navigation items `{"target":"_self","url":"/the-court/about-the-court/justices/…","name":"Title Name",…}` | collected |
| GA | Supreme Court of Georgia | 9 | https://www.gasupreme.us/court-information/biographies/ and https://www.gasupreme.us/wp-json/wp/v2/pages?parent=80&per_page=100&_fields=title,link | Membership and titles: the "Justice Biographies" paragraph (`<a href="/court-information/biographies/justice-…/">NAME</a>, Title`). Names are printed in capitals there, so the display name comes from the same site's WordPress listing of those biography pages, matched by link. The listing title's role must equal the paragraph's, and its name upper-cased must equal the printed name. Rows cite both sources. | collected |
| HI | Hawaii Supreme Court | 5 (page: "a Chief Justice and four Associate Justices") | https://www.courts.state.hi.us/courts/supreme/justices/justices | Member table (Name / Title / Phone / Term) | **not collected**: the table lists four members for five seats and marks no vacancy |
| ID | Idaho Supreme Court | 5 (page: "consists of five justices") | https://isc.idaho.gov/about-the-courts/sc-justices | `profile__info` `<h2 class="text-h3">Title Name</h2>` (server-rendered) | collected |
| IL | Illinois Supreme Court | 7 | https://www.illinoiscourts.gov/courts/supreme-court/meet-the-justices/ | `<h2 class="accordion-title mceEditable">Name[, Chief Justice]</h2>` | collected |
| IN | Indiana Supreme Court | 5 | https://www.in.gov/courts/supreme/justices/ | `<h6>` links between "Current Justices" and the next `<hr />`: "Title Name (n)" | collected |
| IA | Iowa Supreme Court | 7 (page: "composed of seven justices") | https://www.iowacourts.gov/iowa-courts/supreme-court/justices/ | `<h2 class="title_header">Name</h2>` + `cms_metadata2 cms_title` title | collected |
| KS | Kansas Supreme Court | 7 | https://kscourts.gov/About-the-Courts/Supreme-Court/Justices | — | **not collected**: Cloudflare block page (HTTP 403) |
| KY | Supreme Court of Kentucky | 7 | https://www.kycourts.gov/Courts/Supreme-Court/Pages/default.aspx | Card `<h3>Name</h3><h4>Title<span class="court-name">Supreme Court</span></h4><p>Nth Supreme Court District</p>` | collected |
| LA | Louisiana Supreme Court | 7 | https://www.lasc.org/Justices | — | **not collected**: Blazor Server application; the HTTP response contains no member list |
| ME | Maine Supreme Judicial Court | 7 | https://www.courts.maine.gov/courts/sjc/justices.html | `<h3><strong>Hon. Name</strong><br> Title</h3>` (the title may itself be in `<strong>`) | collected |
| MD | Supreme Court of Maryland | 7 | https://www.mdcourts.gov/scm/judges | — | **not collected**: bot challenge (HTTP 403) |
| MA | Massachusetts Supreme Judicial Court | 7 (page: "a Chief Justice and six Associate Justices") | https://www.mass.gov/info-details/supreme-judicial-court-justices | `<h2 class="ma__comp-heading" id=…>Title Name</h2>` | collected |
| MI | Michigan Supreme Court | 7 | https://www.courts.michigan.gov/api/episerver/v3.0/content?ContentUrl=https://www.courts.michigan.gov/courts/supreme-court/justices/ | The site's content-delivery record for the Justices page, from which the page renders in the browser: the "Justice Bios" link-card items `"title":"Title Name","image":…,"linkItem":`. `website` is the human page. | collected |
| MN | Minnesota Supreme Court | 7 | https://mncourts.gov/supremecourt/justices | — | **not collected**: Cloudflare challenge (HTTP 403) |
| MS | Supreme Court of Mississippi | 9 | https://courts.ms.gov/appellatecourts/sc/scjustices.php | `<span><strong>Title Name</strong><br> </span>` | collected |
| MO | Supreme Court of Missouri | 7 | https://www.courts.mo.gov/ | — | **not collected**: HTTP 403 for every page on the host |

Seat counts that the page states are asserted through `statement`. The other counts are the courts' constitutional or statutory sizes and match the number of members each page listed in November 2026.

## Not collected

Six courts are declared `not-collected`, with the reason in `COURTS[st]['blockers']`. They are not filled from any other publisher, such as state manuals, news or directories.

- Kansas, Maryland, Minnesota and Missouri refuse the project's user agent at the edge. Each would need a browser capture imported with `tools/import_snapshot.py` before it could be added to `BROWSER` with a rule.
- Louisiana's site is a Blazor Server application. A normal browser renders the member list, so it needs a browser capture as well.
- Hawaii's page is readable but lists four of its five seats without marking a vacancy. The rule would be the member-table row `<td><a …>Name</a></td> <td>Chief Justice|Associate Justice</td>`. It can be enabled once the page accounts for every seat.

## Tests

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_courts_a.py'
```
