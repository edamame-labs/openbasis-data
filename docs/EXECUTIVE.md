# State executive officers

`tools/regions/executive.py` collects sitting governors from each state's own governor website. Lieutenant governors, secretaries of state, attorneys general and other statewide offices are not collected yet, and `coverage.json` lists them under `stateExecutive.notCollected`.

Governor records enter `data/` the next time the release is rebuilt and published with `--browser-snapshots --fresh`. Until then the checked-in snapshot has none.

## Sources and extraction

There is one source per state: the governor's official homepage, or a governor biography page on that site where the homepage names the governor only inside news items (North Dakota, South Dakota). Each rule in `RULES` names a single element that identifies the officeholder: the page `<title>`, a heading, or a meta description. Its pattern runs on the HTML-unescaped page with whitespace collapsed.

- The pattern must match at least once and produce exactly one distinct name. Zero matches or two different names stop the build.
- A name must have two to five words and must not contain `Office`, `Governor`, `Home`, `Welcome` or `State`.
- The North Dakota source URL contains the governor's name. When the office changes hands that page disappears, the fetch fails, and the rule needs review.
- Records carry `office: "Governor"`, `body: "<State> Executive"`, `level: "state"`, and `website` set to the source page. Party, contact details and term dates are not published in these elements and are not added from other directories.
- HTTP requests use the user agent `Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)`, recorded in each source's `acquisition.requestHeaders`. Several state sites reject curl's default agent.

A homepage reports the officeholder its publisher currently shows. After the November 2026 elections, governors-elect take office on dates set by each state. Until a site changes, the record continues to name the sitting governor, and the record does not establish a term end.

## Boundary links

Governors link to their state's Census feature with `matchingRule: "statewide-governor-state-fips"`, the same way U.S. senators link (`statewide-senate-state-fips`). `district_links.target_layer` checks for the governor office before the Nebraska unicameral rule, so the Nebraska governor is never joined to a legislative district.

## Browser captures

Seven official governor sites refuse automated retrieval but load in a normal browser: Kansas, Massachusetts, Michigan, Minnesota, New Hampshire, New York and Rhode Island. Each page was captured in a normal browser and imported with `tools/import_snapshot.py`, and these states are listed in `BROWSER`. Their sources are recorded with `representation: "browser-dom"` and the observation time. Like every browser-only source, they need captures from the last 24 hours before a `--browser-snapshots --fresh` publication. `import_snapshot.py --final-url` records a redirect, such as `governor.kansas.gov` → `www.governor.ks.gov` and `mass.gov/orgs/office-of-the-governor` → a page named after the current governor.

## Not collected

Colorado's governor site (`governor.colorado.gov`, 96.43.154.16 on every resolver tried) accepted no HTTPS connection from either a residential or a hosting-provider network, in a normal browser or over HTTP. It is recorded as `not-collected`, with its URL in `stateExecutive.blockers`, and is not filled from another publisher.

## Network egress

Reachability depends on the network a request leaves from. From a hosting-provider address (a VPN exit), Connecticut and Tennessee refused or dropped connections. From a residential connection, both returned their pages over HTTP to `USER_AGENT`. A state that fails from one network is recorded as blocked for that run. Its status is never changed by retrying through proxies or other networks chosen to get around the block.

## Refreshing

The repeatable procedure (schedule, commands, failure handling, and the rule against evading access controls) is in [skills/refresh-governors/SKILL.md](../skills/refresh-governors/SKILL.md).

## Tests

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_executive.py'
```
