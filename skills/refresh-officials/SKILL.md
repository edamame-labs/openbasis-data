---
name: refresh-officials
description: Refresh every officeholder collection in openbasis-data (federal, national, governors, statewide officers, state high courts, legislatures), repair adapters broken by site changes or elections, rebuild fresh, verify and open a pull request. Use on a schedule or when an office changes hands.
---

# Refresh officials

This is the umbrella runbook. Governors have their own detailed runbook in `skills/refresh-governors/SKILL.md`. Its steps 1–6 apply to every module below.

| Collection | Adapter | Method and per-state notes | Output |
| --- | --- | --- | --- |
| U.S. House and Senate, office addresses, House websites and photos | `tools/build.py` (`parse_federal`) | `docs/FEDERAL.md` | `officials.json` |
| President, Vice President, DC and territory delegates | `tools/national.py` | `docs/NATIONAL.md` | `national.json` |
| Governors | `tools/regions/executive.py` | `docs/EXECUTIVE.md` | `officials.json` |
| Other statewide elected officers | `tools/regions/statewide_{a,b,c,d}.py` | `docs/STATEWIDE-{A,B,C,D}.md` | `officials.json` |
| Courts of last resort | `tools/regions/courts_{a,b}.py` | `docs/COURTS-{A,B}.md` | `officials.json` |
| State legislatures | `tools/regions/region_{a,b,c,d}.py` | `docs/region-{a,b,c,d}.md` | `officials.json` |

The shared vocabulary, module interface and coverage rules are in `tools/statewide.py`. `build.py` discovers `statewide_*.py` and `courts_*.py` by filename.

## Rules that never bend

- **Use only primary government sources.** If a source can't be read, the office stays `not-collected` with a blocker. Never substitute Wikipedia, Ballotpedia, associations (NGA, NASS, NAAG, NCSC), news, search results or a previous release.
- **Don't evade access controls.** Send the module's `USER_AGENT`. Never rotate agents, imitate a browser, run headless browsers, use proxies or solve challenges. Browser-only sources need a capture made by a person (see `refresh-governors` step 3).
- **Fail closed.** Every rule reads one precise element and must produce the expected count: one holder, N seats, exactly one chief justice. Investigate failures; never loosen a pattern until it passes.
- **Incumbents only.** After an election, an officeholder-elect never replaces the incumbent before the legal term start. The record follows the official page. If a page shows a successor before the term starts, stop and investigate.
- **Scope.** Collect statewide-elected offices only. Exclude boards elected by district (see `tools/statewide.py`), appointed offices and legislature-chosen officers. County and city offices are out of scope.
- **No private context** in commits or PRs.

## Steps

Run from the `openbasis-data` root with `.venv-geo` (`requirements-geo.txt`).

### 1. Probe every source

```sh
.venv-geo/bin/python -B - <<'EOF'
import sys; sys.path.insert(0, 'tools')
import build; sys.modules['build'] = build
for m in build.region_modules():
    if not m.__name__.split('.')[-1].startswith(('statewide_', 'courts_', 'executive')): continue
    browser = getattr(m, 'BROWSER', set())
    for key, (pub, url) in m.SOURCES.items():
        if key in browser: continue
        try:
            raw, src = build.fetch(key, pub, url, user_agent=m.USER_AGENT)
            rows = m.parse(key, raw, src)
            print(key, len(rows), '; '.join(r['office']+': '+r['name'] for r in rows)[:160])
        except Exception as x:
            print(key, 'FAIL', type(x).__name__, str(x)[:200])
EOF
```

(If a module's `parse` signature differs, use its `collect(build.fetch, False)`.) Then compare the names with the last `data/officials.json` and `data/national.json`:

| Result | Action |
| --- | --- |
| Same names | Nothing to do. |
| New name | Confirm on the page that the person holds the office now, not as "elect" or "transition", and that the term-start date has passed. Then accept it. |
| HTTP error (403, 5xx, timeout) | Retry once later (`build.fetch` already retries transient transport errors once). If it persists, move the office to the module's `BLOCKED` with the URL and reason. The office becomes `not-collected`. |
| AssertionError (no match, wrong count, conflict) | The page changed. Rewrite that rule against one precise element, add or adjust a fixture test, and update the module's doc table. |
| URL contains an officeholder's name (several do; see the docs) | The page disappears when the office changes hands. Follow the office's homepage link to the new page and update the URL. |

### 2. Re-check blocked offices and courts

For each `BLOCKED` entry and each `not-collected` court, run `curl -sS -o /dev/null -w '%{http_code}\n' -A "<USER_AGENT>" <url>`. If one now returns 200, write a rule, move it out of `BLOCKED`, and add a test.

### 3. Elections and term starts

After a general election, look up each state's term-start date in its constitution or statutes on an official site. Until that date, keep incumbents. Afterwards, expect new names and confirm each one. For legislatures, follow `docs/region-*.md` and the `TERM_BEGUN` handling in the region modules.

### 4. Browser captures

States in any module's `BROWSER` set need a capture made by a person within 24 hours of the build (`refresh-governors` step 3). An automated agent opens an issue listing the captures needed and does not publish without them.

### 5. Test, rebuild, verify

```sh
.venv-geo/bin/python -B -m unittest discover -s tools -p 'test_*.py'
.venv-geo/bin/python -B tools/build.py --browser-snapshots --fresh
python3 -B tools/build.py --verify --fresh
```

Check:
- `data/coverage.json` `states[].stateExecutive.offices`: every declared office shows `collected` or `not-collected`, and `notCollected` matches the blockers.
- `states[].stateCourts.courts`: likewise for courts.
- `national.president`, `national.vicePresident` and `national.delegates`.
- `git diff data/` shows name changes only where step 1 found them.

### 6. Pull request

Branch from `main`. Commit `tools/`, `docs/` and `data/` together. In the PR body, list the officeholders added, removed or renamed, each with its official URL; the offices moved in or out of `BLOCKED` and why; the network type used for the run (residential, office or cloud); the test and verify results; and any missing browser captures. Don't merge your own PR. After it merges, bump the `openbasis-data` submodule in the app repository.

## Adding an office or state

1. Check that voters of the whole state elect the office, from an official source: a constitution or statute on a .gov site, or the secretary of state's list of elected officials. Cite it in the module's doc.
2. If the vocabulary in `tools/statewide.py` lacks the office, add a key with its title and Google Civic role. For several holders at once, also add the key to `MULTI`.
3. Add a rule to the state's module, a fixture test, and a doc table row.
