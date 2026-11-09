---
name: refresh-governors
description: Refresh the governor records in openbasis-data from each state's official governor website, re-check blocked states, rebuild, verify and open a pull request. Use on a schedule (weekly, and daily around inaugurations) or when a governor changes.
---

# Refresh governors

This skill refreshes `office: "Governor"` records. The adapter is `tools/regions/executive.py`, and the method and its limits are in `docs/EXECUTIVE.md`. Read both before changing a rule.

## Rules that never bend

- **Use only official state governor websites.** Never fill a missing or blocked state from Wikipedia, NGA, Ballotpedia, news articles, a search engine, a previous release or memory. If a state can't be read, it stays `not-collected`, with the reason in `BLOCKED`.
- **Don't evade access controls.** If a site answers automated requests with a 403, a bot challenge or a CAPTCHA, don't rotate user agents, imitate a browser, run headless browsers to get through, use proxies, or solve challenges. Requests send `USER_AGENT`, which identifies the project. Those states need a capture made by a person (step 3), or they stay blocked.
- **Fail closed.** If a rule finds zero names or two different names, the build stops. Investigate the page; never loosen a pattern until it "passes".
- **No private context in the public repo.** Commit messages and PRs describe the code and data changes and the validation results, and nothing else.

## Where to run

Run from a stable network and record which kind (residential, office, or cloud) in the PR. Several state sites refuse hosting-provider addresses, so a run from a cloud VM or VPN may see more failures than one from a residential or office connection. In tests, CT and TN failed from a VPN exit and succeeded from a home connection. Treat such failures as blocked for that run. Never switch to proxies, residential-proxy services or other networks chosen to get past a block.

## Schedule

| When | Why |
| --- | --- |
| Weekly | Detect site redesigns that break a rule, and successions such as resignations and deaths |
| Daily from the first Monday in January until all inaugurations are done (in election years) | Governors-elect take office on dates set by each state. Records change only when the official site changes |
| After any news of a governor change | Confirm that the official site reflects it before the data does |

## Steps

Run every command from the `openbasis-data` root. The full build needs `.venv-geo` (`requirements-geo.txt`).

### 1. Probe the HTTP sources

```sh
python3 -B - <<'EOF'
import sys; sys.path.insert(0, 'tools')
import build; sys.modules['build'] = build
from functools import partial
from regions import executive as e
for key, (pub, url) in e.SOURCES.items():
    if key in e.BROWSER: continue
    try:
        raw, src = build.fetch(key, pub, url, user_agent=e.USER_AGENT)
        print(key, e.parse(key, raw, src)[0]['name'])
    except Exception as x:
        print(key, 'FAIL', type(x).__name__, str(x)[:200])
EOF
```

Every line should print a name. Compare the names with the last published `data/officials.json`:

- **Same name.** Nothing changed.
- **New name.** Check that the page really shows the new officeholder as governor (not "governor-elect" or "transition") and that the inauguration date has passed. If the site still shows the outgoing governor, keep their record. The record follows the official site.
- **FAIL with an HTTP error (403, 5xx, timeout).** Retry once later. If it keeps failing, move the state from `RULES` to `BLOCKED` with its URL and say so in the PR.
- **FAIL with an AssertionError (no match or ambiguous).** The page changed. Open it, find one element that names the governor (the `<title>`, a single `<h1>`, `og:title`/`og:site_name`, or a meta description), and update that state's pattern. Prefer elements that name the office holder over news headlines. Add or adjust a case in `tools/test_executive.py`.
- **North Dakota 404.** Its source URL contains the governor's name (`/governor-<name>`). Follow the "Governor" link in the homepage menu and update the URL.

### 2. Re-check blocked states

For each URL in `BLOCKED`, run `curl -sS -o /dev/null -w '%{http_code}\n' -A "<USER_AGENT>" <url>`. If one now returns 200, inspect the page, write a rule, move the state from `BLOCKED` to `RULES`, and add a test.

### 3. Captures made by a person (browser-only states)

States in `BROWSER` are read from a DOM snapshot that a person captured in a normal browser and imported. A snapshot counts for 24 hours. An automated agent must not produce these itself (see the rules above). It should open an issue or PR comment listing the states that need a capture and the instructions below, then continue without them.

For the person doing the capture, repeat this for each `BROWSER` state:

1. Open the source URL in your everyday browser and wait for the page to load. Close any newsletter popup. Confirm that the page shows the governor and is not a challenge or error page. If it is a challenge, skip the state; don't solve it.
2. Open DevTools → Console and run `copy(document.documentElement.outerHTML)`.
3. On macOS, save the clipboard **as UTF-8**. Without the locale, `pbpaste` mangles characters such as curly quotes:

```sh
LC_ALL=en_US.UTF-8 pbpaste > gov-xx.html && date -u +%Y-%m-%dT%H:%M:%SZ
```

4. Import the file using the printed time. If the address bar changed after a redirect, add `--final-url`:

```sh
python3 -B tools/import_snapshot.py --input gov-xx.html --url <source URL> \
  [--final-url <address bar URL>] --observed-at <UTC ISO time>
```

The current browser states and the element each rule reads:

| State | Source URL | Marker |
| --- | --- | --- |
| KS | `https://governor.kansas.gov/` (redirects to `www.governor.ks.gov`) | menu link `aria-label="Governor <name>"` to `/about-the-office/governor-…` |
| MA | `https://www.mass.gov/orgs/office-of-the-governor` (redirects to a page named after the governor) | `<title>Governor <name> and Lt. Governor … \| Mass.gov</title>` |
| MI | `https://www.michigan.gov/whitmer` (the path is the governor's surname; after a change, follow the state's menu to the new path) | `<title>Governor <name></title>` |
| MN | `https://mn.gov/governor/` | `<meta property="og:site_name" content="Office of Governor <name> and Lt. Governor …">` |
| NH | `https://www.governor.nh.gov/` | `<meta property="og:site_name" content="Governor <name>">` |
| NY | `https://www.governor.ny.gov/` | `<meta property="og:site_name" content="Governor <name>">` |
| RI | `https://governor.ri.gov/` | `<title>Welcome to the Office of Governor <name> \| Governor's Office, State of Rhode Island</title>` |

If a browser state becomes readable over HTTP with `USER_AGENT`, remove it from `BROWSER` and delete its cache mapping, so it is collected over HTTP and labeled `http-response-body`.

CO accepted no HTTPS connection from any network tried. Re-check it on each scheduled run.

### 4. Test

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_*.py'
```

### 5. Rebuild and verify

Publication needs fresh observations of every source:

```sh
.venv-geo/bin/python -B tools/build.py --browser-snapshots --fresh
python3 -B tools/build.py --verify --fresh
```

`--browser-snapshots` fails if any browser-only source in the repo (including the legislative ones in `docs/region-d.md`) lacks a capture from the last 24 hours. If a person can't capture them, don't publish. Report which captures are missing and stop. `--offline` rebuilds are for development only and must not be published.

Check the result:

- `data/coverage.json` → `states[].stateExecutive.offices.governor` is `collected` with `records: 1` exactly for the states in `RULES`.
- `data/district-links.json` → every `*-governor` record uses `matchingRule: "statewide-governor-state-fips"`.
- `git diff data/officials.json` shows governor changes only where step 1 found them.

### 6. Pull request

Branch from `main`, commit `tools/`, `docs/` and `data/` together, and open a PR. State in the body:

- governors added, removed or renamed, with the official URL for each
- states moved between `RULES`, `BROWSER` and `BLOCKED`, and why
- test and `--verify --fresh` results
- browser captures that were missing, if any

Don't merge your own PR. After it merges, bump the `openbasis-data` submodule in the app repository so the Google-compatible endpoint (`/api/civicinfo/v2/representatives`) returns the new data.
