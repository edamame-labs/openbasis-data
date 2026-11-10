# Statewide elected officers: MS, MO, MT, NE, NV, NH, NJ, NM, NY, NC, ND, OH, OK, OR

`tools/regions/statewide_c.py` collects every statewide executive officer that voters elect in these states, other than the governor (governors are in `tools/regions/executive.py`). Offices filled by appointment or by the legislature are not declared. Office keys and row titles come from `tools/statewide.py`.

## Rules

- Each rule in `RULES` reads one element of an official page: the `<title>`, a heading, a meta description, an image `alt` or caption, or a navigation label. Patterns run on the HTML-unescaped page with whitespace collapsed.
- A single-holder office must yield exactly one distinct name. A multi-member commission must yield exactly its seat count (North Dakota Public Service Commission and Oklahoma Corporation Commission: 3). Zero, conflicting or surplus names stop the build.
- A name must have two to six words and must not contain an office word (`Governor`, `Secretary`, `Attorney`, `Treasurer`, `Auditor`, `Commissioner`, `State`, ...) or a state name.
- Rows: `id` `<st>-<officeKey>` (`<st>-<officeKey>-<n>` for commissions), `body` `<State> Executive`, `level` `state`, `office` from the vocabulary, `website` the source page. Party, contact details and terms are not published in these elements and are not added from elsewhere.
- Requests use `USER_AGENT` (`Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)`). Sources are fetched at their final URL, because `build.fetch` rejects a redirect to another host.
- Some source URLs contain the officeholder's name (MO attorney general, ND lieutenant governor, OK lieutenant governor, OR treasurer). When the office changes hands the page disappears and the rule needs review.

## Officeholders-elect

The November 3, 2026 general election elected new holders of several of these offices. A page reports whoever its publisher currently shows. Until the official page changes on the day the term begins, the record names the incumbent the page shows, and nothing is inferred from election results.

## Which offices are elected

| State | Official basis for the elected-office list |
|---|---|
| MS | `https://www.sos.ms.gov/` (the Secretary of State's list of elected officials) refused retrieval. The declared offices are those whose own official pages are read below; the Agriculture and Insurance pages state the office is elected. The Public Service and Transportation Commissions are elected from three districts, not statewide, and are not declared. |
| MO | `https://mo.gov/government`, "Elected Officials": Lieutenant Governor, Secretary of State, State Auditor, State Treasurer, Attorney General. |
| MT | `https://mt.gov/govt/elected_officials`, "Statewide Elected Officials": Governor and Lieutenant Governor, Attorney General, Secretary of State, State Auditor, Superintendent of Public Instruction. The page also lists Public Service Commissioners, who are elected from five districts and are not declared as statewide. |
| NE | `https://www.nebraska.gov/government/executive-branch/`: the page lists the Lieutenant Governor, Secretary of State, Treasurer, Attorney General and Auditor of Public Accounts and describes the auditor as "one of five elected constitutional officers". |
| NV | Nevada Constitution, `https://www.leg.state.nv.us/Const/NvConst.html`, Art. 5 §17 (Lieutenant Governor) and §19 (Secretary of State, Treasurer, Controller, Attorney General). |
| NH | The Executive Council is the only elected executive body besides the governor (its five councilors are elected by district). The Secretary of State and Treasurer are chosen by the legislature and are not declared. The council's site refused retrieval (see below). |
| NJ | New Jersey Constitution, `https://www.njleg.state.nj.us/constitution`, Art. V §I ¶4 (Governor and Lieutenant Governor elected jointly) and §IV ¶3 (Secretary of State and Attorney General appointed). |
| NM | `https://www.sos.nm.gov/about-new-mexico/nm-government/`: "statewide elected officials including the Lieutenant Governor ..., Attorney General, Secretary of State, State Auditor, State Treasurer, and Commissioner of Public Lands". |
| NY | `https://elections.ny.gov/new-york-state-elected-officials` refused retrieval (Cloudflare challenge). Declared: Lieutenant Governor, Attorney General, Comptroller. |
| NC | `https://www.nc.gov/your-government/executive`: "Ten members of the Executive Branch are popularly elected", listed by name on the same page. |
| ND | `https://www.nd.gov/government/state-government`: "The voters of the state elect" the Lieutenant Governor, Agriculture Commissioner, Attorney General, Auditor, Insurance Commissioner, three Public Service Commissioners, Secretary of State, Superintendent of Public Instruction, Tax Commissioner and Treasurer. |
| OH | `https://ohio.gov/government/elected-officials`. |
| OK | Oklahoma State Election Board, `https://oklahoma.gov/elections/candidates/2026-candidate-filing-information.html` (filing fees by office): Lieutenant Governor, Attorney General, State Treasurer, State Superintendent of Public Instruction, State Auditor and Inspector, Commissioner of Labor, Insurance Commissioner, Corporation Commissioner. |
| OR | `https://www.oregon.gov/pages/government.aspx`, "Elected Officials": Secretary of State, State Treasurer, Attorney General, Labor Commissioner. |

## Sources and elements

| State | Office | Source URL | Element read |
|---|---|---|---|
| MS | Lieutenant Governor | https://www.legislature.ms.gov/ | `<h4>Lt. Gov. NAME</h4>` |
| MS | Secretary of State | https://www.sos.ms.gov/ | not collected: Cloudflare block (HTTP 403) |
| MS | Attorney General | https://attorneygenerallynnfitch.com/ | `<title>Attorney General NAME - Attorney General of Mississippi</title>`; `ago.state.ms.us` redirects here |
| MS | Treasurer | https://treasury.ms.gov/ | menu `<span class="x-anchor-text-primary">Treasurer NAME</span>` |
| MS | Auditor | https://www.osa.ms.gov/ | "Our Results for Mississippi" paragraph, `State Auditor NAME and his office` |
| MS | Commissioner of Agriculture | https://www.mdac.ms.gov/ | team card `<h3>Commissioner NAME</h3>` with bio "Mississippi's elected Commissioner of Agriculture and Commerce." |
| MS | Insurance Commissioner | https://www.mid.ms.gov/mississippi-insurance-department/about-the-mississippi-insurance-department/divisions/office-of-the-commissioner/ | `NAME, Mississippi's Nth Commissioner of Insurance and State Fire Marshal` |
| MO | Lieutenant Governor | https://ltgov.mo.gov/ | logo `alt="Office of Missouri Lieutenant Governor NAME"` |
| MO | Secretary of State | https://www.sos.mo.gov/ | `<div id="about"> <h3>About NAME</h3>` |
| MO | Auditor | https://auditor.mo.gov/ | footer "About Us" link to `/aboutus/auditor` |
| MO | Treasurer | https://treasurer.mo.gov/ | menu `aria-label="Link to About Treasurer NAME"` |
| MO | Attorney General | https://ago.mo.gov/about-us/about-ag-hanaway/ | portrait caption `NAME <br>Missouri Attorney General` |
| MT | Lieutenant Governor | https://governor.mt.gov/ | menu `Meet Lieutenant Governor NAME` |
| MT | Secretary of State | https://sosmt.gov/ | not collected: firewall block page (HTTP 403) |
| MT | Attorney General | https://dojmt.gov/ | menu `About NAME` linking to `/attorney-generals-office/about-…/` |
| MT | Auditor | https://csimt.gov/meet-commissioner-brown/ | meta description `NAME was elected as the Treasure State's Nth State Auditor` |
| MT | Superintendent of Public Instruction | https://opi.mt.gov/ | header `<span class="agency-slogan">NAME, State Superintendent</span>` |
| NE | Lieutenant Governor, Secretary of State, Treasurer, Attorney General, Auditor | https://www.nebraska.gov/government/executive-branch/ | `<h2 class="h3">TITLE NAME</h2>` for each |
| NV | Lieutenant Governor | https://www.ltgov.nv.gov/ | `<h1>Nevada Lieutenant Governor NAME</h1>` |
| NV | Secretary of State | https://www.nvsos.gov/sos | not collected: Incapsula "Request unsuccessful" page |
| NV | Attorney General | https://ag.nv.gov/ | header `<span>Nevada Attorney General NAME</span>` |
| NV | Treasurer | https://www.nevadatreasurer.nv.gov/ | portrait `alt="Treasurer NAME"` |
| NV | Controller | https://www.controller.nv.gov/ | header `<span class="AgencyTitle">Nevada State Controller NAME</span>` |
| NH | Executive Councilor | https://www.council.nh.gov/ | not collected: Access Denied (HTTP 403); `www.nh.gov` refuses the same way |
| NJ | Lieutenant Governor | https://www.nj.gov/governor/admin/ltgovernor/ | `<title>Lt. Governor NAME</title>` |
| NM | Lieutenant Governor | https://www.ltgov.nm.gov/ | `<h1><span class="hero-kicker">Lieutenant Governor</span> NAME</h1>` |
| NM | Secretary of State | https://www.sos.nm.gov/ | `<title>NAME - New Mexico Secretary of State \| …</title>` |
| NM | Attorney General | https://nmdoj.gov/ | not collected: Cloudflare challenge (HTTP 403) |
| NM | Treasurer | https://www.nmsto.gov/about | `<h1>Meet New Mexico State Treasurer NAME, …</h1>` |
| NM | Auditor | https://www.osa.nm.gov/ | footer `<a href="mailto:…@osa.nm.gov">Auditor NAME</a>` |
| NM | Commissioner of Public Lands | https://www.nmstatelands.org/ | `<title>NM State Land Office \| Commissioner NAME</title>` |
| NY | Lieutenant Governor | https://www.governor.ny.gov/about-lieutenant-governor | not collected: "Access denied" (HTTP 403); no other page of the governor's site names the lieutenant governor |
| NY | Attorney General | https://ag.ny.gov/ | meta description `NAME is the Nth Attorney General of the state of New York.` |
| NY | Comptroller | https://www.osc.ny.gov/ | `<title>Office of the New York State Comptroller \| NAME</title>` |
| NC | Lieutenant Governor and the eight Council of State officers | https://www.nc.gov/your-government/executive | Lieutenant Governor card title; "Council of State: Elected Officials" links `<a href="AGENCY">TITLE: NAME</a>` |
| ND | Lieutenant Governor | https://www.governor.nd.gov/lt-governor-michelle-strinden | `<title>Lt. Governor NAME \| North Dakota Office of the Governor</title>` |
| ND | Attorney General | https://attorneygeneral.nd.gov/ | menu `Attorney General NAME` |
| ND | Auditor | https://www.nd.gov/auditor/about-us | link `Learn more about State Auditor NAME` |
| ND | Insurance Commissioner | https://www.insurance.nd.gov/ | menu `Commissioner NAME` linking to `/about-us/commissioner-…` |
| ND | Public Service Commissioner (3) | https://www.psc.nd.gov/commission | "Meet the Commissioners" tab buttons `data-text="NAME"` (chair label removed) |
| ND | Secretary of State | https://www.sos.nd.gov/about-office | portrait `alt="NAME Secretary of State"` |
| ND | Superintendent of Public Instruction | https://www.nd.gov/dpi/state-superintendent | portrait `alt="North Dakota State Superintendent NAME"` |
| ND | Treasurer | https://www.treasurer.nd.gov/ | slider button `Meet NAME, State Treasurer` |
| ND | Commissioner of Agriculture | https://www.ndda.nd.gov/divisions/office-agriculture-commissioner | portrait `alt="NAME, Agriculture Commissioner"` |
| OH | Lieutenant Governor, Attorney General, Auditor, Secretary of State, Treasurer | https://ohio.gov/government/elected-officials | bio tile `<h3 class="… oh-bio__name …">TITLE NAME</h3>` |
| OK | Lieutenant Governor | https://oklahoma.gov/ltgovpinnell.html | `<title>Lieutenant Governor NAME (440)</title>` |
| OK | Attorney General | https://oklahoma.gov/oag.html | menu description `Learn about Oklahoma Attorney General NAME — …` |
| OK | Treasurer | https://oklahoma.gov/treasurer/inside-the-office/staff-directory.html | portrait `alt="NAME - Oklahoma State Treasurer"` |
| OK | Auditor | https://www.sai.ok.gov/ | hero `<strong>NAME, CPA</strong>` under "Oklahoma State Auditor & Inspector" |
| OK | Superintendent of Public Instruction | https://oklahoma.gov/education/state-board-of-education/superintendent-.html | portrait `alt="Photo of Superintendent NAME"` |
| OK | Commissioner of Labor | https://oklahoma.gov/labor.html | portrait `alt="Commissioner NAME, Oklahoma Department of Labor"` |
| OK | Insurance Commissioner | https://www.oid.ok.gov/ | button `Meet Insurance Commissioner NAME` |
| OK | Corporation Commissioner (3) | https://oklahoma.gov/occ.html | commissioner cards `<p>CHAIRMAN\|VICE CHAIRMAN\|COMMISSIONER</p> <h2>NAME</h2>` |
| OR | Secretary of State | https://sos.oregon.gov/Pages/default.aspx | `alt="Oregon Secretary of State, NAME"` |
| OR | Treasurer | https://www.oregon.gov/treasury/Pages/About-Treasurer-Steiner.aspx | `<h1>About Treasurer …</h1> <i>NAME is Oregon's Nth Treasurer.` |
| OR | Attorney General | https://www.doj.state.or.us/ | `<meta name="description" content="Attorney General NAME">` |
| OR | Commissioner of Labor | https://www.oregon.gov/boli/about/Pages/default.aspx | `Learn more about Labor Commissioner NAME` |

## Not collected

Each office in `BLOCKED` is `not-collected`, with a blocker naming the URL and the refusal:

- MS Secretary of State, MT Secretary of State, NV Secretary of State, NM Attorney General: bot challenge or firewall page.
- NH Executive Council (5 councilors): Access Denied.
- NY Lieutenant Governor: the governor's site returns "Access denied" for its lieutenant governor page, and no other page there names the officeholder.

They are never filled from another publisher. North Dakota's Tax Commissioner is elected but has no office key in `tools/statewide.py`, so it is not declared.

## Live check, November 2026

Every source in `SOURCES` was fetched with `build.fetch(..., user_agent=USER_AGENT)` and parsed by `parse` in November 2026; each rule produced exactly the expected number of names.

## Tests

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_statewide_c.py'
```
