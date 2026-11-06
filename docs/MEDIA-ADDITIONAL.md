# Additional named media outcomes

`tools/temporal/media_additional.py` extracts five explicit named election-outcome statements from [The Texas Tribune's Texas legislative election report](https://www.texastribune.org/2026/11/03/texas-house-legislature-outcomes-control-republicans-democrats-2026/). The acquired article identifies Kristian Carranza, Mark Dorazio, Mano DeAyala and Morgan Meyer as House winners, and Taylor Rehmet as a Senate winner. The parser requires each exact assertion and its named subject in a unique article paragraph. A paragraph checksum makes the grammatical context reproducible.

These records use `media-called-winner` and identify The Texas Tribune as the reporting/calling organization. They describe the newsroom's explicit outcome assertion, not a separately timed decision-desk call. Candidate identifiers, contest identifiers, districts and call times are unresolved because this article does not supply them alongside the assertions. No government identity, certification, service interval or incumbent replacement is inferred. Leads, unnamed defeats, concessions and chamber-control statements produce no candidate designation. The five records are not statewide or chamber-complete coverage.

The source was retrieved on November 5, 2026 at `05:27:48.273504+00:00`, with SHA-256 `81f4fde20fa2af9aa73804faea6e2468bdad6cd9d0d604ab9fd70a0d3f815913`. Original publication and modification timestamps come from the article metadata. Offline replay retains the acquisition time and checksum.

`collect(fetch, offline=False)` uses the standard source acquisition interface and returns `designations`, `stateAudits` and `sourceObservations`. Its sole configured source identifier is `media-additional-texas-tribune-legislature`; its URL remains immutable. A changed or missing required assertion rejects the extraction rather than silently carrying forward an older call.

Regression tests: `.venv-geo/bin/python -m unittest discover -s tools -p test_temporal_media_additional.py`.

A separate discovery check found CalMatters's November 2026 results page publicly links AP Senate embeds `38146`/`38134` and Assembly embeds `38133`/`38145` under `https://interactives.apelections.org/election-results/customers/layouts/organization-layouts/published/117697/`. Direct HTTP acquisition returned a CloudFront access error. Successful browser accessibility observations of the two card embeds are handled separately by the [California adapter](MEDIA-CALIFORNIA.md), with their actual representations and observation times preserved.
