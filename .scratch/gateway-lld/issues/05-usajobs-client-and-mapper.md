# USAJOBS client and mapper (pass 2)

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 03

## Question

How does the Gateway call USAJOBS and map its JSON onto Kernel Postings, following the Adzuna mapper's conventions?

- **Client**: three auth headers, params (`Keyword` / `PositionTitle`, `LocationName`, `Radius` units, `DatePosted`, `ResultsPerPage` up to 500), when to call it at all (settled: when `Fetch.country == "us"`).
- **Mapper**: `MatchedObjectId` as `source_id`, `PositionRemuneration` + `RateIntervalCode` → Salary period, multiple remuneration entries or locations per Posting, `ApplicationCloseDate` for hard expiry, description cap (4000), Region from the location fields.
- **Domain mapping**: USAJOBS family → Adzuna category tag, from the research draft and the categories list fetched in [Live smoke test: Adzuna and USAJOBS](01-live-smoke-test-adzuna-usajobs.md).
- **Federal pay labelling**: how a Posting marks federal pay-table salaries so Analysis never mixes them unlabelled into Adzuna stats (Kernel `Posting` is fixed, so via `source` alone or something else).

Input from [Live smoke test: Adzuna and USAJOBS](01-live-smoke-test-adzuna-usajobs.md): multi-value separator is `;`; `Radius` behaves like miles; announcements can list up to 1,176 locations (Region and `Posting.location` need a rule); per-Posting `RemoteIndicator` and `TeleworkEligible` exist; `JobGrade`/`LowGrade`/`HighGrade` mark pay-table jobs; `JobCategory` can hold up to 11 series; description candidates (`JobSummary`, `MajorDuties`, `QualificationSummary`) run to 7.9 KB against the 4,000 cap; dates have no timezone. Page size 500 would mean ~40 MB per response. Code list fixture has all 822 series with `JobFamily`.

Input from [Gateway query interface](02-gateway-query-interface.md): for the cross-source Duplicate rule to work, `Posting.description` must **start with** the announcement's opening text (likely `JobSummary`), so an Adzuna snippet of the same ad is a prefix of it. `company` should be the employer name Adzuna would show (`OrganizationName` likely). NAVSEA's 3 same-job announcements in the fixture are a test case.

Input from [Adzuna client and mapper](03-adzuna-client-and-mapper.md): conventions to mirror: text fields only trimmed and whitespace-collapsed; a drop is a per-result mapping error (`KeyError`/`TypeError`/`ValueError`/`ValidationError`), and missing optional data never is; non-occupational buckets map to `None` Domain; 10 s timeout, 2 retries on timeout/connect/5xx, 401/403 propagate, other 4xx propagate as bugs; credentials never in logs or trace metadata.

Input from [L1 cache, budget guard and replay](04-l1-cache-budget-guard-and-replay.md): L1 stores mapped Postings, so raw response size only affects the transfer, not the cache. `closes_at` drives both the close-date filter and when an L1 row is deleted, so it must be set whenever `ApplicationCloseDate` parses. USAJOBS calls are counted but unlimited (`calls_left=None`).

## Answer (2026-10-30)

Grilled with the user; all recommendations accepted. 15 free USAJOBS calls made (no Adzuna quota) from a scratchpad script, not saved as fixtures.

**New live facts**
- `PositionTitle` matches **any** word in the title: "data engineer" returned 99 results around DC, including Data Analyst and Civil Engineer. A quoted phrase returned 0. `Keyword` needs all words but searches the whole announcement: 33 results, including `GENERAL ENGINEER`.
- `DatePosted` above 60 is capped silently: "engineer" returned 426 at both 60 and 90.
- Country-wide "data engineer" (`DatePosted=60`) timed out on both tries, at 25 s and 20 s. "engineer" and "nurse" returned in about a second with no location.
- An unresolvable `LocationName` returns 200 with 0 results.
- `ResultsPerPage=50` is about 1 MB. In 125 sampled Postings, every one had a single remuneration entry; one used `SY`.

**Params** (`GET https://data.usajobs.gov/api/Search`; headers `Host`, `User-Agent`, `Authorization-Key`)
- `PositionTitle=<Fetch.title>`, in the API's default relevance order. `sort=opendate` (Adzuna's rule) was rejected because it puts unrelated engineers ahead of real matches. The Relevance stage removes the extra matches.
- `ResultsPerPage=50`, `Page=Fetch.page`, `DatePosted=min(max_days_old, 60)`. `Fields` isn't sent, because the default response already carries `Details`.
- `LocationName=location`, `Radius=ceil(radius_km / 1.609)`. A blank location omits both.
- `Fetch.category` is ignored. Translating a tag into series codes needs long `;` lists, and filtering after mapping would shorten pages, falsify `total` and lose real matches where the Domain table is coarse. A USAJOBS Posting can therefore return with a different Domain from the one asked for.
- `SourceOutcome.total = SearchResultCountAll`.

**Mapper** (one `SearchResultItems` entry → `Posting`)
- `source_id = MatchedObjectId`; `title = PositionTitle`; `company = OrganizationName` (the agency, not the department); `url = PositionURI` with `:443` removed. Text fields are trimmed and whitespace-collapsed, nothing more.
- `posted_at` = date of `PublicationStartDate`; missing or unparseable is a drop. `closes_at` = date of `ApplicationCloseDate`; unparseable is `None`. The timestamps carry no timezone, so the date is taken as written.
- **Description:** `JobSummary`, `MajorDuties` (list joined), `QualificationSummary`, in that order, collapsed and cut at 4,000 characters. All three blank is a **drop**: an empty description is a prefix of every other, so `coalesce` would merge it with any Posting of the same title and employer.
- **Salary:** the first `PositionRemuneration` entry only. `PA`/`PH`/`PD`/`BW`/`PM` → annual, hourly, daily, biweekly, monthly. `SY`/`PW`/`FB`/`ST`/`WC` → `salary=None`, because those figures can't be compared. Bounds ≤ 0 are ignored, reversed ones swapped, as for Adzuna. `currency="USD"`, `predicted=False`.
- **Federal pay label:** `source == usajobs`. Every USAJOBS salary is federal pay, so a new field would only repeat it. Keeping it apart from Adzuna salaries is the Analysis LLD's rule.
- **Location:** `location = PositionLocationDisplay`. For `region`, each `PositionLocation` becomes `(country, CountrySubDivisionCode, city)`, with `United States` written `US` and the `, State` suffix removed from `CityName`. One location uses its hierarchy; several use the common prefix (two Virginia sites → `("US", "Virginia")`, FAA's 1,176 → `("US",)`). Mixed countries or no locations → `("US",)`. Overseas Postings are kept, country first.
- `RemoteIndicator` and `TeleworkEligible` are ignored: `Posting` has no field for them, and the display string already reads "Anywhere in the U.S. (remote job…".
- FAA "Public Notice" talent-pool announcements stay normal Postings, since the mapper doesn't judge relevance.
- A body without `SearchResult` → `SourceUnavailable`. Drops follow the Adzuna rule otherwise.

**Domain**: a static dict in the USAJOBS client, using the first `JobCategory` entry. Series overrides win over the family. An unknown series → `None`, logged once. All tags checked against the 30 live Adzuna tags.

| Tag | Families | Series overrides into this tag |
|---|---|---|
| `social-work-jobs` | 0100 | |
| `hr-jobs` | 0200 | |
| `admin-jobs` | 0300 | |
| `scientific-qa-jobs` | 0400, 1300, 1500, 1900 | 0028 |
| `accounting-finance-jobs` | 0500 | 1510 |
| `healthcare-nursing-jobs` | 0600, 0700 | 0180 |
| `engineering-jobs` | 0800 | |
| `legal-jobs` | 0900, 1200 | |
| `creative-design-jobs` | 1000, 3900, 9000 | |
| `pr-advertising-marketing-jobs` | | 1035 |
| `consultancy-jobs` | 1100 | 0110, 0343 |
| `property-jobs` | | 1170 |
| `maintenance-jobs` | 1600, 4800, 5300, 5800, 8200, 8600, 8800 | |
| `teaching-jobs` | 1700 | |
| `logistics-warehouse-jobs` | 2000, 2100, 5700, 6900, 7000 | |
| `it-jobs` | 2200 | 0391, 0854, 1550, 1560 |
| `trade-construction-jobs` | 2500, 2600, 2800, 3600, 3800, 4100, 4200, 4600, 4700 | |
| `manufacturing-jobs` | 3100, 3300, 3400, 3700, 4000, 4300, 4400, 5200, 5400, 6500, 6600 | |
| `domestic-help-cleaning-jobs` | 7300 | |
| `hospitality-catering-jobs` | 7400 | |
| `None` | 0000, 1400, 1800, 2300, 3500, 5000, 7600, 9900 | 1102, 1105 |

The draft's local `law-enforcement` Domain is rejected: Domain stays an Adzuna tag. No USAJOBS Posting gets `sales-jobs`, `retail-jobs`, `customer-services-jobs`, `energy-oil-gas-jobs` or `charity-voluntary-jobs`.

**Transport**: as Adzuna (`httpx`, 10 s timeout, 2 retries at 0.5 s and 1 s on timeout, connect error and 5xx, then `SourceUnavailable`; 401/403 propagate; other 4xx propagate as bugs). The differences:
- A `429` → `SourceUnavailable`, with no day-long lockout, because USAJOBS has no limit to protect.
- The timeout stays at 10 s. A multi-word country-wide search that times out ends in `failures[usajobs]`, and Adzuna's results still return. Raising it wouldn't help, since those calls also failed at 20 s and 25 s.
- The key travels in a header, not the URL, so it can't reach `httpx`'s URL logs. It still never goes into logs or trace metadata.
