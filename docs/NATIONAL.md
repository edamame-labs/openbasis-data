# National offices

`data/national.json` holds the President, the Vice President, and the non-voting members of the U.S. House for the District of Columbia and the territories. Every row in `officials.json` belongs to one of the 50 states, so these offices are published separately rather than with a placeholder state.

## Sources

| Office / field | Source | Element read |
| --- | --- | --- |
| President | `https://www.whitehouse.gov/administration/` (The White House) | `<h2><a href="/administration/<slug>/">President <name></a></h2>` |
| Vice President | same page | `<h2><a href="/administration/<slug>/">Vice President <name></a></h2>` |
| President `party` | `https://api.open.fec.gov/v1/candidate/P80001571/?api_key=DEMO_KEY` (Federal Election Commission) | `results[0]`: `candidate_id`, `name`, `office`, `election_years`, `party` |
| Vice President `party` | `https://www.senate.gov/about/officers-staff/vice-president/vice-presidents.htm` (United States Senate) | `#SortableData_table` row whose Term ends in `present`: Name, Party, Presidency |
| Delegates and Resident Commissioner | Clerk `MemberData.xml`, house.gov directory and Clerk member pages | see [U.S. House and Senate fields](FEDERAL.md) |

All pages are fetched over HTTP with the project's identifying `USER_AGENT` (`tools/national.py`). The FEC URL uses the API's public `DEMO_KEY`.

## Method

- Each executive office's heading must match exactly once. Zero matches or two different names stop the build. `President` does not match inside `Vice President`.
- Names must be 2–5 words and contain none of President, Vice, Cabinet, Administration, First, Second or Lady.
- `website` is the officeholder page that the heading links to.
- `photo` is set only when the page links exactly one `whitehouse.gov` image with alt text ending "Official Portrait" to that officeholder page. Otherwise it is omitted.
- President `party`: the FEC candidate record must be `P80001571`, office `P`, with 2024 among its election years, and its name (`TRUMP, DONALD J.`) must match the White House name on family name and first given name. FEC party code `REP` is published as `Republican` (`DEM` as `Democratic`); any other code stops the build. This is the party of the 2024 presidential candidacy as registered with the FEC.
- Vice President `party`: exactly one row of the Senate's list of Vice Presidents may have a term ending `present`. Its name must match the White House Vice President, and its Presidency cell the White House President, on family name and first given name (dots ignored, so `J.D.` matches `JD`). The Party cell must be `Republican` or `Democratic`.
- Both `party` values carry `fieldEvidence.party` naming their source; the row's `sources` lists the White House page and that source.

## Schema

Executive rows have `id` (`us-president`, `us-vice-president`), `name`, `level: "federal"`, `jurisdiction: "United States"`, `body: "U.S. Executive"`, `office`, `website`, optional `photo`, `party`, `fieldEvidence` and `sources`.

Non-voting House rows follow, ordered by territory. They have `id` (`us-house-<bioguide>`), `name`, `level: "federal"`, `jurisdiction: "United States"`, `body: "U.S. House"`, `office` (`Delegate`, or `Resident Commissioner` for PR), `territory` (postal code: DC, PR, GU, VI, AS, MP), `party`, `phone`, `address`, `website`, `photo`, `ids.bioguide`, `fieldEvidence` and `sources`.

No row has `state` or `district`.

`coverage.json` → `national` gives `{status, records}` for `president`, `vicePresident` and `delegates`. A collected executive office has exactly one record. `delegates.records` counts the non-voting members in the release; a seat absent from the Clerk list is not recorded as a vacancy. Releases built before `national.json` existed have no `national` key, and releases built before delegates were added have no `delegates` key. `--verify` accepts both.

## Tests

`tools/test_national.py` covers extraction, the Vice President heading not being read as President, a missing or duplicated heading, photo selection, party from both sources with field evidence, a candidate or Vice President record naming someone else, two serving Vice Presidents, an unmapped FEC party code and the source allowlist. `tools/test_federal.py` covers the delegate rows.
