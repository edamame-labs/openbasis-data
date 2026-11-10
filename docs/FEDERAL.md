# U.S. House and Senate fields

`tools/build.py` (`collect_federal`) builds the U.S. House and Senate rows. The roster XML files establish who serves. Second official sources add the House website, photo and office address, each with `fieldEvidence`.

## Sources

| Field | Chamber | Source | Element read |
| --- | --- | --- | --- |
| identity, district, party, phone | House | `https://clerk.house.gov/xml/lists/MemberData.xml` (Office of the Clerk) | `member-info` (`bioguideID`, `official-name`, `party`, `phone`); `statedistrict` |
| `address` | House | MemberData.xml, plus the room-code key on `https://www.house.gov/representatives` | `office-room`, `office-building`, `office-zip`, `office-zip-suffix`; the key's `<li>CODE: <a>… House Office Building</a></li>` items |
| `website` | House | `https://www.house.gov/representatives` (U.S. House of Representatives) | each `housegov_reps_by_state-*` table: caption (state), District cell, the Name cell's single link |
| `photo`, address check | House | `https://clerk.house.gov/members/<bioguide>` (one page per member) | `<img src=/images/members/<bioguide>.jpg alt="Photo of <official-name>">`; the Contact block's office and `Washington, DC, <ZIP+4>` spans |
| identity, party, phone, website, `address` | Senate | `https://www.senate.gov/general/contact_information/senators_cfm.xml` | `member` (`bioguide_id`, names, `party`, `phone`, `website`, `address`) |

House directory and member pages are fetched with the project's identifying `USER_AGENT`, four at a time. Each member page is its own source (`house-member-<bioguide>`).

## Rules

- **Address (House).** `<room> <building>, Washington, DC 20515-<suffix>`. The building name comes from the house.gov room-code key (CHOB Cannon, LHOB Longworth, RHOB Rayburn as of November 2026). A code missing from the key, a ZIP other than 20515, or a malformed room stops the build. The member's Clerk page must state the same room, building, city and ZIP+4, or the build stops. `fieldEvidence.address` names MemberData, the directory and the member page.
- **Address (Senate).** The XML `<address>` is whitespace-collapsed and must read `<room> Russell|Hart|Dirksen Senate Office Building Washington DC 20510`; it is published as `<room> <building> Senate Office Building, Washington, DC 20510`. Any other form stops the build.
- **Website (House).** Joined to MemberData by state name and district label (`1st`, `At Large`, `Delegate`, `Resident Commissioner`). Both lists give `Family, Given`; family names and first given names must agree after removing accents and punctuation (`Sanchez, Linda` matches `Sánchez, Linda`). A seat absent from the directory, a disagreeing name, or a host other than `house.gov`/`*.house.gov` stops the build. Rows labeled `- Vacancy` are skipped. URLs are published as the directory gives them; a few use `http://`. `fieldEvidence.website` names `house-directory`.
- **Photo (House).** Published only when the member's Clerk page contains exactly `https://clerk.house.gov/images/members/<bioguide>.jpg` and its alt text is `Photo of <official-name>`. A photo labeled for someone else stops the build. A page without that image gets no photo. The URL is never constructed without the page. `fieldEvidence.photo` names the member page.
- **Photo (Senate).** Not collected. The Senate contact XML has no photos, senate.gov publishes no per-senator photo pages, and the Biographical Directory (`bioguide.congress.gov`) answers this agent with an HTTP 403 challenge.
- **Non-voting members.** DC, PR, GU, VI, AS and MP members go to `data/national.json`, not `officials.json` (see [national offices](NATIONAL.md)). Their office is the MemberData `<district>` value (`Delegate` or `Resident Commissioner`). Any other value, or an unknown postal code, stops the build.

## Fetch retry

`build.fetch` retries a request once, after `RETRY_DELAY` (5 s), when curl reports a transport failure: exit 6 (DNS), 7 (connect), 28 (timeout), 35 (TLS), 52 (empty reply) or 56 (receive error). HTTP errors (`--fail`, exit 22) are never retried. A second failure stops the build.

## Tests

`tools/test_federal.py` covers the retry rules, the room-code key and directory parsing, an unknown building code, an unexpected non-voting office, website/address/photo extraction with field evidence, a missing photo, each conflict that stops (another member's name, a non-house.gov host, a different room on the Clerk page, a photo labeled for someone else, a seat missing from the directory), Senate address formatting, and the non-voting member rows in `national.json`.
