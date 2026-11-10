# Statewide executive officers: ID, IL, IN, IA, KS, KY, LA, ME, MD, MA, MI, MN

`tools/regions/statewide_b.py` collects every statewide executive officer other than the governor that voters in these states elect statewide. Governors come from `tools/regions/executive.py`. Office keys and titles come from `tools/statewide.py`.

## Inclusion rule

An office is declared only if voters elect it statewide. These are left out:

- officers chosen by the legislature: Maine's Secretary of State, Treasurer, Attorney General and State Auditor, and Maryland's State Treasurer;
- appointed officers, for example Maryland's Secretary of State and Indiana's Secretary of Education, which replaced the elected Superintendent of Public Instruction in 2025;
- boards elected from districts rather than statewide: the Kansas State Board of Education, Louisiana's Board of Elementary and Secondary Education and Public Service Commission, and the Massachusetts Governor's Council.

Which offices are elected was taken from these official state sources:

| State | Source for which offices are elected |
|---|---|
| ID | Idaho Secretary of State, [Idaho Elected Officials](https://voteidaho.gov/idaho-elected-officials/) (the source of the rows too) |
| IL | [illinois.gov Executive Branch](https://www.illinois.gov/government/executive-branch.html): six elected officers |
| IN | Indiana Constitution art. 5 §§1–3 (Governor and Lieutenant Governor) and art. 6 §1 (Secretary, Auditor, Treasurer of State, elected by the voters); the Attorney General is elected under IC 4-6-1-2. The Auditor of State is now titled State Comptroller ([in.gov/comptroller](https://www.in.gov/comptroller/)) |
| IA | [Iowa Code §39.9](https://www.legis.iowa.gov/docs/code/39.9.pdf): governor, lieutenant governor, secretary of state, auditor of state, treasurer of state, secretary of agriculture and attorney general are elected |
| KS | State of Kansas portal, [Elected State Officials](https://portal.kansas.gov/government/) (the source of the rows too) |
| KY | [Kentucky Constitution §91](https://apps.legislature.ky.gov/law/constitution/Constitution/ViewConstitution?rsn=91) and §70 |
| LA | [louisiana.gov Executive Branch Elected Officials](https://louisiana.gov/government/executive-branch-elected-officials): six statewide elected officials besides the governor; BESE and PSC members are elected from districts |
| ME | Maine Secretary of State, [Maine State Government](https://www.maine.gov/sos/kids/government/state-government): the three constitutional officers and the statutory State Auditor are elected by the Legislature in joint convention. Maine has no lieutenant governor |
| MD | Maryland Manual, [Maryland at a Glance: Government](https://msa.maryland.gov/msa/mdmanual/01glance/html/mdgovt.html): voters elect the Comptroller and Attorney General, the Lieutenant Governor runs on a joint ticket, and the General Assembly selects the Treasurer |
| MA | [Massachusetts Constitution](https://malegislature.gov/Laws/Constitution) (Articles of Amendment LXIV, XVII): Lieutenant Governor, Secretary, Treasurer and Receiver General, Auditor, Attorney General |
| MI | [Michigan Constitution art. V §21](https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-Article-V-21) (Lieutenant Governor, Secretary of State, Attorney General) and art. VIII §§3, 5 (State Board of Education; University of Michigan Regents, Michigan State University Trustees, Wayne State University Governors, all elected statewide) |
| MN | [Minnesota Constitution art. V §1](https://www.revisor.mn.gov/constitution/#article_5): governor, lieutenant governor, secretary of state, auditor and attorney general, chosen by the electors |

## Sources and extraction

Each rule names one element that identifies the officeholder. Its pattern runs on the HTML-unescaped page, with zero-width characters (U+200B–U+200D, U+FEFF) removed and whitespace collapsed. A pattern must match at least once and produce exactly one distinct officeholder. Zero matches, or two different names, stop the build. A name must have two to five words and must not contain words such as `Office`, `Governor`, `State`, `General`, `Treasurer` or `Commissioner`. Rows carry `office` set to the vocabulary title, `body: "<State> Executive"` and `level: "state"`. `website` is the office link from the list page (Idaho, Kansas), or otherwise the source page. `party` is set only where the source element gives it: Idaho `(R)`/`(D)` is mapped to Republican/Democratic, and the Minnesota LRL party column is copied as written. HTTP requests use `USER_AGENT`.

| State | Office (key) | Source | Element read | Status |
|---|---|---|---|---|
| ID | lieutenantGovernor, secretaryOfState, attorneyGeneral, controller, treasurer, superintendentOfPublicInstruction | https://voteidaho.gov/idaho-elected-officials/ | `<p><strong>{office label}</strong></p>` followed by `<h3 class="elementor-heading-title …">Name (P)</h3>` and the card's external link | collected |
| IL | lieutenantGovernor | https://ltgov.illinois.gov/ | `<h1 class="cmp-title__text"> Lieutenant Governor Name</h1>` | collected |
| IL | attorneyGeneral | https://illinoisattorneygeneral.gov/ | `<title>Office of the Illinois Attorney General Name</title>` | collected |
| IL | secretaryOfState | https://www.ilsos.gov/ | — | not-collected: every request had its HTTP/2 stream reset, and HTTP/1.1 timed out |
| IL | comptroller | https://illinoiscomptroller.gov/ | `<title>Name – Illinois State Comptroller - The Illinois Office of Comptroller</title>` | collected |
| IL | treasurer | https://illinoistreasurer.gov/ | `<title>Illinois State Treasurer Name: …` | collected |
| IN | lieutenantGovernor | https://www.in.gov/lg/ | `<title>Lieutenant Governor Name: Home</title>` | collected |
| IN | secretaryOfState | https://www.in.gov/sos/ | `<h1>Welcome to the Office of Secretary of State Name</h1>` | collected |
| IN | attorneyGeneral | https://www.in.gov/attorneygeneral/ | `<h1>Attorney General Name</h1>` | collected |
| IN | comptroller | https://www.in.gov/comptroller/ | `<h1 >Indiana State Comptroller Name</h1>` | collected |
| IN | treasurer | https://www.in.gov/tos/ | `<h2>Welcome to the Office of Treasurer Name</h2>` | collected |
| IA | lieutenantGovernor | https://governor.iowa.gov/ | `alt="Lt. Governor Name headshot"` | collected |
| IA | secretaryOfState | https://sos.iowa.gov/ | — | not-collected: Cloudflare challenge (HTTP 403) |
| IA | attorneyGeneral | https://www.iowaattorneygeneral.gov/ | `<h2>Name</h2> <p>Iowa Attorney General</p>` | collected |
| IA | auditor | https://www.auditor.iowa.gov/ | `<div class="logo-text">IOWA AUDITOR OF STATE<br>Name</div>` | collected |
| IA | treasurer | https://www.iowatreasurer.gov/ | `<p>Hi – I’m Name, Iowa’s State Treasurer.` | collected |
| IA | agricultureCommissioner | https://iowaagriculture.gov/ | mega-menu link `Secretary of Agriculture Name </a>` | collected (title in source: Secretary of Agriculture) |
| KS | lieutenantGovernor, secretaryOfState, treasurer, attorneyGeneral, insuranceCommissioner | https://portal.kansas.gov/government/ | "Elected State Officials" cards: `<a class="elementor-cta" href=…>` … `elementor-cta__title` Name, then `elementor-cta__description` office | collected |
| KY | lieutenantGovernor | https://governor.ky.gov/ | `<h2 class="bottom"><small>LIEUTENANT GOVERNOR</small>Name</h2>` | collected |
| KY | secretaryOfState | https://www.sos.ky.gov/Pages/default.aspx | `<meta name="description" content="Secretary of State Name" />` | collected |
| KY | attorneyGeneral | https://www.ag.ky.gov/Pages/default.aspx | header `Attorney General<br><span class="header-title-name">Name</span>` | collected |
| KY | auditor | https://www.auditor.ky.gov/Pages/index.aspx | header `AUDITOR OF PUBLIC ACCOUNTS<br><span class="header-title-name">Name</span>` | collected |
| KY | treasurer | https://treasury.ky.gov/Pages/index.aspx | `<h2 class="agencyElement-H2-Fancy">A Message from Treasurer Name</h2>` | collected |
| KY | agricultureCommissioner | https://www.kyagr.com/ | logo link to `/commissioner/`, `alt="Commissioner Name"` | collected |
| LA | lieutenantGovernor | https://www.crt.state.la.us/lt-governor/ | `<title>Lt. Governor Name \| State of Louisiana</title>` | collected |
| LA | secretaryOfState | https://www.sos.la.gov/ | menu text `Learn about Louisiana's Secretary of State Name's background and role.` | collected |
| LA | attorneyGeneral | https://www.ag.state.la.us/ | `<h1>Meet Name</h1>` | collected |
| LA | treasurer | https://www.treasury.la.gov/ | `<title>Name, MD Treasurer \| Louisiana State Treasurer \| Louisiana</title>` (the post-nominal is not part of the name) | collected |
| LA | agricultureCommissioner | https://www.ldaf.la.gov/ | `<a href="/about/commissioner" class="usa-link">Commissioner Name</a>` | collected |
| LA | insuranceCommissioner | https://www.ldi.la.gov/ | — | not-collected: bot challenge (HTTP 403) |
| ME | — | — | No statewide-elected officer besides the governor. Declared as `{'blockers': []}` so that coverage reads as complete rather than undeclared | — |
| MD | lieutenantGovernor | https://governor.maryland.gov/leadership/lt-governor | `<h1 id="page-hero" …><span>The Office of Lieutenant Governor Name</span> </h1>` | collected |
| MD | attorneyGeneral | https://oag.maryland.gov/Pages/oag.aspx | masthead `<span>Attorney General of Maryland</span></span> <span class="mdgov-agency__name"><span>Name</span>` | collected |
| MD | comptroller | https://www.marylandcomptroller.gov/ | `<meta name="description" content="… led by Comptroller Name. Working towards …` | collected |
| MA | lieutenantGovernor | https://www.mass.gov/orgs/office-of-the-governor | page-header leadership link to `mass.gov/person/…` whose description is `Lieutenant Governor` | collected |
| MA | secretaryOfState | https://www.sec.state.ma.us/ | — | not-collected: redirects to itself until the redirect limit (needs a cookie session) |
| MA | attorneyGeneral | https://www.mass.gov/orgs/office-of-the-attorney-general | page-header leadership link, description `Attorney General` | collected |
| MA | treasurer | https://www.mass.gov/orgs/office-of-the-treasurer-and-receiver-general | `<h1 class="ma__page-header__title"> Office of State Treasurer and Receiver General Name </h1>` | collected |
| MA | auditor | https://www.mass.gov/orgs/office-of-the-state-auditor | page-header leadership link, description `State Auditor` | collected |
| MI | lieutenantGovernor, secretaryOfState, attorneyGeneral, stateBoardOfEducationMember | https://www.michigan.gov/ (whitmer, sos, ag, mde) | — | not-collected: Access Denied (HTTP 403) |
| MI | universityRegent (University of Michigan Board of Regents) | https://regents.umich.edu/regents/ | — | not-collected: bot challenge (HTTP 403) |
| MN | lieutenantGovernor | https://www.lrl.mn.gov/mngov/ltgov | first row of the table under `</colgroup>`: assumed-office date, name, party | collected |
| MN | secretaryOfState | https://www.lrl.mn.gov/mngov/secstate | first row of the state table (the territorial table has no `<colgroup>`), `Last, First` reordered to `First Last` | collected |
| MN | attorneyGeneral | https://www.ag.state.mn.us/ | `alt="Portrait of Attorney General Name"` | collected |
| MN | auditor | https://www.osa.state.mn.us/ | `<title>Office of the State Auditor Name \| MN Office of the State Auditor (OSA)</title>` | collected |

Some redirecting URLs are recorded at their final address because `build.fetch` refuses a redirect to another host. These are `governor.ky.gov` (not `ltgovernor.ky.gov`), `oag.maryland.gov` (not `marylandattorneygeneral.gov`), `www.ldaf.la.gov` and `portal.kansas.gov`. The Mass.gov governor and treasurer pages redirect within `www.mass.gov` to URLs that carry the officeholder's name. The rules read the requested URL.

The Minnesota Secretary of State (`sos.mn.gov`) and `mn.gov/governor` send automated requests to a Radware bot challenge. Their offices are therefore read from the Minnesota Legislative Reference Library's officer lists. Those lists are historical tables, and the rule takes the most recent row. The rule also checks that the row's assumed-office date is not after the retrieval date, so a successor-elect listed early stops the build instead of replacing the incumbent.

The Massachusetts Attorney General page's meta description still names a former Attorney General. The rule therefore reads the page-header leadership link, not the description.

## Officeholders after the November 2026 election

These pages were read on 2026-11-09, after the November 3 general election. Each shows the sitting officeholder. Officers-elect take office on dates set by each state, mostly in January 2027. Until a source changes, the record names the incumbent, and the record does not establish a term end.

## Not covered by the vocabulary

Michigan State University's Board of Trustees and Wayne State University's Board of Governors are elected statewide (Mich. Const. art. VIII §5). They are not declared because `tools/statewide.py` has no key for them. `universityRegent` is used only for the University of Michigan Board of Regents. Their official pages were readable: https://trustees.msu.edu/ and https://bog.wayne.edu/.

## Refreshing

Live-check each source without running the full build:

```
cd tools && ../.venv-geo/bin/python -B -c "
import build; from regions import statewide_b as m
for k,(p,u) in m.SOURCES.items():
    raw,src=build.fetch(k,p,u,user_agent=m.USER_AGENT); print([(r['state'],r['office'],r['name']) for r in m.parse(k,raw,src)])"
```

A rule that stops after a page redesign or a change of officeholder needs review against the page. It is never relaxed until it passes. A source that refuses retrieval is moved to `BLOCKED` with its reason.
