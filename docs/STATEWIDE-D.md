# Statewide executive officers: PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY

`tools/regions/statewide_d.py` collects every elected statewide executive officer other than the governor in these thirteen states. Governors are collected by `tools/regions/executive.py` ([EXECUTIVE.md](EXECUTIVE.md)). The module follows the interface in `tools/statewide.py`: `STATEWIDE`, `SOURCES`, `USER_AGENT`, `collect` and `parse`.

## Rules

- Sources are official state pages only. Where a state publishes one page listing its statewide elected officers, that page is used: RI.gov, SC.gov, the South Dakota Secretary of State, and the Wisconsin Board of Commissioners of Public Lands for its three constitutional-officer members. Otherwise the source is the office's own website.
- Each rule in `RULES` names one element: a page `<title>`, heading, meta tag, image `alt`, or menu link. Its pattern runs on the HTML-unescaped page with whitespace collapsed and zero-width characters removed. The pattern must produce exactly the expected number of distinct names: one for a single-holder office, and three for the Texas Railroad Commission and the South Dakota Public Utilities Commission. Zero matches, extra names or conflicting names stop the build.
- A name must have two to five words, ignoring a trailing `, Jr.`, and must not contain an office word such as `Office`, `Secretary`, `Treasurer`, `Commissioner`, `State`, `About` or `Biography`.
- Rows carry `office` set to the shared vocabulary title (`tools/statewide.py` `OFFICES`), `body: "<State> Executive"` and `level: "state"`. Where the source is the office's own site, `website` is set to that page. Rows from list pages (RI, SC, SD, WI BCPL) have no `website`. Party, contact details and term dates are not recorded.
- IDs are `<st>-<officeKey>`. Multi-member commissions use `<st>-<officeKey>-<n>`, numbered in page order.
- HTTP requests use `USER_AGENT` (`Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)`). No source needs a browser capture (`BROWSER` is empty).

### After the November 3, 2026 election

Each source shows the officeholder its publisher currently presents. These offices change hands in January 2027 or later, on dates each state sets. An officeholder-elect is not recorded until the official source shows that person in office. None of the November 2026 sources named an officeholder-elect.

## Which offices are elected

Only offices chosen by statewide popular vote are declared. Offices filled by appointment or by the legislature are left out.

| State | Elected statewide (besides governor) | Official basis | Not elected statewide |
|---|---|---|---|
| PA | Lieutenant Governor, Attorney General, Auditor General, State Treasurer | Pa. Const. art. IV §§ 4, 4.1, 18 ([palegis.us](https://www.palegis.us/statutes/consolidated/view-statute?txtType=HTM&ttl=00&div=0&chapter=4&iFrame=true)) | Secretary of the Commonwealth, Secretary of Education (appointed) |
| RI | Lieutenant Governor, Secretary of State, Attorney General, General Treasurer | RI.gov "Rhode Island Elected Officials" ([ri.gov/officials](https://www.ri.gov/officials/)) | |
| SC | Lieutenant Governor, Secretary of State, Attorney General, Treasurer, Comptroller General, Superintendent of Education, Commissioner of Agriculture | S.C. Const. art. VI § 7 ([scstatehouse.gov A06.pdf](https://www.scstatehouse.gov/scconstitution/A06.pdf)); art. IV for the lieutenant governor | Adjutant General (appointed under the amended art. VI § 7) |
| SD | Lieutenant Governor, Secretary of State, Attorney General, State Auditor, State Treasurer, Commissioner of School and Public Lands, Public Utilities Commissioners (3) | South Dakota Secretary of State "Current Elected Officials" | |
| TN | None | Tennessee Secretary of State: the secretary of state is elected by the General Assembly ([sos.tn.gov](https://sos.tn.gov/)); Tenn. Const. art. III § 17 and art. VII § 3 (secretary of state, treasurer, comptroller chosen by the General Assembly); the Speaker of the Senate is lieutenant governor | All non-governor constitutional officers |
| TX | Lieutenant Governor, Attorney General, Comptroller of Public Accounts, Commissioner of the General Land Office, Commissioner of Agriculture, Railroad Commissioners (3) | Texas Secretary of State "Statewide Elected Officials", column "Elected or Appointed" = E ([sos.state.tx.us](https://www.sos.state.tx.us/elections/voter/elected.shtml)). Its officeholder names are out of date and are not used. | Secretary of State (appointed). State Board of Education members are elected by district, not statewide. |
| UT | Lieutenant Governor, Attorney General, State Auditor, State Treasurer | Utah Const. art. VII § 1, "elective constitutional officers" ([le.utah.gov](https://le.utah.gov/xcode/ArticleVII/UC_AVII_S1_1800010118000101.html)) | |
| VT | Lieutenant Governor, Secretary of State, Treasurer, Auditor of Accounts, Attorney General | Vt. Const. ch. II § 43 ([legislature.vermont.gov](https://legislature.vermont.gov/statutes/constitution-of-the-state-of-vermont/)); 3 V.S.A. § 151 for the Attorney General ([legislature.vermont.gov](https://legislature.vermont.gov/statutes/section/03/007/00151)) | |
| VA | Lieutenant Governor, Attorney General | Va. Const. art. V §§ 13, 15 ([law.lis.virginia.gov](https://law.lis.virginia.gov/constitution/article5/section15/)) | Secretary of the Commonwealth, Treasurer (appointed) |
| WA | Lieutenant Governor, Secretary of State, Treasurer, Auditor, Attorney General, Commissioner of Public Lands, Superintendent of Public Instruction, Insurance Commissioner | Wash. Const. art. III § 1 ([leg.wa.gov](https://leg.wa.gov/state-laws-and-rules/washington-state-constitution/)); RCW 48.02.010 for the Insurance Commissioner ([app.leg.wa.gov](https://app.leg.wa.gov/RCW/default.aspx?cite=48.02.010)) | |
| WV | Secretary of State, Attorney General, Treasurer, Auditor, Commissioner of Agriculture | W. Va. Const. art. VII § 1 (cited, not fetched in this run) | Lieutenant governor: the Senate President holds the title by statute. State Superintendent of Schools is appointed by the Board of Education. The Board of Public Works page includes the superintendent, but that page does not establish election. |
| WI | Lieutenant Governor, Secretary of State, State Treasurer, Attorney General, State Superintendent of Public Instruction | Wis. Const. art. V § 1, art. VI § 1, art. X § 1 ([docs.legis.wisconsin.gov](https://docs.legis.wisconsin.gov/constitution/wi); article text did not render over plain HTTP in this run) | |
| WY | Secretary of State, State Auditor, State Treasurer, Superintendent of Public Instruction | Wyo. Const. art. IV § 11 (cited, not fetched in this run) | Attorney General (appointed by the governor). Wyoming has no lieutenant governor. |

## Vocabulary mapping

Rows use the shared titles. The official titles map to the shared keys as follows:

- Auditor General (PA), Auditor of Accounts (VT) and State Auditor map to `auditor`.
- Comptroller General (SC) and Comptroller of Public Accounts (TX) map to `comptroller`.
- General Treasurer (RI) and State Treasurer map to `treasurer`.
- State Superintendent of Education (SC) maps to `superintendentOfPublicInstruction`.
- Commissioner of the General Land Office (TX), Commissioner of School and Public Lands (SD) and Commissioner of Public Lands (WA) map to `landCommissioner`.
- South Dakota Public Utilities Commissioner maps to `publicServiceCommissioner`.
- Commissioner, Railroad Commission of Texas maps to `railroadCommissioner`.

## Sources and elements

All offices below were collected and parsed live on 2026-11-10. There are no blockers.

| State | Office | Source | Element read |
|---|---|---|---|
| PA | Lieutenant Governor | https://www.pa.gov/ltgovernor | `<meta name="copapwp-page-title" content="…">` |
| PA | Attorney General | https://www.attorneygeneral.gov/ | header logo `alt="AG …"` |
| PA | Auditor General | https://www.paauditor.gov/ | `img.hero-auditor-img alt="PA Auditor General …"` |
| PA | Treasurer | https://www.patreasury.gov/ | `og:site_name` "Pennsylvania Treasury, … - State Treasurer" |
| RI | Lt. Governor, Secretary of State, Attorney General, General Treasurer | https://www.ri.gov/officials/ | `<h3 class="blue-sub-header">{office}</h3> <h5>…</h5>` |
| SC | Lt. Governor, Secretary of State, Treasurer, Attorney General, Comptroller General, State Superintendent of Education, Commissioner of Agriculture | https://sc.gov/government/getting-know-your-government/elected-officials/constitutional-officers | tile heading `<h3 data-item="0">{office} …</h3>` |
| SD | Lt. Governor, Secretary of State, Attorney General, State Auditor, State Treasurer, Commissioner of School and Public Lands, Public Utilities Commissioner ×3 | https://sdsos.gov/elections-voting/election-resources/current-elected-officials.aspx | `<p><strong>{office} … (R)</strong>` (the party letter ends the name) |
| TX | Lieutenant Governor | https://www.ltgov.texas.gov/ | `<title>Home - Lieutenant Governor …</title>` |
| TX | Attorney General | https://www.texasattorneygeneral.gov/about-office | meta description "… is the 51st Attorney General of Texas." |
| TX | Comptroller | https://comptroller.texas.gov/about/bio.php | `<title>… - Texas Comptroller of Public Accounts</title>` |
| TX | Land Commissioner | https://www.glo.texas.gov/ | header `<span class='d-block show-for-large'>Commissioner …, M.D.</span>` |
| TX | Agriculture Commissioner | https://texasagriculture.gov/ | `alt="Texas Agriculture Commissioner …"` |
| TX | Railroad Commissioners ×3 | https://www.rrc.texas.gov/about-us/commissioners/ | `<h4>…</h4> <h5>Chairman|Commissioner</h5>` |
| UT | Lieutenant Governor | https://ltgovernor.utah.gov/ | `<title>Home - Lt. Governor …</title>` |
| UT | Attorney General | https://attorneygeneral.utah.gov/ | heading after the "Utah Attorney General" heading |
| UT | State Auditor | https://auditor.utah.gov/ | menu link `Meet Auditor …` |
| UT | State Treasurer | https://treasurer.utah.gov/ | menu link `State Treasurer …` (not the logo `alt`, which names a former treasurer) |
| VT | Lieutenant Governor | https://ltgov.vermont.gov/ | `<img alt="Lieutenant Governor ….">` |
| VT | Secretary of State | https://sos.vermont.gov/secretarys-desk | `<p><strong>…, Secretary of State</strong></p>` |
| VT | Treasurer | https://www.vermonttreasurer.gov/ | `<h1>` "Welcome to the Office of Vermont State Treasurer …" |
| VT | Auditor of Accounts | https://auditor.vermont.gov/about-us/biographies | `<h3>State Auditor …, J.D.</h3>` |
| VT | Attorney General | https://ago.vermont.gov/ | `<span class="usa-logo__slogan">…</span>` beside the site name |
| VA | Lieutenant Governor | https://www.ltgov.virginia.gov/ | site branding after `<span class="office-name">Lieutenant Governor of Virginia</span>` |
| VA | Attorney General | https://www.oag.state.va.us/ | `twitter:title` "Attorney General …" |
| WA | Lieutenant Governor | https://www.ltgov.wa.gov/ | `<title>Lieutenant Governor …</title>` |
| WA | Secretary of State | https://www.sos.wa.gov/ | link "Secretary of State … Biography" |
| WA | Treasurer | https://tre.wa.gov/ | logo `alt="Washington State Treasurer - …"` |
| WA | Auditor | https://sao.wa.gov/ | link `title="State Auditor …"` |
| WA | Attorney General | https://www.atg.wa.gov/ | block `displayspresentattorneygeneralname` |
| WA | Commissioner of Public Lands | https://dnr.wa.gov/ | body after `<h2>Commissioner of Public Lands</h2>`: "Commissioner … is" |
| WA | Superintendent of Public Instruction | https://ospi.k12.wa.us/ | menu link "Superintendent …" |
| WA | Insurance Commissioner | https://www.insurance.wa.gov/ | menu link "About …" under `/about-us/` |
| WV | Secretary of State | https://sos.wv.gov/about-secretary | `<h2>…</h2><h3>West Virginia's 31st Secretary of State</h3>` |
| WV | Attorney General | https://ago.wv.gov/ | `<title>Office of the WV Attorney General …</title>` |
| WV | Treasurer | https://wvtreasury.gov/ | header `div.tname` beside `div.ttitle` "West Virginia State Treasurer" |
| WV | Auditor | https://www.wvsao.gov/ | header "Auditor …" under "West Virginia State Auditor's Office" |
| WV | Commissioner of Agriculture | https://agriculture.wv.gov/ | hidden `<h1>` "West Virginia Department of Agriculture, …, Commissioner" |
| WI | Lieutenant Governor | https://evers.wi.gov/ltgov/Pages/default.aspx | logo `alt="Lieutenant Governor …"` |
| WI | Secretary of State, State Treasurer, Attorney General | https://bcpl.wisconsin.gov/Pages/AboutBCPL.aspx | board-member `<figcaption> <h3>…</h3>{office}</figcaption>` |
| WI | Superintendent of Public Instruction | https://dpi.wi.gov/ | photo `alt` in the "State Superintendent of Public Instruction" widget |
| WY | Secretary of State | https://sos.wyo.gov/AboutUs/AboutSecretary.aspx | headshot `alt="…, Wyoming Secretary of State"` |
| WY | State Auditor | https://sao.wyo.gov/ | `<h4>…</h4> <h5>State Auditor</h5>` |
| WY | State Treasurer | https://statetreasurer.wyo.gov/ | intro image `alt` |
| WY | Superintendent of Public Instruction | https://edu.wyoming.gov/ | headshot `alt="Headshot of …, Wyoming Superintendent of Public Instruction"` |

### Source notes

- **Redirects.** `build.fetch` rejects a redirect to another host, so the module requests the final host directly:
  - `evers.wi.gov/ltgov`, not `ltgov.wisconsin.gov`
  - `wvtreasury.gov`, not `wvtreasury.com`
  - `wisdoj.gov`, not `doj.state.wi.us` (the Wisconsin attorney general is read from BCPL instead)
- **Rhode Island.** The lieutenant governor, attorney general and treasurer sites returned a bot challenge (HTTP 403, "Just a moment...") to `USER_AGENT`. The state portal `ri.gov/officials/` lists all four officers over plain HTTP and is used instead. It is also a State of Rhode Island page, so no third party is involved.
- **South Carolina.** `ltgov.sc.gov` accepted no connection. The SC.gov constitutional-officers page lists all seven officers.
- **South Dakota.** The Secretary of State page also lists congressional and judicial officers. Some of those entries are out of date, for example a retired justice. Only the state executive entries are read. Their section reflects the January 2025 succession (Governor Rhoden, Lt. Governor Venhuizen).
- **Texas Comptroller.** The comptroller's biography says the governor appointed Don Huffines and he was sworn in on August 1, 2026. He is recorded as the sitting comptroller. The office remains elected.
- **Utah Treasurer.** The site logo's `alt` text still names a former treasurer, so the rule reads the "State Treasurer …" menu link instead.
- **Wisconsin.** The DOJ homepage photo `alt` misspells the attorney general's name, and the Secretary of State's biography splits the surname across `<span>` elements. The BCPL board page names all three officers cleanly.

## Coverage notes for integration

- Tennessee is declared as `{}` because it elects no non-governor statewide executive officer. `build.state_executive` currently lists `otherStatewideOffices` as not collected for any state whose declaration is empty. For Tennessee that label would be wrong.

## Tests

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_statewide_d.py'
```
