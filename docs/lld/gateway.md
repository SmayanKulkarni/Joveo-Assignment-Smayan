# Jobs Data Gateway LLD

The low-level design of the Jobs Data Gateway (component B in [HLD](../HLD.md) §3 and §7), precise enough to build from. Items marked ⏳ belong to the named LLD or task. Deliberate deferrals live in [future-scope.md](future-scope.md). Shared types and settings come from the [Kernel LLD](kernel.md).

Source tickets (each holds the full reasoning):
- [Live smoke test: Adzuna and USAJOBS](../../.scratch/gateway-lld/issues/01-live-smoke-test-adzuna-usajobs.md)
- [Gateway query interface](../../.scratch/gateway-lld/issues/02-gateway-query-interface.md)
- [Adzuna client and mapper](../../.scratch/gateway-lld/issues/03-adzuna-client-and-mapper.md)
- [L1 cache, budget guard and replay](../../.scratch/gateway-lld/issues/04-l1-cache-budget-guard-and-replay.md)
- [USAJOBS client and mapper (pass 2)](../../.scratch/gateway-lld/issues/05-usajobs-client-and-mapper.md)
- [Adzuna aggregate endpoints](../../.scratch/gateway-lld/issues/06-adzuna-aggregate-endpoints.md)
- [L2 store, expiry and sweep (pass 2)](../../.scratch/gateway-lld/issues/07-l2-store-expiry-and-sweep.md)

## 1. What the Gateway is

A plain async Python library outside the graph, between Collection's `search_jobs` tool and the jobs APIs. It protects a small daily Adzuna quota.

It owns:
- `Fetch` and `FetchResult`, the typed interface
- source choice and fan-out
- the Adzuna and USAJOBS HTTP clients and mappers
- Duplicate coalescing (`coalesce`)
- L1, L2, the budget guard, expiry and sweep
- jobs-data replay, and the test fake

It does **not** own:
- the LLM-facing `search_jobs` schema, tool args → `Fetch`, or when to page (⏳ Collection)
- when to raise a Caveat and its wording (⏳ Collection). The Gateway only supplies the data.
- rendering "The Adzuna API" attribution (⏳ Brief)
- keeping federal pay apart from Adzuna salary Stats (⏳ Analysis)
- a daily budget shared across concurrent Runs (⏳ Infra shell)

## 2. Layout and conventions

```
src/talent_scout/gateway/
  types.py     # Fetch, FetchResult, SourceOutcome, CacheStatus, errors, ADZUNA_CURRENCY, ATTRIBUTION
  coalesce.py  # coalesce(), the one Duplicate rule
  http.py      # the shared retry loop
  adzuna.py    # AdzunaClient, one-result mapper
  usajobs.py   # UsajobsClient, one-result mapper, Domain table (pass 2)
  store.py     # gateway_db: L1, budget, L2 (pass 2), _purge()
  gateway.py   # JobsGateway, make_gateway()
  testing.py   # FakeGateway
```

- Kernel conventions apply: `uv`, Python 3.12, `pytest`, Pydantic v2 with `ConfigDict(frozen=True, extra="forbid")`, `StrEnum`, `date` for dates.
- **Imports:** `gateway/` imports `kernel.types` and `kernel.settings`. Nothing in the Kernel imports the Gateway.
- `ADZUNA_CURRENCY` sits in `types.py` because the `Fetch` validator needs it, and `adzuna.py` already imports `Fetch`.
- `httpx` is a transitive dependency today. Pin it directly (`httpx==0.28.1`, the installed version).

## 3. Interface (`gateway/types.py`)

```python
class Fetch(BaseModel):
    title: str                   # one Search Plan title; non-blank
    country: str                 # a key of ADZUNA_CURRENCY; "us" adds USAJOBS
    location: str                # blank = country-wide
    radius_km: int               # >= 0
    max_days_old: int            # >= 1
    category: str | None         # Adzuna tag
    page: int = 1                # >= 1, same page of each source

class CacheStatus(StrEnum): hit, miss, replay, store     # store is pass 2

class SourceOutcome(BaseModel):
    total: int                   # the source's match count; L2's own count when cache == store
    dropped: int                 # mapper drops (Caveat input); 0 when cache == store
    cache: CacheStatus
    fetched_at: datetime         # when this data came from the API
    calls_left: int | None       # None = unmetered (USAJOBS)

class FetchResult(BaseModel):
    postings: list[Posting]      # coalesced survivors
    merged: dict[str, list[str]] # kept key -> Duplicate keys
    sources: dict[Source, SourceOutcome]  # sources that answered
    failures: dict[Source, str]  # sources that failed

class JobsGateway:
    async def fetch(self, f: Fetch) -> FetchResult: ...
    # used as `async with`, which opens and closes one httpx.AsyncClient per source

def make_gateway(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> JobsGateway: ...
```

- **Plain typed Python, not GraphQL:** one in-process caller and no work removed.
- **Named `Fetch`,** because the glossary avoids "query" and "search" for the Hiring Request.
- **Validation:** a validator lowercases, strips and collapses whitespace in `title`, `location` and `category`, so equal Fetches are equal objects. Any `country` outside `ADZUNA_CURRENCY` is rejected: it's a planning bug, not a source failure. The [Request & Plan LLD](request-plan.md) §6 constrains the Search Plan to the same table, which moves to `kernel/types.py`.
- **One title per Fetch.** Adzuna's `what_or` ORs single words, so title variants can't be combined. Each variant is its own Fetch and its own L1 key.
- **One page per call.** A `Fetch` asks for page N of each source, so one call costs at most one logical API call per source. Page size is a client constant (50 for both). Collection decides whether another page is worth it, from `total` and `calls_left`.
- **No `sources`, work mode or target count.** The source rule picks sources, `Posting` can't carry a work mode, and L2 doesn't need a target (§11).
- **`total` is disclosure only.** It may appear in Run Notes or a Caveat, labelled as the source's own match count ("Analysed 50 of about 3,200 Adzuna matches"), and is never a Stat, Evidence or a demand figure ([Adzuna aggregate endpoints](../../.scratch/gateway-lld/issues/06-adzuna-aggregate-endpoints.md)). With `cache == store` it isn't Adzuna's count, so it can't feed that disclosure.
- `ATTRIBUTION[Source.adzuna] = "The Adzuna API"` is exported from here.

## 4. Fetch flow

**Source choice:** Adzuna always, USAJOBS when `country == "us"`. Sources run concurrently. The model never picks a source.

Each source is resolved independently, first answer wins:

| # | Step | Sources | `cache` | Then |
|---|---|---|---|---|
| 1 | Replay file, when `REPLAY_CACHE` is set (§10) | both | `replay` | Skips the close-date filter and the replay write |
| 2 | Fresh L1 row, younger than `l1_ttl_hours` (§8) | both | `hit` | Close-date filter |
| 3 | L2, if it can fill the requested page (§11) | Adzuna, pass 2 | `store` | Never written to L1, which would restart the TTL on old data |
| 4 | Guarded live call (§6, §7, §9) | both | `miss` | Write L1, then L2 for Adzuna, then `_purge()`, then close-date filter |
| 5 | The live call failed: L2's partial page, if it has any matches | Adzuna, pass 2 | `store` | Also fills `failures[adzuna]`, so "one source failed" still fires |
| 6 | Nothing left | both | | `failures[source]` |

When `REPLAY_CACHE` is set, the answer from steps 2 to 5 is also written to the replay file, as served.

Then `fetch` concatenates the sources' Postings, runs `coalesce`, and returns. Rows are written before `fetch` returns, so a kill mid-node re-serves them at no quota cost.

## 5. Errors

| Exception | Raised for | What happens |
|---|---|---|
| `BudgetExhausted(GatewayError)` | guard refusal, Adzuna `429` | per-source: `failures[source]`, other sources still return |
| `SourceUnavailable(GatewayError)` | timeout, connect error or 5xx after retries; a body without `results` / `SearchResult`; USAJOBS `429` | per-source: `failures[source]`, other sources still return |
| `GatewayError` | no source returned anything | raised by `fetch`; Collection's tool turns it into a `ToolMessage` |
| `SourceRejected(Exception)` | `401`, `403`, any other 4xx | propagates and stops the Run (Kernel §9) |
| bugs | anything else | propagate and stop the Run |

- A `SourceRejected` from one source wins over a result from the other. Use `asyncio.gather(..., return_exceptions=True)`, then re-raise anything that isn't a `GatewayError`.
- `SourceRejected` carries the source, status and response body, and **never the URL**.
- **Never call `raise_for_status()`.** Its message contains the full URL, and Adzuna's URL contains `app_id` and `app_key` (checked against `httpx` 0.28.1). That message would reach logs and LangSmith error traces. For the same reason, raise `SourceUnavailable` with `from None` and fixed text.
- If Adzuna's over-quota answer turns out to be a `403`, it fails loudly with the body logged, and `adzuna_daily_limit` gets lowered.

## 6. `coalesce` (`gateway/coalesce.py`)

```python
def coalesce(postings: list[Posting]) -> tuple[list[Posting], dict[str, list[str]]]: ...
```

A pure function, and the one Duplicate rule. The Gateway applies it to each merged result, and ⏳ Collection's `collect` re-applies it across Fetches. Collapsing is a ⏳ `run_log` `note`, not a Caveat. No LLM or Jev. See [Gateway query interface](../../.scratch/gateway-lld/issues/02-gateway-query-interface.md).

**Two Postings are Duplicates when all hold:**
1. Same normalised title and same normalised employer.
2. Descriptions agree: after normalising (lowercase, non-word characters to spaces, trailing partial word dropped), the shorter is a prefix of the longer.
3. Same `salary`, unless either salary is `predicted`.

Location and date are ignored, so a multi-location ad counts as one job; the dropped locations are recoverable from `merged`.

**Survivor:** USAJOBS over Adzuna (close date, full text, real pay range), then the most recent `posted_at`, then the lowest `key`.

**Test cases from `tests/fixtures/jobs/`:**
- Collapse: Deloitte "Data Engineer III" (3 locations, same snippet), Capital One "Data Engineer 4" (3 reposts, predicted salaries differ), a re-announced USAJOBS ad (same text, second hiring path).
- Keep apart: Booz Allen's 15 DC "Data Engineer" requisitions (every description differs), FAA FV/FG pairs (different pay plans), NAVSEA's two "Supervisory General Engineer" ads (same pay, different offices and duties).

No cross-source overlap was seen (all 50 DC Adzuna results are contractors). The prefix form covers it anyway, because the USAJOBS mapper starts `description` with `JobSummary`.

## 7. Clients

Both clients take an `httpx.AsyncClient` and `Settings`, and return one page:

```python
class Page(NamedTuple):
    postings: list[Posting]
    total: int
    dropped: int

async def search(self, f: Fetch) -> Page: ...
```

### 7.1 Shared transport (`gateway/http.py`)

- 10 s timeout. Up to 2 retries (0.5 s, 1 s) on timeout, connect error and 5xx, then `SourceUnavailable`.
- `store.spend(source)` runs before **every** attempt, retries included (§9).
- `200` returns the body. Other statuses are handled as in §5, with the per-source `429` rule below.
- **Secrets:** `app_id` and `app_key` are query params and `httpx` logs URLs at INFO, so `make_gateway` sets the `httpx` logger to WARNING. Logs and trace metadata never carry a URL or key.

### 7.2 Adzuna (`gateway/adzuna.py`)

See [Adzuna client and mapper](../../.scratch/gateway-lld/issues/03-adzuna-client-and-mapper.md). `GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}`.

| Param | Value |
|---|---|
| `app_id`, `app_key` | from `Settings` |
| `title_only` | `Fetch.title`. Never `what` or `what_or`: matching the title cuts keyword collisions, and synonyms come from title variants |
| `where`, `distance` | `location`, `radius_km`. Both omitted when `location` is blank. `location0..n` is never used |
| `results_per_page` | always `50`. Adzuna silently caps at 50 |
| `max_days_old` | always |
| `sort_by` | `date`, so page N walks back in time; repeats from shifting pages are caught by `key` |
| `category` | when set |

No salary or `contract_*` filters. `Page.total = count`. A body without a `results` list is `SourceUnavailable`.

`429` sets today's budget to spent (§9) and raises `BudgetExhausted`, with no retry.

```python
ADZUNA_CURRENCY = {
    "gb": "GBP", "us": "USD", "ca": "CAD", "au": "AUD", "nz": "NZD", "in": "INR", "sg": "SGD",
    "za": "ZAR", "br": "BRL", "mx": "MXN", "pl": "PLN", "ch": "CHF",
    "at": "EUR", "be": "EUR", "de": "EUR", "es": "EUR", "fr": "EUR", "it": "EUR", "nl": "EUR",
}
```

**Mapper** (one raw result → `Posting`). `title`, `company` and `description` are trimmed and whitespace-collapsed, nothing more. The trailing `…` stays, since `coalesce` normalises it away. No HTML stripping, because none was seen in 100 results.

| `Posting` | From |
|---|---|
| `source_id` | `id` |
| `title` | `title` |
| `company` | `company.display_name`; missing → `None` |
| `location` | `location.display_name` |
| `region` | `tuple(location.area)` as given, country first; missing → `(country.upper(),)` |
| `domain` | `category.tag`; `graduate-jobs`, `part-time-jobs`, `other-general-jobs`, `unknown` or missing → `None` |
| `posted_at` | UTC date of `created` |
| `closes_at` | `None` |
| `description` | `description` |
| `url` | `redirect_url` with `utm_source` and `utm_medium` removed, every other param kept. `utm_source` is our app id, and `se`/`v` may be needed by the landing page |
| `salary` | see below |

**Salary:** both bounds missing or ≤ 0 → `None`. One bound → just that bound. Reversed → swapped. `currency` from the table, `period = unknown`, `predicted = str(salary_is_predicted) == "1"` (accepts `"1"` and `1`). Predicted salaries are kept, and Analysis decides how to treat them. Every salary in the live sample was predicted, with `min == max`.

**Drop:** a result whose mapping raises `KeyError`, `TypeError`, `ValueError` or `ValidationError`. It's counted in `dropped` and logged once with its id. No salary, a non-Domain category or no company is not a drop.

### 7.3 USAJOBS (`gateway/usajobs.py`, pass 2)

See [USAJOBS client and mapper (pass 2)](../../.scratch/gateway-lld/issues/05-usajobs-client-and-mapper.md). `GET https://data.usajobs.gov/api/Search`, with headers `Host: data.usajobs.gov`, `User-Agent: <usajobs_user_agent>`, `Authorization-Key: <usajobs_api_key>`.

| Param | Value |
|---|---|
| `PositionTitle` | `Fetch.title`, in the API's default relevance order. It matches any word; the Relevance stage removes the extras |
| `ResultsPerPage` | `50`, about 1 MB |
| `Page` | `Fetch.page` |
| `DatePosted` | `min(max_days_old, 60)`. The API silently caps at 60 |
| `LocationName`, `Radius` | `location`, `ceil(radius_km / 1.609)`. `Radius` behaves like miles. Both omitted when `location` is blank |

- `Fields` isn't sent, and `sort=opendate` isn't used: it puts unrelated engineers ahead of real matches.
- `Fetch.category` is ignored, so a Posting can return with a different Domain from the one asked for. Filtering after mapping would shorten pages and falsify `total`.
- `Page.total = SearchResult.SearchResultCountAll`. A body without `SearchResult` is `SourceUnavailable`.
- `429` is `SourceUnavailable`, with no lockout, since there's no limit to protect.
- A multi-word country-wide search can time out (seen at 20 s and 25 s). It ends in `failures[usajobs]`, and Adzuna's results still return. Raising the timeout wouldn't help.

**Mapper.** Each entry of `SearchResult.SearchResultItems` has `MatchedObjectId` and a `MatchedObjectDescriptor` (`d`). Text fields follow the Adzuna rule.

| `Posting` | From |
|---|---|
| `source_id` | `MatchedObjectId` |
| `title` | `d.PositionTitle` |
| `company` | `d.OrganizationName` (the agency, not the department) |
| `location` | `d.PositionLocationDisplay` |
| `region` | see below |
| `domain` | §7.4 |
| `posted_at` | date of `d.PublicationStartDate`; missing or unparseable is a **drop**. No timezone, so the date is taken as written |
| `closes_at` | date of `d.ApplicationCloseDate`; unparseable → `None` |
| `description` | `Details.JobSummary`, `Details.MajorDuties` (list joined), `d.QualificationSummary`, in that order, collapsed, cut at 4,000 characters. `Details` is `d.UserArea.Details` |
| `url` | `d.PositionURI` with `:443` removed |
| `salary` | see below |

- **Blank description is a drop.** An empty description is a prefix of every other, so `coalesce` would merge it with any Posting of the same title and employer.
- **Salary:** the first `d.PositionRemuneration` entry only. `PA`/`PH`/`PD`/`BW`/`PM` → annual, hourly, daily, biweekly, monthly. `SY`/`PW`/`FB`/`ST`/`WC` → `salary = None`, because those figures can't be compared. Bounds (`MinimumRange`, `MaximumRange`, strings) ≤ 0 are ignored, and reversed ones swapped. `currency = "USD"`, `predicted = False`.
- **Federal pay label:** `source == usajobs`. Every USAJOBS salary is federal pay, so a new field would only repeat it.
- **Region:** each `d.PositionLocation` becomes `(country, CountrySubDivisionCode, CityName)`, with `United States` written `US` and the `, State` suffix removed from `CityName`. One location uses its hierarchy. Several use the common prefix (two Virginia sites → `("US", "Virginia")`, FAA's 1,176 → `("US",)`). Mixed countries or no locations → `("US",)`. Overseas Postings are kept, country first.
- `RemoteIndicator` and `TeleworkEligible` are ignored: `Posting` has no field for them, and the display string already says "Anywhere in the U.S. (remote job…".
- FAA "Public Notice" talent-pool announcements stay normal Postings, since the mapper doesn't judge relevance.

Other drops follow the Adzuna rule.

### 7.4 USAJOBS Domain table

A static dict in `usajobs.py`, reading the first `d.JobCategory` entry's `Code` (the series). Series overrides win over the family. The family is the series' first two digits plus `00`. In the 822-entry code list the only exception is series `8999`, whose family is `8800`, so it needs its own override into `maintenance-jobs`. An unknown series → `None`, logged once.

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
| `maintenance-jobs` | 1600, 4800, 5300, 5800, 8200, 8600, 8800 | 8999 |
| `teaching-jobs` | 1700 | |
| `logistics-warehouse-jobs` | 2000, 2100, 5700, 6900, 7000 | |
| `it-jobs` | 2200 | 0391, 0854, 1550, 1560 |
| `trade-construction-jobs` | 2500, 2600, 2800, 3600, 3800, 4100, 4200, 4600, 4700 | |
| `manufacturing-jobs` | 3100, 3300, 3400, 3700, 4000, 4300, 4400, 5200, 5400, 6500, 6600 | |
| `domestic-help-cleaning-jobs` | 7300 | |
| `hospitality-catering-jobs` | 7400 | |
| `None` | 0000, 1400, 1800, 2300, 3500, 5000, 7600, 9900 | 1102, 1105 |

Domain stays an Adzuna tag, so there's no local `law-enforcement` Domain.

## 8. L1 cache (`gateway/store.py`)

See [L1 cache, budget guard and replay](../../.scratch/gateway-lld/issues/04-l1-cache-budget-guard-and-replay.md). `gateway_db` is the Gateway's own SQLite file, using stdlib `sqlite3` in autocommit mode, called directly from async code like the Kernel's replay cache. Its parent directory is created on open.

```sql
l1(source TEXT, fetch TEXT, postings TEXT, total INT, dropped INT,
   fetched_at TEXT, expires_at TEXT, PRIMARY KEY (source, fetch))
```

- **Key:** `(source, fetch.model_dump_json())`. It's already normalised and holds no credentials, unlike the request URL.
- **Value:** one source's mapped Postings, stored before `coalesce`. Lean, and nothing in it can leak the Adzuna app id. This reverses the HLD's raw response.
  - A mapper fix doesn't reach cached rows until they're refetched. Delete `gateway_db` if it can't wait.
  - A row that no longer validates against `Posting` is a miss.
- **Stored:** valid 2xx bodies, including empty result lists. Never failures or bodies without a results list.
- **Refetch:** after `l1_ttl_hours` (24, both sources), a row stops being served, and the next identical Fetch calls the API and overwrites it. A stale row is never served when the budget has run out; L2's fallback is the place for that reuse.
- **Delete:** `expires_at = max(closes_at)`, or `NULL` if any Posting has no close date or the row is empty. So Adzuna rows and empty rows are never purged, only overwritten. See §12.
- **Close-date filter:** on normal hits and fresh responses, remove each Posting past its `closes_at`. These don't count in `dropped`.

## 9. Budget guard (`gateway/store.py`)

```sql
budget(source TEXT, utc_day TEXT, used INT, PRIMARY KEY (source, utc_day))
```

- Both sources are counted. Only Adzuna has a limit (`adzuna_daily_limit`, 25, from the account dashboard), so USAJOBS reports `calls_left = None`. No per-minute limit was reported.
- To hold calls back for a walkthrough, lower the setting in `.env`. There's no reserve setting.
- The day boundary is UTC, since Adzuna's reset time is undocumented. If it differs, a `429` catches it.
- `store.spend(source)` runs before every HTTP attempt, retries included. It's one atomic statement, after `INSERT OR IGNORE` of today's row:

  ```sql
  UPDATE budget SET used = used + 1 WHERE source = ? AND utc_day = ? AND used < ? RETURNING used
  ```

  No returned row raises `BudgetExhausted`.
- Cache hits don't count. L1 is checked first, so a fresh row is still served once the budget runs out.
- **On an Adzuna `429`:** set today's `used` to the limit, so the refusal survives restarts until the next UTC day. Deleting the row clears it by hand.
- Responses carry no rate-limit headers, so the guard's count is the only signal. A one-page call can spend up to 3 calls.
- **What a Run sees:** `failures[adzuna]`, with USAJOBS still returning for `us`. Outside the US every source has failed, so `GatewayError` becomes a `ToolMessage`.

## 10. Replay

`REPLAY_CACHE` switches on jobs-data replay too (Kernel §14). See [L1 cache, budget guard and replay](../../.scratch/gateway-lld/issues/04-l1-cache-budget-guard-and-replay.md).

- **Where:** a `jobs` table in the replay file, next to `llm` and `jev`, so one file is a self-contained recorded Run. Add `get_jobs`/`put_jobs` to the Kernel's `Replay` and get it from `open_replay`, as Jev does. Same columns as L1, minus `expires_at`.
- **Budget counters always stay in `gateway_db`,** otherwise a new replay path would reset the count.
- **Read-through, like Jev (Kernel §11):** the steps in §4. A failing miss was rejected, because a recording Run could then never fill the file without a second setting.
- **Reports:** a replay hit is `cache = replay` with `fetched_at` from the row. A live call during replay is `miss`.
- **Written as served,** after the close-date filter, so a replay returns what the recording Run returned.
- **Never purged, ignores the TTL, skips the close-date filter on read.** Filtering would make Postings vanish as dates pass, change the prompts and miss every LLM cache entry. ⏳ Collection's age Caveat discloses the staleness.
- A replay hit returns before L2, so a replayed Run stays reproducible.

## 11. L2 store (`gateway/store.py`, pass 2)

See [L2 store, expiry and sweep (pass 2)](../../.scratch/gateway-lld/issues/07-l2-store-expiry-and-sweep.md). L2 skips Adzuna calls on an L1 miss and backs failed live calls. It adds two savings over L1: the same search after 24 hours, and overlapping searches.

**Adzuna only.** USAJOBS calls are free and its Postings match poorly (nationwide notices at `("US",)`, Domains that differ from the one asked for, any-word titles). This reverses the HLD's original "every Posting is stored".

```sql
l2_postings(key TEXT PRIMARY KEY, country TEXT, via TEXT, posting TEXT, last_seen_at TEXT)
-- plus one index on last_seen_at
```

- **Write:** every live Adzuna response, from any page, before `coalesce`, with `INSERT ... ON CONFLICT(key) DO UPDATE`. The newest version wins. `via` is that `Fetch`'s JSON. `last_seen_at` is now.
- **Read:** `WHERE country = ? AND last_seen_at >= ?`, then the reuse rule in Python, checking `via` before validating the Posting. A row that no longer validates is skipped. Mark the read with `# ponytail: full scan of about 8,750 rows (25 calls x 50 x 7 days), add Region and Domain columns if the budget grows`. Measured at 23–39 ms for 7,000 rows, against 800–2,500 ms for an Adzuna call.
- **Dropped from the schema:** Region and Domain columns, `first_seen` (nothing reads it) and raw responses (§8).

**Reuse rule.** A stored Posting is reused only if the `Fetch` that last returned it (`via`) was at least as broad as the new one. Otherwise "senior data engineer" Postings would fill a later "data engineer" request and push its salary Stats up.

`via` must have:
- the same country
- every word of `via.title` in the new title
- the same location, or a blank `via.location`
- `via.radius_km` ≥ the new radius
- `via.category` of `None` or the same category

The Posting must have:
- every word of the new title in `Posting.title`, compared as lowercase word tokens (what `title_only` would require)
- `posted_at` within `max_days_old`
- `domain == category`, if a category was given
- if `via` was country-wide and the new location isn't blank: the new location equal to one `region` segment, case-insensitive

| Stored `via` | New `Fetch` | Result |
|---|---|---|
| "data engineer", London | "senior data engineer", London | Reused, only the senior jobs |
| "senior data engineer", London | "data engineer", London | Live call |
| "data engineer", Camden | "data engineer", London | Live call |
| "data engineer", UK-wide | "data engineer", Camden | Reused, Camden jobs only |

Known limits:
- A wider stored radius can return a few Postings outside the new radius.
- A later, narrower `Fetch` overwrites `via`, which can cost an extra call but never skews the Sample.
- A country-wide `via` carries whatever `radius_km` it was given, so a small value fails the radius check and costs an extra call.

**"Enough" means a full page.** Matches sort newest first, then by key, like `sort_by=date`. L2 serves page N only if slice `(N-1)*50 .. N*50` is full, so it never returns less than a live call would. Otherwise the call goes live, and any overlap is removed by key in `collect`. Only the failure fallback serves a partial page. `Fetch` needs no target count.

**Outcome fields:** `cache = store`, `total` = L2's match count, `dropped = 0`, `fetched_at` = the oldest `last_seen_at` served, `calls_left` = current. A read-before-call hit spends no budget. ⏳ Whether an L2 answer's age raises a Caveat is Collection's.

## 12. Expiry and sweep (pass 2)

- **Hard expiry:** a passed `closes_at`. USAJOBS only, so it applies to L1 alone (§8).
- **Soft expiry:** `l2_fresh_days` (7) since Adzuna last returned the Posting (`last_seen_at`). Only a live call moves it, so serving from L2 doesn't extend it. A search can therefore go about a week without spending a call.
- `Fetch.max_days_old` separately limits how old the ad is, per request, and every Adzuna search passes it.
- **Read filters** hide expired rows whether or not they've been deleted yet.

**Sweep.** A single `store._purge()` runs straight after each live write:

```sql
DELETE FROM l2_postings WHERE last_seen_at < :cutoff;
DELETE FROM l1 WHERE expires_at < :today;
```

The tables only grow on a live write, so nothing else needs to trigger it, and cache hits and opening the Gateway do no sweep work. This reverses HLD §7's original "sweep at the start of each Run" and the L1 ticket's "when the Gateway opens". Measured on a worst-case table: 0.01 ms with nothing to delete, 4 ms for 350 rows. ⏳ The Infra shell's scheduled job can call the same method later.

## 13. Tracing

Each source call is a LangSmith child run `gateway:<source>`, with metadata `source`, `page`, `cache` and `calls_left`, and a summary output (count, dropped, total), not the Postings. Never the URL or a key. The exact `traceable` API gets checked at build time, through the `langchain-router` skill.

From pass 3, `fetch` also emits one `api_called` custom event per source for the live view, through the Kernel's guarded `emit()`, which does nothing outside a graph. See the [Runtime LLD](runtime.md) §10.

## 14. Settings

All in Kernel §13 and already in `kernel/settings.py`: `adzuna_app_id`, `adzuna_app_key`, `usajobs_api_key`, `usajobs_user_agent`, `replay_cache`, plus:

| Setting | Default |
|---|---|
| `gateway_db` | `.cache/gateway.sqlite` |
| `adzuna_daily_limit` | 25 |
| `l1_ttl_hours` | 24 |
| `l2_fresh_days` | 7 |

The page size (50) is each client's constant, not a setting.

## 15. Test seams

Fills the Jobs APIs row of Kernel §15.

| Tests | Use | Runs |
|---|---|---|
| Gateway | `make_gateway(settings, transport=httpx.MockTransport(...))` serving `tests/fixtures/jobs/`, with `gateway_db` under `tmp_path` | the real clients, mappers, L1 and guard |
| Stages | `FakeGateway(results)` in `gateway/testing.py`, returning canned `FetchResult`s from `fetch` | nothing below `fetch`. Matched by duck typing, no `Protocol` |

- Fixtures hold `{status, latency_ms, headers, body}`, with secrets replaced by `REDACTED`. The handler returns `status` and `body`.
- TTL and expiry tests backdate rows in `gateway_db` directly, so no clock needs injecting.

## 16. Build checklist

Each step leaves one small `pytest` file behind. No test spends live quota.

**Pass 1 (walking skeleton):** Adzuna, L1, budget guard, replay.
1. Pin `httpx`. `types.py`. Test: the validator normalises text, equal Fetches dump equal JSON, and an unknown country is rejected.
2. `coalesce.py`. Test: the Deloitte and Capital One cases collapse, Booz Allen stays apart, and the survivor order holds.
3. `http.py`, `adzuna.py`. Test on `adzuna_search.json`: 50 Postings, no `utm_` params in `url`, `predicted` true, non-Domain tags → `None`. Reversed and missing salaries. A bad result is counted in `dropped`. `5xx` retries then `SourceUnavailable`. A `401` raises `SourceRejected` with no key in its message.
4. `store.py`: L1 and budget, writing `expires_at` from the start so the schema doesn't change in pass 2. Test: the guard refuses at the limit and the count survives reopening, retries spend, a `429` locks the day, and a row past its TTL misses.
5. `gateway.py`: steps 1, 2, 4 and 6 of §4, tracing (§13), and the `httpx` logger level. Test: a repeat Fetch is a `hit` at no spend, a failed source fills `failures`, `GatewayError` fires when nothing returned, and `SourceRejected` propagates.
6. Replay: `get_jobs`/`put_jobs` on `kernel/replay.py`, then the read-through. Test: a recording Run's answer replays with `cache = replay` past its TTL, and a miss goes live and is written.
7. `testing.py`: `FakeGateway`.
8. One live smoke script (not in CI): one `fetch` through the real stack. It spends one Adzuna call, which needs the user's OK.

**Pass 2:** USAJOBS, L2, expiry and sweep.
1. `usajobs.py`. Test on `usajobs_search.json`: the description starts with `JobSummary`, `:443` is gone, FAA's 1,176 locations → `("US",)`, `SY` → `None` salary, the Domain table, and blank description is a drop. A `429` is `SourceUnavailable` with no lockout.
2. Fan-out: `country == "us"` calls both, others call Adzuna only, one source failing still returns the other. Test: a re-announced ad collapses, while NAVSEA's offices and FAA FV/FG stay apart, through `coalesce`.
3. The close-date filter, and `_purge()` for L1. Test: an expired Posting is filtered and not counted in `dropped`, a row is deleted only when all its Postings have closed, and a replay row skips both.
4. L2 in `store.py`, `CacheStatus.store`, and steps 3 and 5 of §4. Test: the four rows of the reuse table, page N served only when full, no spend on a read-before-call hit, the fallback fills both `sources` and `failures`, an L2 answer isn't written to L1, and a replay hit returns before L2.
5. `_purge()` for L2. Test: rows past `l2_fresh_days` are hidden on read and deleted after the next live write.

## 17. Excluded and deferred

- **Adzuna aggregates are excluded from every pass:** `histogram`, `top_companies`, `history` and the search `mean`. They carry no Posting IDs, `histogram` covers an undocumented 44% of matches with 76% in its open top band, the Sample already gives employers and trends, and `mean` may average estimates. See [Adzuna aggregate endpoints](../../.scratch/gateway-lld/issues/06-adzuna-aggregate-endpoints.md).
- Deliberate deferrals are in [future-scope.md](future-scope.md).
- Handed on:
  - ⏳ **Infra shell:** shared daily budget across concurrent Runs, persistence off SQLite, MiniStack if required.
  - ⏳ **Collection:** the `search_jobs` schema, re-applying `coalesce`, the `run_log` note for merged Duplicates, every Caveat's trigger and wording, whether the replay Caveat reports live calls made during replay, and telling Relevance about FAA "Public Notice" announcements and any-word titles.
  - ⏳ **Analysis:** federal pay apart from Adzuna salaries.
  - ⏳ **Brief:** rendering the attribution, and the `total` disclosure with Collection.
  - ⏳ **Delivery:** sample-run strategy within the Adzuna budget, and listing the aggregate exclusion in the README's known limitations.
