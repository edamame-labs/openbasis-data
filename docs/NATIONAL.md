# National offices

`data/national.json` holds the President and Vice President. Every row in `officials.json` belongs to one of the 50 states, so these two offices are published separately rather than with a placeholder state.

## Source

| Office | Source | Element read |
| --- | --- | --- |
| President | `https://www.whitehouse.gov/administration/` (The White House) | `<h2><a href="/administration/<slug>/">President <name></a></h2>` |
| Vice President | same page | `<h2><a href="/administration/<slug>/">Vice President <name></a></h2>` |

The page is fetched over HTTP with the project's identifying `USER_AGENT` (`tools/national.py`).

## Method

- Each office's heading must match exactly once. Zero matches or two different names stop the build. `President` does not match inside `Vice President`.
- Names must be 2–5 words and contain none of President, Vice, Cabinet, Administration, First, Second or Lady.
- `website` is the officeholder page that the heading links to.
- `photo` is set only when the page links exactly one `whitehouse.gov` image with alt text ending "Official Portrait" to that officeholder page. Otherwise it is omitted.
- `party` is not published, because the source page does not state it.

## Schema

Each row has `id` (`us-president`, `us-vice-president`), `name`, `level: "federal"`, `jurisdiction: "United States"`, `body: "U.S. Executive"`, `office`, `website`, optional `photo`, and `sources`. Rows have no `state` and no `district`.

`coverage.json` → `national` gives `{status, records}` for `president` and `vicePresident`. A collected office has exactly one record. Releases built before `national.json` existed have no `national` key, and `--verify` accepts them.

## Tests

`tools/test_national.py` covers extraction, the Vice President heading not being read as President, a missing or duplicated heading, photo selection and the source allowlist.
