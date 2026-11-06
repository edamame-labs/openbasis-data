# Repository instructions

## Public repository communication

- Write commit messages, PR descriptions, issues, release notes, and other public repository communications around the concrete code or data changes, their technical purpose, and relevant validation results.
- Do not quote, summarize, or refer to private user conversations. Keep internal discussions, user requests, product strategy, and unpublished planning out of repository communications and published artifacts.
- Publish only supported factual claims. Describe relationships only to the extent established by their cited evidence.
- Before committing or pushing, review the staged diff and commit message for unintended files, private information, and conversational context.

## Data sources and reproducibility

- Publish only primary data directly issued by federal, state, or county governments (including county equivalents). City, town, municipal, and other smaller local datasets are outside the published scope. Use authoritative sources appropriate to the fact and effective date; accessibility alone does not establish currency.
- Do not use secondary aggregators, third-party directories, inferred contacts, or legacy records as fallbacks. Remove unsupported records instead of retaining them to meet a coverage target. Uncollected jurisdictions and offices must be labeled explicitly; missing rows do not establish vacancies. Never imply official verification that has not occurred.
- Every published datum must have traceable provenance, including contact details, officeholders, terms, vacancies, relationships, boundaries, and population figures. Use record-level references for facts from one source and field-level references when fields have different sources or conflicting evidence.
- Record the publisher, direct source URL or API query, retrieval date, and available publication date, effective period, dataset version, and geographic vintage. Preserve source identifiers and permitted evidence snapshots or checksums where practical. Distinguish retrieval from substantive verification.
- Derived data must reference its inputs and document transformations, matching rules, assumptions, exclusions, and validation checks so another person can reproduce it. Label inferred values and unresolved conflicts; do not present them as source facts.
- Document repeatable collection and verification workflows with source endpoints, commands, dependencies, output schemas, and known limitations. Where useful, provide a reusable SKILL.md with supporting scripts and references. Keep public-data verification instructions accessible without the private application repository, and exclude credentials and private conversations.

- Election race calls may also use directly published reporting from established news organizations, including attributed AP calls carried by a reporting partner. Keep media calls separate from official declarations, certification, vote-derived leaders and serving memberships. Record the calling organization, publishing outlet, direct URL, exact winner/call marker, actual observation time and publisher call time when provided. Do not substitute polling, candidate victory claims, concessions or calculated vote leads for a media race call. The government-only requirement remains in effect for other data classes.

## Legislative roster collection

- Track coverage separately for each chamber; Nebraska is unicameral. A collected chamber is not a census of legally occupied seats, and missing rows do not establish vacancies.
- Check source-specific status semantics against the actual current roster. Labels such as `Former` may describe a returning member rather than a departure. Preserve multiple direct references when one source provides identity fields and another establishes current membership.
- Preserve alphanumeric and named districts, multi-member districts, and source-person identifiers. Do not merge different people merely because they share a district.
- Separate HTTP response bodies from live browser DOM snapshots in provenance. Retain actual observation timestamps and representation checksums; never reset them during an offline replay. Publication requires the source-age gate, including browser observations.
- Use `tools/build.py`, `tools/test_*.py`, and `docs/region-*.md` in the public data repository for reproducible acquisition and source-specific extraction rules. Browser-only sources require explicit recent evidence; an access block must not trigger a fallback to a third-party directory or a previous roster.

## Analytical geography

- Preserve original government polygon coordinates for analysis; lossless compression is permitted. Generalized display boundaries must never feed analytical intersections.
- Record boundary vintage, applicable legislative plan, source identifiers and all derived transformations. Keep future election plans separate from the current officeholder cycle.
- Distinguish polygon area (including water), land area, population and voters. Never relabel area shares as population overlap. Preserve geometry repairs and coverage residuals without silently normalizing them.
- Derived boundaries require explicit primary-source component relationships and input references; do not invent Census GEOIDs for derived features.
