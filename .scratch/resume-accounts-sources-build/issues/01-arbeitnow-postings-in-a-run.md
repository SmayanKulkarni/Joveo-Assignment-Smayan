# 01: Arbeitnow Postings in a Run

**What to build:** A Run on any accepted country can search Arbeitnow beside Adzuna, and its local Postings join the Sample, the Brief and the attribution line. There's no LLD, so the decisions in [What Arbeitnow does in the gateway](../../resume-accounts-sources/issues/10-what-arbeitnow-does-in-the-gateway.md), [One gateway for many sources](../../resume-accounts-sources/issues/11-one-gateway-for-many-sources.md) and [Choosing among the search tools](../../resume-accounts-sources/issues/12-choosing-among-many-search-tools.md) are the spec. Where they differ, the last of the three wins.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] A third source and a `search_arbeitnow` tool exist, offered on every accepted country and never alone, with the docstring from ticket 12
- [x] `COVERAGE` holds only USAJOBS and is read by both `fetch` and `_bound`
- [x] The whole feed is walked lazily into one L1 snapshot row behind a module-level lock, so two Runs never walk at once
- [x] A failed or rate-limited walk discards the partial snapshot, raises `SourceUnavailable`, and is remembered for the rest of that Run
- [x] Arbeitnow is unmetered and `calls_left` is `None`
- [x] Postings map as ticket 11 sets out: no salary, close date or domain; stripped description cut at 4,000 characters; `region` from Adzuna's country root and the city
- [x] Title, country, location and age filter locally, in pages of 50, newest first, with `radius_km` and `category` ignored
- [x] A missing salary never blocks a merge, and the Posting with pay wins
- [x] The "Mostly no pay" Caveat fires past half the Sample
- [x] `_cap`, `FETCH_SYSTEM` and `BROADEN_SYSTEM` change as ticket 12 sets out
- [x] The attribution line names every credited source in the Sample, in the Run Notes, `brief.md` and the Brief footer
- [x] Client tests use the `transport` seam with a trimmed recorded page; tests cover binding on any country, the cap, the merge rule, the Caveat and the remembered failure
- [x] Adzuna's country root names are checked against one live response per country, and the walk's time and memory are measured against 512 MB

## Built

- Adzuna's root names, checked live on 2026-11-02: Deutschland, UK, France, Schweiz, Nederland.
- A live walk took about 58 s for 4,071 Postings with none dropped, and peak working set rose from 68 MB to 243 MB on Windows. That leaves room under Render's 512 MB, but not much once the app's own 117 MB is added.
- **Cloudflare answers 429 to pages fetched back to back.** Two pages 1.5 s apart still failed, 2 s apart passed all 23, so the walk pauses `PAGE_PAUSE` (2.5 s) between pages. The first Run of the day therefore waits about a minute for Arbeitnow.
- The remembered failure lives on `ArbeitnowClient`, which is built once per gateway and so once per Run, rather than on `JobsGateway`. The effect is the same.
- A 4xx from the feed becomes `SourceUnavailable`, because the feed needs no key and a refusal is the source failing.
- Missing from the ticket: `Posting.remote` and the remote mapping came with ticket 02 in the same pass.
