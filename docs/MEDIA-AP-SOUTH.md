# AP southern legislative race observations

`tools/temporal/media_ap_south.py` collects exact AP metadata/progress publications for the November 3, 2026 election. The acquired snapshot contains **1,457 state-legislative races and 1,397 explicit candidate winner flags** across 13 states. Sixty observed races have no extracted candidate call. These counts describe this publication rather than a legal seat inventory.

| State | Observed legislative races | Explicit candidate calls |
| --- | ---: | ---: |
| TX | 168 | 154 |
| NC | 170 | 164 |
| GA | 236 | 228 |
| FL | 141 | 134 |
| VA | 1 | 1 |
| SC | 125 | 119 |
| AL | 140 | 138 |
| TN | 116 | 115 |
| KY | 119 | 118 |
| AR | 119 | 117 |
| LA | 1 | 1 |
| MS | 2 | 0 |
| WV | 119 | 108 |

The exact source pattern is `https://interactives.apelections.org/election-results/data-live/2026-11-03/results/races/{STATE}/metadata.json` and the corresponding `progress.json`. Each of the 26 URLs is explicitly registered in `SOURCES`. Actual response-body acquisitions completed on November 5, 2026 from `06:28:41.644983+00:00` through `06:28:42.074673+00:00`. The standard public `Mozilla/5.0` user agent is recorded in acquisition metadata. Original entity bytes, including any compression, remain checksum-addressed; parsing decodes content without relabeling it as browser evidence.

The shared `media_ap.py` parser verifies the publication's archived layout/client/module chain and the result-card renderer's candidate `winner: X` semantics. The renderer explicitly associates this flag with a named win and AP race-call time. Metadata and progress join only through exact publisher race and candidate identifiers; each designation references both observations and the rendering semantics. Only state aggregate reporting units are accepted. The five shared publication context observations are included alongside the 26 state observations.

The collector preserves source general/special/nonpartisan type labels, seat labels, source sort/seat numbers, Census district fields and explicit winner counts. Named labels such as `District 20 Unexpired Term` remain intact instead of becoming guessed numeric districts. Two Arkansas same-day special-primary rows remain in raw evidence but are excluded from this general-election dataset. Runoff status does not establish a winner. County copies, vote leaders, estimated reporting completion and uncontested candidate lists cannot create a designation. Explicit candidate winner flags in uncontested races remain separately labeled according to publisher metadata.

Call timestamps are preserved when provided, including their explicit timezone. Retrieval times, publisher updates, calls, certification and service remain separate. No government person identity or serving membership is inferred. Sparse state observations, including Virginia, Louisiana and Mississippi, do not establish that other offices were absent from the ballot.

`collect(fetch, offline=False)` returns `designations`, `raceStatuses`, `stateAudits` and `sourceObservations`. Missing evidence and failed source validation are explicit. Offline replay preserves the original acquisition time. Run `.venv-geo/bin/python -m unittest discover -s tools -p test_temporal_media_ap_south.py`; shared candidate/race semantics have separate tests in `test_temporal_media_ap.py`.
