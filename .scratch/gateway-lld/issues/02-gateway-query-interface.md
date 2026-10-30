# Gateway query interface

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

What is the Gateway's public interface that Collection's tools call?

- **Query type**: fields (title variants, location, distance, freshness / `max_days_old`, source(s), how many Postings or pages), validation, and how it normalises for cache keys.
- **Result**: Postings, mapper-dropped count, cache provenance (hit or miss, fetched-at age, replayed), per-source failure (feeds Collection's "one source failed" Caveat).
- **Shape of the call**: one `search(query)` across sources vs one per source; async (`httpx.AsyncClient`, already a LangChain dependency) to match the Kernel; who pages (Gateway to a target vs one page per tool call).
- **Errors**: budget refused, source down, bad credentials; which propagate and which become a result field.
- **Tracing**: whether Gateway calls are LangSmith runs, and what metadata (source, cache hit, calls left).
- **API style**: a plain typed Python function/class vs a GraphQL layer federating the sources. Recommendation at charting was plain Python: the Gateway is an in-process library with one caller and no network boundary, every caller wants the same flat `list[Posting]`, and source unification happens in the mapper either way, so GraphQL would add a schema server and resolvers without removing any work. GraphQL could be reconsidered for the Infra shell's external API (out of scope here).

Input from [Live smoke test: Adzuna and USAJOBS](01-live-smoke-test-adzuna-usajobs.md): Adzuna pages cap at 50 silently (`count` 3,200 for a common role), so "who pages" decides how many quota calls one tool call can burn. Adzuna takes 0.8–2.5 s per call; USAJOBS returns ~85 KB per item.

## Answer (2026-10-30)

Grilled with the user. One Adzuna call spent (call 6) on "data engineer", Washington DC, to see real cross-source overlap: [adzuna_search_dc.json](../../../tests/fixtures/jobs/adzuna_search_dc.json).

**Shape**
- **Plain typed Python, not GraphQL.** One class, `JobsGateway`, built from the Kernel's `Settings`, with its HTTP clients as constructor arguments (the exact test seam is decided in [L1 cache, budget guard and replay](04-l1-cache-budget-guard-and-replay.md)). GraphQL would add a schema server and resolvers with one in-process caller and no work removed.
- **Async.** `async def fetch(f: Fetch) -> FetchResult`, one `httpx.AsyncClient` per source client, opened and closed with `async with JobsGateway(...)`. Sources run concurrently.
- **The Gateway fans out and merges.** Collection exposes **one** `search_jobs` tool, not one per source. The Gateway picks sources by rule: Adzuna always, USAJOBS when `country == "us"`. This reverses HLD §2's "the model decides which to call" (HLD and its ticket updated).
- **One page per call.** A `Fetch` asks for page N of each source, so one call costs at most one API call per source. Page size is a client constant (Adzuna 50; USAJOBS set in its mapper ticket). Collection decides whether another page is worth it, using each source's `total` and `calls_left`.
- **Tracing.** Each call is a LangSmith child run `gateway:<source>`, with metadata `source`, `page`, `cache`, `calls_left` and a summary output (count, dropped, total), not the Postings. The exact `traceable` API gets checked at build time.

**Types** (`gateway/types.py`, frozen, `extra="forbid"`). Named `Fetch`/`FetchResult` because the glossary avoids "query" and "search" for the Hiring Request.

```python
class Fetch(BaseModel):
    title: str                   # one Search Plan title; non-blank
    country: str                 # ^[a-z]{2}$; "us" adds USAJOBS
    location: str
    radius_km: int               # >= 0
    max_days_old: int            # >= 1
    category: str | None         # Adzuna tag
    page: int = 1                # >= 1, same page of each source

class CacheStatus(StrEnum): hit, miss, replay

class SourceOutcome(BaseModel):
    total: int                   # source's match count
    dropped: int                 # mapper drops (Caveat input)
    cache: CacheStatus
    fetched_at: datetime         # replay Caveat age (Kernel §14)
    calls_left: int | None       # budget guard; None = unmetered

class FetchResult(BaseModel):
    postings: list[Posting]      # coalesced survivors
    merged: dict[str, list[str]] # kept key -> Duplicate keys
    sources: dict[Source, SourceOutcome]  # sources that answered
    failures: dict[Source, str]  # sources that failed
```

- **One title per Fetch.** Adzuna's `what_or` ORs single words, so title variants can't be combined; each variant is its own Fetch and its own L1 key.
- A validator lowercases, strips and collapses whitespace in `title`, `location` and `category`, so equal Fetches are equal objects. The L1 key is derived in the L1 ticket.
- No `sources` field (the rule above picks them), no work mode (`Posting` can't carry it), no target count (the L2 fog stays open).

**Errors**
- `BudgetExhausted` and `SourceUnavailable` (timeout or 5xx after the client's retries) subclass `GatewayError`. A per-source one is recorded in `failures` and the other source's Postings still return, which is the input for Collection's "one source failed" Caveat.
- `GatewayError` is raised only when every source failed, and Collection's tool turns it into a `ToolMessage`.
- Auth failures (401/403) and bugs propagate and stop the Run (Kernel §9).

**Duplicates** (new glossary term). `coalesce(postings) -> (survivors, merged)`, a pure function in `gateway/`. The Gateway applies it to each merged result, and Collection's `collect` re-applies it over everything gathered across Fetches. One rule, owned by the Gateway; Kernel §3 updated.
- **Rule:** same normalised title, same normalised employer, and descriptions agree: after normalising (lowercase, non-word characters to spaces, trailing partial word dropped), the shorter is a prefix of the longer. They must also have the same Salary, unless either salary is `predicted`. Location and date are ignored. No LLM or Jev.
- **Survivor:** USAJOBS over Adzuna (close date, full text, real pay range), then the most recent `posted_at`, then the lowest key. A multi-location ad counts as one job; the dropped locations are recoverable from `merged`.
- Collapsing is a `run_log` `note`, not a Caveat.
- **Evidence from the fixtures.**
  - The rule collapses Deloitte "Data Engineer III" (3 locations, same snippet), Capital One "Data Engineer 4" (3 reposts weeks apart, all predicted salaries differ) and NAVSEA "Supervisory General Engineer" (3 hiring paths, same pay).
  - It keeps apart Booz Allen's 15 DC "Data Engineer" requisitions (every description differs) and the FAA FV/FG pairs (different pay plans).
  - Title + employer alone would have wrongly collapsed Booz Allen.
- **Cross-source overlap was zero.** All 50 DC Adzuna results are contractors with no federal agency, so Adzuna doesn't appear to carry USAJOBS ads. The prefix form still covers cross-source at no extra cost, *if* the USAJOBS mapper's description starts with the announcement's opening text (handed to [USAJOBS client and mapper (pass 2)](05-usajobs-client-and-mapper.md)).
