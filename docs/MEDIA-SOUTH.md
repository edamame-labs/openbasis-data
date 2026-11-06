# Southern newsroom legislative outcome observations

`tools/temporal/media_south.py` collects explicit publisher outcomes from three acquired newsroom publications. The snapshot contains 313 observed legislative races and 297 explicit publisher outcomes:

| Publisher / jurisdiction | Races | Explicit outcomes | Not called |
| --- | ---: | ---: | ---: |
| Texas Tribune carrying AP, Texas | 168 | 154 | 14 |
| Alabama Political Reporter, Alabama | 140 | 138 | 2 |
| WHQR, North Carolina regional reporting | 5 | 5 | Not a complete ballot universe |

The [Texas Tribune application](https://apps.texastribune.org/features/2026/texas-general-election-live-results-2026/) links the exact `main.b04f0e5dfd.mjs` script, which references the [public bulk publication](https://s3.amazonaws.com/sos-test-2.texastribune.org/2026_general/republic_json/results_FLAT.json). The application explicitly renders Associated Press projections from `contest_result`, `is_called` and candidate `is_winner`. The collector accepts only November 3, 2026 legislative rows whose source is Associated Press. It retains 150 general House races and 16 general Senate races, plus the separate House93 and Senate22 special races with distinct publisher contest IDs. The 154 positive records include 17 separately labeled uncontested outcomes with both explicit called and candidate-winner flags. County components, other offices and vote ranking do not determine designations. No call timestamp is supplied by this feed.

[Alabama Political Reporter's publication](https://www.alreporter.com/?ui=desktop) links `/_next/static/chunks/2yt3y_gbjse3r.js`, which exposes `/api/election-results` and defines `APR call` and `Race called by APR`. The [public endpoint](https://www.alreporter.com/api/election-results) contains 105 House and 35 Senate races for November 3, 2026. Only candidate `winner: true` paired with `calledBy: apr` is accepted. These calls belong to Alabama Political Reporter, even where the vote source is labeled `sos`. They are not represented as AP calls or government certifications. Historical, test and disputed representations are rejected. Publisher update times remain separate from call times.

[WHQR's Cape Fear election report](https://www.whqr.org/local/2026-11-03/election-2026-preliminary-results-for-cape-fear-region-races) explicitly reports five named defeats: Senate7/8 and House17/18/19. Each accepted assertion has an exact paragraph reference and district. The House20 lead is excluded. These are direct newsroom outcome assertions, not separately timed AP decision-desk calls. Regional coverage does not establish missing contests elsewhere in the state.

All observations retain their original retrieval timestamps, checksums, exact publication URLs and publisher identifiers. Texas acquisitions were completed November 5, 2026 around 06:25:39 UTC; the independent Alabama feed around 06:26:42 UTC. Source metadata supplies the exact times for each artifact. The S3 publication requires the archived script's exact JavaScript URL literal as its authority chain; the storage host alone establishes no publisher authority.

The collector returns `designations`, `raceStatuses`, `sourceObservations` and `stateAudits`. Certification, government person identity, service and unsupported call times remain unresolved. GA, FL, VA, SC, TN and KY are not collected by this particular module; separate AP acquisition collectors may provide those observations. Run `.venv-geo/bin/python -m unittest discover -s tools -p test_temporal_media_south.py`.
