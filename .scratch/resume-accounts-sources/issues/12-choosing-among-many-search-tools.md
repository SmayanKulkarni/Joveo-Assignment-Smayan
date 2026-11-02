# Choosing among the search tools

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md), [One gateway for many sources](11-one-gateway-for-many-sources.md)

## Question

How does Collection's fetch model choose among `search_adzuna`, `search_usajobs` and an Arbeitnow tool, and how is the budget shared out?

- One tool per source (as `search_adzuna` and `search_usajobs` are today), or one `search(source=...)` tool? What must each tool description say so the model picks well: coverage, cost, and the fields it ignores.
- `_bound`: [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md) fixed that Arbeitnow is offered beside Adzuna for DE, GB, FR, CH and NL only, with no role filter, and [One gateway for many sources](11-one-gateway-for-many-sources.md) made `_bound` read the gateway's `COVERAGE` dict. What remains is the exact tool descriptions and any interaction with remote plans.
- `MAX_FETCHES`, `RAW_FACTOR` and `_cap` with a third source. Is there a per-source cap inside an Attempt?
- How broaden and the low-data review treat a source that ran out of quota or failed.
- Whether the resume agent (see [Matching Postings to a Resume](18-matching-postings-to-a-resume.md)) reuses these tools unchanged.
- The Collection LLD sections and prompts (`collection/prompts.py`) to update.

Load `langchain-router` first: this touches LangGraph tool binding and the custom executor.

## Answer

**Reopened and closed again on 2026-11-02:** the user considered covering remote jobs on Adzuna and USAJOBS too, then chose to skip them. Everything below stands. Remote Postings come from Arbeitnow only, by the user's choice. For anyone revisiting this: USAJOBS has a `RemoteIndicator` field and search filter, while Adzuna has no remote field in the docs page we could read, its text can't be keyword-matched ("Potential for Remote Work: ORA_ON_SITE"), and each search covers one of 19 countries from a shared 250 calls a day.

Grilled with the user on 2026-11-02. The user accepted every recommendation except one: remote Postings apply to all Runs, not only resume Runs. The user added the remote rule during the grilling: a remote job should be visible to a person anywhere, whatever the job's location. This amends [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md) and [One gateway for many sources](11-one-gateway-for-many-sources.md).

**Tools**

1. **One tool per source.** `search_arbeitnow` joins the other two, for the reasons in Collection LLD §5. A remote plan doesn't exist: `SearchPlan` has no `work_mode` and Collection doesn't read it, so remote is a property of a Posting.
2. **Docstring**, with exact wording tunable in the build:
   > Search Arbeitnow, a European job board, by title. Inside Germany, UK, France, Switzerland and the Netherlands it returns local and remote jobs; elsewhere it returns remote jobs only. Free and unmetered, but mostly tech and corporate roles, no salaries, and only about the last 7 days. It ignores the plan's radius and category, and a place must match the city name exactly. One call returns one page of up to 50. `location` must be one of the plan's places; blank means the first.
3. **`_bound`.** `search_arbeitnow` is offered on every country the app accepts, always beside `search_adzuna`. Arbeitnow is therefore left out of `COVERAGE`, which holds only USAJOBS. "Anywhere" stops at the countries `Fetch` and `SearchPlan` accept, which is the Adzuna list.
4. **`FETCH_SYSTEM`.** "On a US Run, try both sources for the primary title" becomes "When more than one source is offered, try each for the primary title, unless its description says it can't hold this role".

**Budget**

5. **Cap.** `_cap` becomes `max(MAX_FETCHES, titles × places + places × (sources offered − 1))`, which leaves room for the primary title on the extra sources in each place. It stays shared, with no per-source cap, and `RAW_FACTOR` is unchanged. Plans with few searches keep 6. Larger plans gain a few calls, US Runs included, so the worst case can pass 18 Adzuna calls for a Run. The daily guard stays the ceiling.

**Broaden and failures**

6. **`BROADEN_SYSTEM`** gains: "Judge a title as exhausted from Adzuna's total, not Arbeitnow's, which covers about a week. A wider radius, a category change or an older `max_days_old` finds nothing new on Arbeitnow." A repeat Arbeitnow search after a broaden isn't listed as already searched, so it can use up a cap slot and show "0 new". That is accepted.
7. **Adzuna out of quota.** `_blocked` doesn't change. Arbeitnow alone has no pay and a week of history, so the Run goes to `low_data_review` and the user decides.
8. **A failed walk is remembered for the Run.** `tools` runs calls under `gather`, so parallel calls would otherwise queue on the lock and each walk again, even after a 429. `JobsGateway` keeps the failure in an instance field, and later Arbeitnow Fetches raise the same `SourceUnavailable` without walking. A new Run tries again. A brief blip loses Arbeitnow for that whole Run, and the One source failed Caveat reports it.

**Remote Postings**

9. **`Posting.remote: bool = False`.** The Arbeitnow mapper sets it when the `remote` flag is true, or the location says "Remote", or a tag says "Remote", because those signals disagree. Adzuna stays `False` because our recorded responses and its mapper have no remote field, and guessing from text is unreliable. USAJOBS stays `False` because these are federal jobs whose eligibility is doubtful for anyone abroad; that doubt wasn't checked. So in practice the rule applies to Arbeitnow only.
10. **Filtering.** A remote Posting skips the country and location filters in every Arbeitnow Fetch. Title and `max_days_old` still apply, so `location` only narrows non-remote Postings.
11. **All Runs.** Remote Postings are full members of the Sample, counting toward Sufficiency and every Stat. They have no salary, so pay Stats are unaffected.
12. **Caveat.** A closing Caveat fires whenever any are present, with no threshold: "Includes remote: N of M Postings are remote jobs that may be based outside <country>".
13. **Label.** Every remote Posting is shown, with no filtering of "remote, Germany only" jobs, because the feed has no eligibility field. It carries a label such as "Remote: check where the employer can hire". Placement and scoring belong to [Matching Postings to a Resume](18-matching-postings-to-a-resume.md).
14. **`region`** is `("Remote",)` for these Postings, so the places chart shows one Remote group. The build ticket tests `brief/glance.py` with a Sample holding that region, since this reading of the chart comes from ticket 11 and wasn't re-checked.

**Resume agent**

15. It reuses these tools, `fetch_agent` and `tools` unchanged, by building a normal `SearchPlan`. How that plan comes from a Resume belongs to [Matching Postings to a Resume](18-matching-postings-to-a-resume.md).

**Cost accepted**

16. Nearly every Run now calls Arbeitnow, so the first Run each day pays for the walk of about 21 pages and 35 MB. It stays at most one successful walk per L1 TTL. The build ticket measures its time and memory against Render's 512 MB.

**LLD sections to update**

- **Collection:**
  - §1 and §5: the third tool, its docstring, `_bound`, `_cap`
  - §11: the "Includes remote" and "Mostly no pay" Caveats
  - §12: `FETCH_SYSTEM` and `BROADEN_SYSTEM`
  - §14: tests for binding on any country, the new cap, and both Caveats
- **Gateway:**
  - §3: `COVERAGE` without Arbeitnow
  - §7.5: the remote mapping and filter, `region`, and the remembered failure
- **Kernel:** `Posting.remote`, with the default so existing checkpoints still load.
- **`collection/prompts.py`:** the two prompt lines above.
