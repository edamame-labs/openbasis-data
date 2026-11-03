# Government legislative roster adapters: Louisiana through North Dakota

`tools/regions/region_b.py` reads only the state legislature publishers below.
It does not read an existing officials dataset or a secondary directory. The
counts are observed named members in the fetched official responses, not inferred
statutory membership or a vacancy census. Source snapshots were fetched on
November 2, 2026 (America/Los_Angeles).

| State | House / Assembly | Senate | Official primary roster |
| --- | ---: | ---: | --- |
| Louisiana | 103 | 38 | [House](https://house.louisiana.gov/H_Reps/H_Reps_FullInfo), [Senate](https://senate.la.gov/Senators_FullInfo.aspx) |
| Maine | 150 | 35 | [House](https://legislature.maine.gov/house/MemberProfiles/List?sort=alpha), [Senate](https://legislature.maine.gov/senate/senators/9536) |
| Maryland | 141 | 47 | [House of Delegates](https://mgaleg.maryland.gov/mgawebsite/Members/Index/house), [Senate](https://mgaleg.maryland.gov/mgawebsite/Members/Index/senate) |
| Massachusetts | 157 | 40 | [House](https://malegislature.gov/Legislators/Members/House), [Senate](https://malegislature.gov/Legislators/Members/Senate) |
| Michigan | 110 | 38 | [House](https://www.house.mi.gov/AllRepresentatives), [Senate](https://senate.michigan.gov/senators/all-senators/) |
| Minnesota | 134 | 67 | [House](https://www.house.mn.gov/members/list), [Senate API](https://www.mnsenate.gov/api/members), [Senate biennium](https://www.mnsenate.gov/api/bienniumYears) |
| Mississippi | 120 | 51 | [House](https://www.legislature.ms.gov/member/?fiscalyear=26&chamber=H), [Senate](https://www.legislature.ms.gov/member/?fiscalyear=26&chamber=S) |
| Missouri | 155 | 33 | [House](https://house.mo.gov/listmembers.aspx?year=2026&code=R), [Senate](https://www.senate.mo.gov/Senators); party/phone from the [House member grid](https://house.mo.gov/MemberGridCluster.aspx?year=2026&code=R) and [Senator Directory](https://www.senate.mo.gov/Senators/SenatorDirectory/) |
| Montana | 100 | 50 | [Legislature current-member feed](https://www.legmt.gov/wp-json/legmt/v1/people/legislators) |
| Nebraska | — | — | [Unicameral legislature: 49](https://nebraskalegislature.gov/senators/senator_list.php) |
| Nevada | 42 | 21 | [Assembly](https://www.leg.state.nv.us/App/Legislator/A/Assembly/Current), [Senate](https://www.leg.state.nv.us/App/Legislator/A/Senate/Current) |
| New Hampshire | 382 | 24 | [General Court membership TSV](https://gc.nh.gov/downloads/members.txt), [current House roster](https://gc.nh.gov/house/members/) |
| New Jersey | 80 | 40 | [Legislative roster](https://www.njleg.state.nj.us/legislative-roster) |
| New Mexico | 68 | 42 | [House](https://www.nmlegis.gov/Members/Legislator_List?T=R), [Senate](https://www.nmlegis.gov/Members/Legislator_List?T=S) |
| New York | 150 | 62 | [Assembly](https://nyassembly.gov/mem/), [Senate](https://www.nysenate.gov/senators-committees) |
| North Dakota | 94 | 47 | [September 2026 special-session membership](https://ndlegis.gov/assembly/69-2025/special-2/members), all nine pages |

Total: **2,670** named legislators, from **39** source responses. Nebraska is
represented as a unicameral legislature; it has no synthetic lower chamber.

## Collection and validation

The module exposes `SOURCES`, `SOURCE_HOSTS`, `COVERAGE`, `parse`, and `collect`.
`collect(build.fetch, offline=False)` retrieves and parses the government responses.
The shared fetcher records the exact URL, redirect destination, retrieval timestamp,
response SHA-256, and local snapshot. `collect(build.fetch, offline=True)` replays
those snapshots and verifies their checksums. `build.fetch` rejects publisher-host
changes, HTTP failures, and missing cached evidence. No former record is carried
forward when a new fetch fails.

Run parser regressions with:

```sh
python3 -m unittest discover -s tools -p test_region_b.py -v
```

The parser rejects missing roster structures, unknown roster structures,
conflicting duplicate profiles, impossible term-date / active-flag combinations,
duplicate person identifiers, grossly incomplete counts, and multiple occupants
in a district where the published chamber uses single-member districts. Named
Massachusetts districts and Minnesota subdistrict letters are preserved. Person
identifiers remain distinct in multimember districts; no synthetic seat numbers
are assigned. Only fields stated by a source are emitted. For example, no party
is inferred when a directory does not supply it.

## Contact fields, identifiers and party

`email`, `phone` and `photo` are copied from the record's own roster, normalized
by `build.contact`; generic placeholder portraits are skipped and shared office
mailboxes/numbers are dropped centrally. `ids` holds the publisher's person
identifier keyed by source id where one is published (MD, MA, ME House, MI Senate,
MN, MO Senate, MT, NH House index value, NJ, NM `SponCode`, NY slugs, ND biography
slug keyed `nd-roster`). Louisiana, Missouri House, Nebraska and Nevada profile
links carry district numbers, not person IDs, so no `ids` are emitted.

| State | Fields from roster |
| --- | --- |
| Louisiana | email, district-office phone, portrait (from the enclosing card) |
| Maine | House email, portrait; Senate party letter from each `Name (P-County)` listing line |
| Maryland, New Mexico, North Dakota, NY Senate, Mississippi | portrait |
| Massachusetts | email, phone, portrait |
| Michigan | House email, phone; Senate email, phone, portrait from `senatorInfo` |
| Minnesota | House email, phone, portrait; Senate email, phone; portrait is `/img/member_thumbnails/` + `mem_bio_pic`, the path the Senate's own `memberList` script renders |
| Montana | `emailAddress`, `phoneNumber`, `photo.url` |
| Nevada | Carson City phone (detail row after each member row), portrait; Cloudflare-obfuscated emails are not decoded |
| New Hampshire | `WorkEmail`, `Phone` from the download |
| New York Assembly | email, Albany office phone (LOB/Capitol ZIP 12248/12247, fax excluded), portrait |

Missouri party and capitol phone come from a second official page per chamber and
carry `fieldEvidence` naming it: the House grid is joined by district **and**
identical published name; the Senator Directory by Senate member `id`, name and
district. Non-matching rows keep no value. Party remains absent where no official
list publishes it: Mississippi (only per-member files such as
`https://billstatus.ls.state.ms.us/members/house/<name>.xml`, 171 members; the
roster PDFs are image-only), the New York Assembly (no party on any Assembly page),
Michigan HD4 (Karen Whitsett, listed without party) and nonpartisan Nebraska.

## Publisher structure and eligibility details

- **Louisiana:** use the full member-information pages linked by each chamber.
  Senate `/Senators` and `/Senators.aspx` returned HTTP 403, while the homepage-linked
  `/Senators_FullInfo.aspx` returns the roster. Name, district, party, and profile
  links are taken from the member cards. Vacant labels are excluded.
- **Maine:** the House moved its alphabetical directory to
  `/house/MemberProfiles/List?sort=alpha`. Explicitly resigned and deceased entries
  remain in that table and are excluded. The November 2 refresh explicitly labels
  Lydia Crafts (district 46) `Resigned`; this is an exclusion based on that
  published status, rather than an inferred vacancy. Tribal representatives without numbered
  districts are outside this adapter's district-member scope. Senate profile paths
  use both `/district` and `/District`; matching is case-insensitive.
- **Maryland:** leadership profiles appear again in the ordinary member directory.
  Identical records are deduplicated; hidden accessibility links containing whole
  profile descriptions are excluded from name extraction. Delegate subdistrict
  suffixes and multimember membership are retained.
- **Massachusetts:** the current chamber directories contain structured tables.
  Named districts are kept verbatim, without converting county-style names to
  invented district numbers. Vacant labels are not person records.
- **Michigan:** the House states its current term expires December 31, 2026. The
  House entries can be either linked cards or plain `div.page-search-target`
  cards without a party profile link. Both are included; an absent party remains
  absent rather than excluding the person. The Senate publishes its roster directly
  in the `senatorInfo` attribute of its
  `senator-list` component; this is first-party page data, not a separate aggregator.
  Linked caucus websites are not used as data inputs.
- **Minnesota:** House data comes only from the current alphabetical `Alpha` tab;
  the `Elect` tab contains former names alongside successors. The Senate page's
  own `memberList` JavaScript requests `/api/members` and `/api/bienniumYears`.
  The old `www.senate.mn` host redirects those APIs to the canonical government
  host `www.mnsenate.gov`. The biennium must report `2025 - 2026`.
- **Mississippi:** the public chamber pages embed `/member/` iframes with
  `fiscalyear=26` and the chamber code. Only `active-member` cards are collected.
  The Senate feed includes the presiding lieutenant governor with a synthetic
  internal district value `53`; that card is excluded from district legislators.
  Its official lieutenant-governor link and presiding title must match before
  exclusion, preventing accidental removal of an ordinary senator.
- **Missouri:** the House roster embeds a menu that links the `listmembers.aspx`
  directory with explicit `year=2026&code=R`. Member profile links must retain that
  session. Senate records come from current named member links, excluding the
  separate vacant-district link.
- **Montana:** the legislature's [Legislator Explorer](https://legislators.legmt.gov/)
  JavaScript explicitly calls the government WordPress current-member endpoint.
  It includes 155 records: 150 active and five inactive. The response must report `recordCount` equal to its content length and
  `pageable.paged=false`. Only `isActive=true` records are eligible, and each reported start/end date must contain the source
  retrieval date. An inconsistency stops collection; it does not choose one field
  over the other.
- **Nebraska:** the official landing-page directory repeats the list for alternative
  display ordering. Identical entries are deduplicated. The current/default legislature selection must identify the
  109th Legislature (2025–2026); a historical dropdown option alone does not qualify. No party field is inferred.
- **Nevada:** use the explicit `Current` directories. `data-order` supplies the
  actual member name separately from visible leadership titles. It also supplies
  party and district labels. Contact fields hidden by email protection are omitted.
- **New Hampshire:** the official downloadable tab-delimited file uses
  Windows-1252 characters and contains 384 House entries. Its `electedStatus`
  values (`new`, `Incumbent`, `Former`, or blank) classify election history;
  `Former` does **not** establish that a person has left the current legislature.
  The adapter joins the downloadable House entries to all 382 members selected
  by the official current House roster. Matching requires exact normalized
  surname and a unique compatible given name; ambiguous identities or a current
  roster member missing from the download stop collection. The two extra download
  entries, Charlie St. Clair and Michael Vose, are absent from the current roster
  and therefore excluded. Each House record references **both** the download
  (name, district, party) and current roster (membership eligibility). House
  district numbers retain their county qualifier. All 24 Senate members are
  transcribed from the current combined membership download. The separate
  [House Clerk update](https://gc.nh.gov/house/aboutthehouse/RDSE.pdf), dated
  August 27, 2026, independently reports 382 qualified members and identifies
  St. Clair's death and Vose's resignation. That PDF was a cross-check, not a
  data input or a vacancy inference rule.
- **New Jersey:** current roster data is embedded in the official page's
  `__NEXT_DATA__`, under `props.pageProps.legrosterData`. The records explicitly
  supply chamber, district, party, name components, and official biography links.
  Both Assembly members in each district retain their individual biography IDs.
- **New Mexico:** the current chamber pages provide name, party, district, and
  official `SponCode` profile links. Former legislators have a separate directory
  that is not read by this adapter.
- **New York:** the Assembly member directory provides each name and district in
  its member heading. Senate directory links provide name, party labels, and
  ordinal district. Party labels are transcribed without inferring affiliation.
- **North Dakota:** the official [2025–26 legislators index](https://ndlegis.gov/2025-26-legislators)
  links regular, January 2026, and September 2026 session memberships. This adapter
  uses the latest linked session, September 2026, instead of the older regular
  session directory, which includes dated historical transitions. Pagination is
  discovered from the official last-page link and all pages are fetched. Each
  member cites its exact supporting page, including `?page=1` through `?page=8`.
  A dated transition marker triggers review. This is the publisher's latest
  session membership snapshot, not a claim that every later personnel event has
  been independently checked.

## Currency limits

An undated current directory establishes what its publisher presently displays;
its retrieval timestamp is not a government certification date. Source-reported
session periods and active term dates are retained in provenance where available.
These adapters verify faithful source extraction and explicit eligibility filters;
they do not certify that an official website cannot contain an omission or delay.
Missing records are never converted into vacancy assertions.
