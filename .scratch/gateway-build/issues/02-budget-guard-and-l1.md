# 02: Budget guard and L1

**What to build:** the Gateway protects the daily Adzuna quota. A repeat `Fetch` is served from `gateway_db` at no spend, every HTTP attempt is counted first, and once the limit is reached or Adzuna answers `429`, no more calls go out until the next UTC day. A killed process re-serves what it already fetched. Spec: [Gateway LLD](../../../docs/lld/gateway.md) §4 steps 2, 4 and 6, §8, §9, §16 pass 1 steps 4-5.

Out of scope: the close-date filter and deleting L1 rows (ticket 04), though `expires_at` is written from the start so the schema doesn't change then. L2 (ticket 05).

**Blocked by:** 01: Adzuna through fetch.

**Status:** done

- [x] Test: a repeat `Fetch` is a `hit` with no HTTP call and no spend, and a first call is a `miss`
- [x] Test: a fresh row is still served after the budget has run out
- [x] Test: a row past `l1_ttl_hours` misses and is overwritten, and isn't served when the budget has run out
- [x] Test: a row that no longer validates against `Posting` is a miss
- [x] Test: an empty result list is cached, and failures and bodies without `results` aren't
- [x] Test: the guard refuses at the limit, and the count survives reopening `gateway_db`
- [x] Test: retries spend too, one budget call per attempt
- [x] Test: an Adzuna `429` raises `BudgetExhausted` with no retry and locks the UTC day across a reopen
- [x] Test: a refusal ends in `failures[adzuna]` and, with no other source, `GatewayError`
- [x] `calls_left` is reported on every outcome, and the spend is one atomic statement
- [x] The L1 key holds no credentials, and rows are committed before `fetch` returns
- [x] TTL tests backdate rows directly, with no injected clock
