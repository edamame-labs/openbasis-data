# AP federal race calls published by NPR

`tools/temporal/media_federal.py` collects explicit media calls independently of government election observations. It reads the live [NPR 2026 dashboard](https://apps.npr.org/2026-election-results/), its directly linked [application script](https://apps.npr.org/2026-election-results/app.js), and the script-referenced [House feed](https://apps.npr.org/2026-election-results/data/house.json) and [Senate feed](https://apps.npr.org/2026-election-results/data/senate.json). The script attributes tabulation to The Associated Press, renders candidate `winner === "X"` as the winner marker, and labels `winnerDateTime` as the call time. Its distinct `R` marker denotes a runoff and is not a winner call.

At the initial observations on November 5, 2026 at `05:25:51Z`, the feeds contained 435 House races across all 50 states and 35 Senate races. There were 381 explicit House calls and 33 Senate calls. The module emits 414 `media-called-winner` designations and 470 `raceStatuses`, including all uncalled races. These are observed counts, not a promise that every race has been called. Senate special-general races for Florida and Ohio retain their separate source race IDs, class/seat labels and election types. Louisiana's source election type remains `Nonpartisan Election`.

House source District 1 in the six single-district states is mapped to the existing dataset's district `0` alias; the original seat number and label remain visible. Senate districts remain null, and multiple seat contests are distinguished by the publisher race ID. AP candidate identifiers remain election/contest scoped. No candidate name is joined to a government person or membership record.

A designation requires both candidate `winner: X` and race `called: true`, corroborated by `raceCallStatus: Called`. Missing, conflicting, test or non-live data fails closed. High vote totals, reporting percentages, incumbent flags, poll ratings and uncalled runoff markers produce no calls. Candidate `winnerDateTime` is preserved only when supplied, must have a timezone, and cannot be after the actual source observation. Government certification and legal service remain unestablished.

Every designation retains a JSON pointer to the exact candidate marker, corroborating race fields, source contest/candidate IDs, the actual observation timestamp and original source references. The House feed's original HTTP-body SHA-256 is `c5c11d9dc041f8e68c6e18c53bb18bc5ebcb784b57733aa0c9d9551f8e9b880d`; the Senate feed's is `7560f8ec2f24a0e9555a2f048a34bd206df2f0e66b76bdb4f09d307b13dbf64b`. NPR serves some bodies gzip encoded. Original bytes and hashes are retained; decompression is only a parser transformation.

The exact media source catalog is separate from official primary data and uses `MediaEvidenceStore`. Offline replay preserves source timestamps and raw representations. The context page/script must still establish the 2026 application, the explicit feed references, AP attribution and marker semantics. Separate fetches do not establish an atomic observation across both chambers.

```sh
.venv-geo/bin/python -m unittest discover -s tools -p 'test_temporal_media_federal.py'
```
