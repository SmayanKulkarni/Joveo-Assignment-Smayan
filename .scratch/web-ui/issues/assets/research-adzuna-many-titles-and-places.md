# Research: searching many titles and places on Adzuna

Researched 2026-11-01. No API search was called for this note; the only requests were for documentation pages and spec files. Each claim is marked **Documented** (a primary source says it), **Measured earlier** (recorded from this project's own past calls), **Inferred** (reasoned from the docs), or **Needs a live check**.

## Sources

| Key | Source | What it is |
|---|---|---|
| [OAS] | https://developer.adzuna.com/swagger/spec/test2.json | OpenAPI 3.1 spec behind Adzuna's interactive docs. Treated as the current parameter reference |
| [SW] | https://api.adzuna.com/v1/api-docs/adzuna | Older Swagger 1.2 spec, still served |
| [SEARCH] | https://developer.adzuna.com/docs/search | Adzuna search guide |
| [REGION] | https://developer.adzuna.com/docs/regional | Adzuna guide to `locationN` |
| [TOS] | https://developer.adzuna.com/docs/terms_of_service | Adzuna API terms |
| [UJ] | https://developer.usajobs.gov/api-reference/get-api-search | USAJOBS search reference |
| [UJR] | https://developer.usajobs.gov/guides/rate-limiting | USAJOBS rate limiting guide |
| [SMOKE] | [Live smoke test](../../../gateway-lld/issues/01-live-smoke-test-adzuna-usajobs.md) | This project's measured calls, US only |
| [L1] | [L1 cache and budget guard](../../../gateway-lld/issues/04-l1-cache-budget-guard-and-replay.md) | Records the owner's dashboard limit |

## Bottom line

Budget on one Adzuna call per title, per place, per page. Several multi-word titles cannot share a call by any documented means, and `where` takes one centre. The way to save calls is to widen one search area rather than add places: one `where` with a wide radius, or one `locationN` region. Whether that actually catches Navi Mumbai and Thane needs a live check.

## 1. Can several titles share one call?

**Documented**

- `what_or`: "any keywords may be found", with terms space separated [OAS]. [SW] also allows commas. It takes keywords, and nothing describes grouping them into titles.
- `what_phrase`: "An entire phrase which must be found in the description or title" [OAS]. It is a single phrase, with no OR form.
- `what`: keywords, space separated [OAS]. Neither spec mentions quotes or phrase syntax.
- `title_only`: "Keywords to find, but only in the title", space separated [OAS]. Neither spec says whether several terms must all match or any may match.
- `count` is "The total number of advertisements found" [SW]. `sort_by` accepts `default`, `hybrid`, `date`, `salary` and `relevance` [OAS]. No primary source explains how relevance is computed.

**Inferred**

- `what_or=data engineer analytics engineer` means any of the words `data`, `engineer`, `analytics`, not either title. This agrees with the existing rule in `docs/lld/gateway.md`.
- OR-ing words can only grow `count` and bring in unrelated titles. So `count` stops measuring the market for a title, and pages fill with postings that must be filtered afterwards.
- The client sends `sort_by=date` (`adzuna.py`), so relevance plays no part in ordering today. Noise from an OR would be spread through the pages by date, not pushed to the end. Switching to `relevance` would break the "page N walks back in time" assumption.
- Single-word variants of one title (`developer`, `programmer`) are the only documented case where sharing a call is safe in principle.

**Needs a live check**

- Whether `what_or` combines with `title_only` so the OR applies to titles only. The docs do not describe combining them, and this is the one experiment that could change the conclusion.
- Whether quoted phrases work in `what`, `what_or` or `title_only`.
- Whether `title_only=data engineer` needs both words. `docs/lld/gateway.md` assumes it does.

## 2. Can `where` take several places?

**Documented**

- `where` is "The geographic centre of the search" [OAS]: one string, one centre. No multi-value form appears in either spec.
- `distance` is in kilometres from that centre [OAS][SW]. The default differs: 5 km in [OAS], 10 km in [SW]. This does not affect us, because the client always sends `distance` with `where`.
- `location0`..`location7` describe one place in a hierarchy, for example `location0=UK&location1=South East England&location2=Surrey` searches that county [OAS][REGION]. Again that is one path per call, but it can cover a whole region.
- `in` is a supported country [OAS][SW].

**Inferred**

- Each separate place needs its own call, unless one radius or one region covers them all.

**Indian places: nothing documented**

No Adzuna source mentions Indian place names, how they resolve, or how Indian ads are geocoded. All of the project's measured calls were US [SMOKE].

As a rough estimate from general geography, not from a cited source, Thane and Navi Mumbai sit a few tens of kilometres from central Mumbai. A radius near 40 to 50 km around `where=Mumbai` should reach them geometrically, within the plan's 0 to 100 km limit. Whether it does in practice depends on things only a live call can show.

**Needs a live check**

- Whether `where=Navi Mumbai` and `where=Thane` resolve, and to what. Adzuna does not document what happens to an unknown place.
- Where Adzuna puts the centre of `Mumbai`, and whether `where=Mumbai&distance=50` returns ads whose `location.area` names Thane or Navi Mumbai.
- Whether radius search works for ads located only at city or state level.
- What `location.area` looks like for India, and so whether `location0=India&location1=Maharashtra` is a usable one-call region. Results from a Mumbai search will show this.

A small test would be about 4 calls: `where=Mumbai` at a wide radius, `where=Thane`, `where=Navi Mumbai`, and one `location0`/`location1` search. Compare `count` and the `area` values.

## 3. Free-tier limits

**Documented:** no public number. The terms say the free tier "is intended for evaluating the API" and "The plans available to you, and their limits, are shown in your account", and that limits may change [TOS]. The spec lists only 400, 404, 410 and 500 responses, with no quota error [OAS].

**Project record:** the owner read **25 calls a day** from the account dashboard, with no per-minute limit reported [L1]. That is the best figure we have, but it is not public, and the dashboard should be re-read before planning around it.

**Unverified:** third-party pages cite different figures (25 a minute with 250 a day, or about 1,000 a month). Search snippets attribute a similar set to Adzuna's terms, but the terms page fetched today has no such numbers. Do not use these.

**A correction to the ticket:** `MAX_FETCHES` is not the 25. It is 6 searches per Attempt, so 18 over 3 Attempts (`collection/nodes.py`). The 25 is `adzuna_daily_limit`, enforced by the budget guard in `gateway/store.py`.

**The cost**

Calls = titles x places x pages, at up to 50 postings a page. The cap of 50 is enforced silently [SMOKE].

| Titles | Places | Pages | Calls | Share of 25 a day |
|---|---|---|---|---|
| 1 | 1 | 1 | 1 | 4% |
| 2 | 3 | 1 | 6 | 24%, one full Attempt |
| 4 | 1 | 1 | 4 | 16% |
| 4 | 3 | 1 | 12 | 48%, exceeds `MAX_FETCHES` |
| 4 | 3 | 2 | 24 | 96% |
| 4 | 5 | 1 | 20 | 80% |

Today's `MAX_FETCHES` of 6 allows only about 2 titles x 3 places, first pages only, in one Attempt. Broadening repeats the spend, and L1 and L2 reuse may reduce it. [SEARCH] adds nothing further on cost. Retries also count, since the guard counts each HTTP attempt (`store.py`).

## 4. USAJOBS

**Documented**

- `LocationName` accepts several values, separated by semicolons [UJ].
- `Keyword` and `PositionTitle` are not marked as multi-value, unlike the ten parameters that are [UJ]. `Keyword` searches for "all of the words specified (or synonyms of the word)", and `PositionTitle` is a "contains" match [UJ].
- `Radius` expands `LocationName` [UJ]. Its behaviour across several locations is not stated.
- Search limits: 500 rows a page, 10,000 a query. No call quota is stated [UJR].

**Measured earlier**

- `;` is the working separator on a multi-value series code: `2210;1550` gave 424, `2210:1550` gave 0 [SMOKE].
- `Radius` behaves like miles [SMOKE].
- Rows are about 85 KB each, so the client's page size of 50 is worth keeping [SMOKE].

**Inferred:** several places can share one call, but each title needs its own call. Since USAJOBS calls aren't limited in the code, this matters little for quota.

**Needs a live check**

- `LocationName=A;B` itself, as the measured test used a different parameter.
- `LocationName=A;B&Radius=N`.
- Whether `PositionTitle=A;B` is accepted despite not being documented.

## Live check, 2026-11-01

Five real calls on `in`, `title_only=marketing`, `max_days_old=30`, first page, counted by the budget guard. This settles most of section 2 for this metro. One title and one day only, so it is evidence, not a rule for every place.

| Search | `count` | `area` values on the page |
|---|---|---|
| `where=Mumbai&distance=5` | 110 | Mumbai and its suburbs |
| `where=Mumbai&distance=50` | 122 | Mumbai, plus Navi Mumbai and Thane |
| `where=Thane&distance=10` | 6 | Thane, Bhiwandi, Rabale, one Mulund West |
| `where=Navi Mumbai&distance=10` | 9 | Navi Mumbai, two Govandi |
| `location0=India&location1=Maharashtra` | 204 | Mumbai, Pune, Nagpur and others |

- `where=Thane` and `where=Navi Mumbai` both resolve.
- Mumbai at 50 km reaches both. The three smaller searches overlap by the 3 Mumbai-area ads above, and 110 + 6 + 9 - 3 = 122, so nothing was missed here.
- `location0` and `location1` work for India, but Maharashtra is wider than a metro, so it isn't a substitute.
- `location.area` for India reads country, state, city, then locality. Some ads have the country alone.

Still unchecked: `what_or` with `title_only`, quoted phrases, and USAJOBS with several locations. No decision waits on them.
