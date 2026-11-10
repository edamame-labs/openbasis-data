# Statewide executive offices: AL AK AZ AR CA CO CT DE FL GA HI

`tools/regions/statewide_a.py` collects every elected statewide executive officeholder other than the governor in Alabama, Alaska, Arizona, Arkansas, California, Colorado, Connecticut, Delaware, Florida, Georgia and Hawaii. Governors come from `tools/regions/executive.py`. The office vocabulary and the module interface are in `tools/statewide.py`.

## Extraction rules

- Each source is one official state page. Arkansas, Colorado, Delaware and Georgia publish one state page that lists the statewide officials. The other states' offices are read from each office's own website.
- A rule runs a pattern on the page after HTML entities are unescaped, HTML comments are removed and whitespace is collapsed. Each pattern names one element per officeholder: a `<title>`, a heading, a meta tag, an image caption or a menu link.
- Every pattern must match. On state list pages, every matched office title must be a known title. The governor's entry is read but not published. An unknown title stops the build.
- Each office must yield exactly its expected number of distinct holders: one for a single-holder office, or the full membership of a multi-member body. Two different names for one office, a missing member, or two holders for one district all stop the build. The same name repeated in several menus counts as one record.
- Names must have two to six words and must not contain office words such as `Office`, `Commissioner` or `State`. Trailing academic or professional suffixes (`Ph.D.`, `Ed.D.`, `M.D.`, `CPA`) are dropped. Generational suffixes such as `Jr` are kept.
- Records carry `office` (the vocabulary title), `body: "<State> Executive"`, `level: "state"`, `website` set to the source page and, for district-elected boards, `district` (a number, or `At-Large`). Ids are `<st>-<officeKey>`, with `-<n>` added for multi-member offices, numbered in page order. Party, contact details and term dates are not read.
- Requests use the shared `USER_AGENT` and go through `build.fetch`. Two pages are requested at their final hostnames, `ed.cde.state.co.us` and `regents.cu.edu`, because the shorter URLs redirect to another hostname and `build.fetch` rejects cross-host redirects.

## Incumbents and the November 2026 election

Each rule reads the officeholder its page shows as serving. No rule reads election results. The terms of officers elected on November 3, 2026 begin after this collection date. The constitution texts read for this module give these start dates: Alaska and Hawaii at noon on the first Monday in December (December 7, 2026), Arizona on the first Monday of January, and Florida on the first Tuesday after the first Monday in January. All pages showed incumbents when they were retrieved on November 10, 2026. A page that switched to an officeholder-elect before the term began would change the record, so review refreshes made between the election and the term start.

**Arizona Lieutenant Governor.** Arizona Constitution Article 5 §1 (as amended; [azleg.gov/const/5/1.htm](https://www.azleg.gov/const/5/1.htm)) creates a lieutenant governor elected jointly with the governor. The first lieutenant governor was elected in November 2026 and takes office on the first Monday of January 2027, so the office has no holder yet and is not declared. Add it after that term begins.

## Sources

| State | Office | Source | Element read |
|---|---|---|---|
| AL | Lieutenant Governor | https://ltgov.alabama.gov/ | `og:site_name` "Lt. Governor …" |
| AL | Secretary of State | https://www.sos.alabama.gov/ | banner `span.banner-body` after the h1 "Official Website of the Alabama Secretary of State" |
| AL | Attorney General | https://www.alabamaag.gov/ | meta description "… was sworn in as the … Attorney General of the State of Alabama" |
| AL | Treasurer | https://treasury.alabama.gov/ | `og:site_name` "Office of the Alabama State Treasurer - …" |
| AL | Auditor | https://auditor.alabama.gov/ | signed quote "- …, State Auditor" |
| AL | Commissioner of Agriculture and Industries | https://agi.alabama.gov/ | `h3.section-title` "Meet Commissioner …" |
| AL | Public Service Commission (3) | https://psc.alabama.gov/ | image captions "Commissioner …, President / Place One / Place Two" |
| AK | Lieutenant Governor | https://ltgov.alaska.gov/ | menu link "Meet Lt. Governor …" |
| AZ | Attorney General | https://www.azag.gov/ | menu link "…, Attorney General" |
| AZ | Treasurer | https://www.aztreasury.gov/ | "The Honorable … serves as the NNth Treasurer of Arizona." |
| AZ | Corporation Commission (5) | https://www.azcc.gov/ | "Commissioners" menu: `a.dropdown-item` links to `/…/biography` |
| AZ | Secretary of State | https://azsos.gov/ | **not collected**: HTTP 403 with a Cloudflare challenge |
| AZ | Superintendent of Public Instruction | https://www.azed.gov/ | **not collected**: HTTP 403 with a Cloudflare challenge |
| AZ | Mine Inspector | https://asmi.az.gov/ | **not collected**: HTTP 403 with a Cloudflare challenge |
| AR | Lt. Governor, Secretary of State, Attorney General, Treasurer, Auditor, Land Commissioner | https://portal.arkansas.gov/elected-officials/ | in the "Elected Officials for the State of Arkansas" section (before "Federal Elected Officials"): an office-title `p.elementor-heading-title` followed by the name `h3.elementor-heading-title` |
| CA | Lieutenant Governor | https://ltg.ca.gov/about/ | `<title>` "About … - Lieutenant Governor" |
| CA | Secretary of State | https://www.sos.ca.gov/ | `#header-name` after `#header-office` "California Secretary of State" |
| CA | Attorney General | https://oag.ca.gov/about | `h1.page-header` "Attorney General …" |
| CA | Treasurer | https://www.treasurer.ca.gov/bio | "… is California's NNth State Treasurer." |
| CA | Insurance Commissioner | https://www.insurance.ca.gov/0500-about-us/ | "Information about Commissioner …" |
| CA | Controller | https://www.boe.ca.gov/ | the Board of Equalization member card labelled "Controller" (the Controller is an ex officio BOE member). The Controller's own site, sco.ca.gov, answered `USER_AGENT` with HTTP 403 and a Cloudflare challenge. |
| CA | Superintendent of Public Instruction | https://www.cde.ca.gov/ | **not collected**: cde.ca.gov answered with a Radware bot-manager captcha page |
| CO | Lt. Governor, Attorney General, Secretary of State, Treasurer | https://www.colorado.gov/ | the portal's footer "Government" block (`#block-footergovernment`), which must appear once: links "Lt. Governor …", "Attorney General …", "Secretary of State …", "State Treasurer …" |
| CT | Lieutenant Governor | https://portal.ct.gov/lt-governor | `<title>` "Lieutenant Governor … \| Office of the Lieutenant Governor \| CT.GOV" |
| CT | Secretary of the State | https://portal.ct.gov/sots | `h2.cg-c-section-title` "Secretary of the State …" |
| CT | Attorney General | https://portal.ct.gov/ag/about-the-ag/william-tong-biography-page | h1 "Attorney General …". This page is the target of the AG homepage's "About the Attorney General" link, and its URL names the officeholder: when the office changes hands, the fetch fails and the rule needs review. |
| CT | Treasurer | https://portal.ct.gov/ott | `<title>` "Connecticut Office of the Treasurer …" |
| CT | Comptroller | https://osc.ct.gov/ | bio card `h5` "Comptroller …" |
| DE | Lt. Governor, Attorney General, Auditor, Insurance Commissioner, Treasurer | https://delaware.gov/guides/your-government/ | "State elected officials" cards: `h5` link to `*.delaware.gov` "Title Name" |
| FL | Lieutenant Governor | https://www.flgov.com/eog/leadership/people/jay-collins | `div.administration` h2 "Lieutenant Governor …" followed by "… – Present". This page is the target of the EOG site's "Lieutenant Governor" menu link, and its URL names the officeholder. |
| FL | Attorney General | https://www.myfloridalegal.com/ | menu link to `/ag-bio` "Attorney General …" |
| FL | Commissioner of Agriculture | https://www.fdacs.gov/ | link to `/About-Us/Meet-Commissioner-…` "Learn More About Commissioner …" |
| GA | Lt. Governor, Attorney General, Secretary of State, School Superintendent, Agriculture, Insurance, Labor, Public Service Commission (5) | https://georgia.gov/elected-officials | `h2.global-teaser__title` (name) + `p.global-teaser__description` (office title). "Public Service Commission Chairman" and "Public Service Commissioner" both map to `publicServiceCommissioner`. |
| HI | Lieutenant Governor | https://ltgov.hawaii.gov/ | `<title>` "Lieutenant Governor …" |

## Which offices are elected

Offices filled by appointment are left out entirely. The list pages used here are the state's own lists of elected officials (Arkansas "Elected Officials for the State of Arkansas", Delaware "State elected officials", Georgia "Elected Officials"). Constitution texts were read for these states:

- **Alaska**: Article III ([ltgov.alaska.gov](https://ltgov.alaska.gov/information/alaskas-constitution/)). The lieutenant governor is elected jointly with the governor. Heads of principal departments, including the attorney general's department, are appointed by the governor. The only declared office is the lieutenant governor.
- **Arizona**: Article 5 §1 (governor, lieutenant governor, secretary of state, attorney general, treasurer, superintendent of public instruction) and Article 15 (Corporation Commission, elected). The mine inspector is declared under Article 19. That text was not retrieved at the URL tried, and the inspector's own site is blocked, so this declaration needs confirming from an official source.
- **California**: the Secretary of State's California Roster, "Constitutional Officers" ([PDF](https://admin.cdn.sos.ca.gov/ca-roster/2022/constitutional-officers.pdf)), lists eight elected statewide constitutional officers: Governor, Lieutenant Governor, Secretary of State, Attorney General, Controller, Treasurer, Insurance Commissioner and Superintendent of Public Instruction. The Board of Equalization's four members are elected by district.
- **Florida**: Article IV §4–5 ([flsenate.gov](https://www.flsenate.gov/Laws/Constitution)). The cabinet (attorney general, chief financial officer, commissioner of agriculture) and the lieutenant governor are elected. The secretary of state is appointed and is not declared.
- **Hawaii**: Article V §2 ([lrb.hawaii.gov](https://lrb.hawaii.gov/constitution/)) for the lieutenant governor, and Article XII §5 for the Office of Hawaiian Affairs trustees (see below).
- **Colorado**: the State Board of Education page says the board is "composed of nine elected officials representing Colorado's congressional districts". The Regents page says one regent is elected from each congressional district and one from the state at large.

For Alabama, Connecticut and Colorado's executive officers, no constitution text was retrieved. Their declarations follow the offices' own official sites and need confirming against constitution text.

The Delaware secretary of state, the Florida secretary of state and the Alaska attorney general are appointed, so they are not declared.

## Elected offices without a vocabulary key (not declared)

- **Florida Chief Financial Officer**: an elected cabinet officer (Florida Constitution Article IV §4). Source: https://www.myfloridacfo.com/. The homepage text includes "CFO Blaise Ingoglia", but no rule has been written for it yet. Needs a key such as `chiefFinancialOfficer`.
- **Hawaii Office of Hawaiian Affairs trustees**: a board of at least nine elected trustees (Hawaii Constitution Article XII §5). Needs a key such as `officeOfHawaiianAffairsTrustee` (multi-member). Not collected in this module.

## Blockers

| State | Office | Blocker |
|---|---|---|
| AZ | Secretary of State | azsos.gov answered `USER_AGENT` with HTTP 403 and a Cloudflare challenge page (Nov 2026) |
| AZ | Superintendent of Public Instruction | azed.gov answered with HTTP 403 and a Cloudflare challenge page |
| AZ | Mine Inspector | asmi.az.gov answered with HTTP 403 and a Cloudflare challenge page |
| CA | Superintendent of Public Instruction | cde.ca.gov answered with a Radware bot-manager captcha page |

These offices are listed in `BLOCKED`, recorded as `not-collected` with the blocker text, and never filled from another publisher. No browser captures are used (`BROWSER` is not declared). A person could capture these pages in a normal browser and import them with `tools/import_snapshot.py`, but that would also tie the module to 24-hour browser evidence for each publication.

## Tests

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_statewide_a.py'
```

The tests use fixtures to cover: title extraction across whitespace and entities, title-to-office mapping with the governor skipped, an unknown title, a missing office, a wrong member count, a missing marker, conflicting names, placeholder text, a duplicated page block, district normalization, suffix removal, two holders for one seat, and the module's declarations and discovery by `build.py`. Each rule was also checked live on November 10, 2026 with `build.fetch(key, publisher, url, user_agent=USER_AGENT)` followed by `parse`. All 33 sources parsed, giving 89 records.

## Scope: district-elected boards

Boards whose members are elected by district are outside statewide scope (see `tools/statewide.py`): the Alabama and Colorado State Boards of Education, the California Board of Equalization, and the University of Colorado Regents. A district seat belongs to that district's residents, and the districts' boundaries are not published here.
