# Ohio, Oklahoma Senate and Pennsylvania roster evidence

| State/chamber | Publisher endpoint | Parsed people |
| --- | --- | --- |
| Ohio Senate | https://www.ohiosenate.gov/members/directory | 32 |
| Ohio House | https://www.ohiohouse.gov/members/directory | 98 |
| Oklahoma Senate | https://www.oksenate.gov/senators | 47 |
| Pennsylvania Senate | https://www.palegis.us/senate/members | 50 |
| Pennsylvania House | https://www.palegis.us/house/members | 203 |

Counts refer to live official page observations on November 2, 2026 (UTC), not statutory seat totals. Ohio identifies the 136th General Assembly; Pennsylvania identifies the 2025–2026 session. Oklahoma's current Senate directory has 48 cards, one identifying only District 24 without a person's name. That card is excluded without generating a vacancy record.

The Ohio and Pennsylvania directories are requested over HTTP with the project user agent (`USER_AGENT` in `tools/build.py`, listed per source in `IDENTIFIED`). Their publishers answer it with the full roster page and answer curl's default user agent with HTTP 403. Their sources are recorded as `http-response-body` with the request header. Until November 2026 they were read from browser DOM observations.

The Oklahoma Senate answers both user agents with a JavaScript challenge (HTTP 307), while normal browser navigation loads the government-published directory. A person acquires its evidence from the official site in a browser. The cached representation is explicitly `browser-dom`, serialized from the live document after roster loading, rather than described as HTTP response bytes. No search-result snippets, archived third-party copies, or prior directory records supply these data.

For Ohio, the parser reads each portrait card's explicit name, district, party and profile href. Named vacant cards are excluded. For Pennsylvania it reads `.member[data-district]` cards, their name and official biography link. Duplicate occupied districts, unexpected card totals and changed session context stop extraction. Each record links to the directory supporting its fields.

## Reproducing browser evidence

1. Navigate to the exact government URL above in a normal browser. Verify that the full unfiltered directory and current session are displayed.
2. Serialize `document.documentElement.outerHTML` only after the roster finishes loading, preserving all roster cards. If the export interface truncates long strings, export bounded consecutive chunks and check the complete length before and after capture. Save the exact concatenated UTF-8 bytes and the UTC observation timestamp.
3. Import the file with the public helper:

```sh
python3 -B tools/import_snapshot.py --input /path/to/live-dom.html \
  --url https://www.oksenate.gov/senators \
  --observed-at '<actual ISO-8601 UTC observation time>'
python3 -B tools/build.py --offline
python3 -B tools/build.py --verify --fresh
```

The import checks the government allowlist, a complete HTML ending and an observation time within 24 hours. It records acquisition method and the SHA-256 of the saved DOM bytes. Its operator-supplied timestamp is an observation claim, not a government publication date or cryptographic proof of origin. Preserve the raw `.source-cache/` evidence when reproducing a historical snapshot.

Without explicit `--browser-snapshots`, online builds stop when a registered source requires browser evidence; they do not overwrite a saved browser observation with a challenge page or silently carry old records forward. The `--browser-snapshots` mode requires each imported observation to be within 24 hours and preserves its actual acquisition timestamp while freshly downloading the HTTP sources. An offline replay must still pass the 24-hour retrieval check before publication. A source that can be read through HTTP in another environment may instead be freshly collected by HTTP after removing its browser cache mapping; the resulting evidence is labeled `http-response-body`.
