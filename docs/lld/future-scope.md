# Future scope

Work deliberately left out of an LLD, with why and what would bring it back. One section per component. Items that simply belong to another component's LLD are not listed here; that LLD owns them.

## Kernel

| Item | Why it's left out | Brings it back |
|---|---|---|
| `preferences` state slice | Long-term memory is the last build pass and its LLD decides what preferences contain | Long-term memory LLD adds the slice to `kernel/state.py` |
| Calibrated Jev cuts | Need live labelled runs; every cut ships at 0.5, marked untuned | Running the `evals/jev/<placement>.jsonl` sweep and editing `thresholds.py` |
| Jev Choice and Score in the wrapper | All three placements are yes/no questions, so the wrapper is Noul-only | A stage that needs a multi-label or graded judgement |
| `jev-1.13` as a middle fallback hop | It would need its own tuned cuts | `jev-1.14` proving flaky in practice |
| OpenRouter generation id and cost per Jev call in `run_log` | LangSmith already traces and prices Jev; the HTTP hook costs the classifier's 30 s timeout | Needing per-call ids outside LangSmith |
| Timestamps on `run_log` entries | List order is event order, LangSmith has the times, and replay transcripts stay byte-identical | A consumer that needs wall-clock times without LangSmith |
| Production tier models: cheap `openai/gpt-6-luna` → `anthropic/claude-haiku-5.5`, strong `anthropic/claude-sonnet-5.5` → `openai/gpt-6.1-sol` | This is a testing project for now, so both tiers run DeepSeek v4.1 Flash → MiniMax M3.1 Flash | Leaving the testing phase: set `LLM_CHEAP` / `LLM_STRONG` in `.env` and re-run the live smoke script |
| Claude `cache_control` for prompt caching | Caching only pays off in the strong tier's critic loop, and the testing models cache automatically or not at all | The critic pass (5) running on a Claude strong tier |

## Jobs Data Gateway

| Item | Why it's left out | Brings it back |
|---|---|---|
| L2 Region and Domain columns | A full scan of about 8,750 rows takes under 40 ms | A larger Adzuna budget making the scan slow |
| USAJOBS in L2 | Its calls are free, and its Postings match poorly | USAJOBS gaining a real quota |
| HTML stripping in the mappers | None seen in 100 Adzuna results | HTML appearing in a description |
| Serving a past-TTL L1 row when the budget is out | It would need its own status and Caveat, and L2's fallback covers that reuse | L2 not being built |
| A reserve of Adzuna calls for walkthroughs | Lowering `adzuna_daily_limit` in `.env` does the job | Needing to hold calls back routinely |

## Request & Plan

| Item | Why it's left out | Brings it back |
|---|---|---|
| `focus` shaping the Search Plan | The same Postings answer every Dimension, so narrowing saves nothing | A focus needing Postings a general search misses |
| Fetching Adzuna's per-country category list | A fixed list of known tags is enough, and the call would spend quota | A valid tag being rejected for some country |
| Multi-country Runs | `SearchPlan` holds one country, and Stats would mix currencies | A client asking for regional comparisons |

## Collection

| Item | Why it's left out | Brings it back |
|---|---|---|
| A second tool, such as `get_search_status` | It would only repeat what the tool messages say, and the Gateway already picks sources | Another real data source or action for the model to choose |
| A cap on the Sample | Extra Postings make Stats better, and batching is Analysis's job | Analysis cost on large Samples proving a problem |
| Judging seniority in Relevance | It would empty the Sample of unlevelled Postings and bias the seniority mix | A client needing one level's market alone |
| Sufficiency below the target, such as 80% | One rule against the Search Plan's target is simple to explain | First-Attempt broadens proving common even with the 1.5× raw goal |
| Several Postings per Jev request | Saves under a cent per Run, and a shared request has to fit 32 KB | Per-request latency becoming the bottleneck |
| A Caveat on normal L2 reads | Up to 7 days old is within the data's expected freshness | `l2_fresh_days` being raised |

## Runtime and Clients

| Item | Why it's left out | Brings it back |
|---|---|---|
| A simple web UI replacing Streamlit | Streamlit is enough for now, and a real UI needs the Infra shell's API | The Infra shell phase; Streamlit is deleted then |
| Streamlit re-attach, Cancel button and token display | The page is disposable, and re-attach would add a Controller method only it uses | The web UI needing them, built on its own API |
| Persisted event history | `get_run` rebuilds what matters from `run_log`, the pending Pause and status | A client that must show tokens or tool lines after a reload |
| Detaching a CLI from a live Run | The Controller lives in the CLI process and dies with it | Infra shell workers owning the task |
| Partial-field display of structured output | Fragments stay provisional until the node finishes, and a drafting state reads fine | Wanting the Brief to appear as it's written |
| Message IDs on `Token`, to clear an abandoned attempt | A retried `fetch_agent` turn is rare, and the cost is cosmetic | Retried text proving confusing in live use |
| Friendly node labels | Raw names are clear enough for this audience | Showing the live view to clients |
| Balance checks between nodes | A Run's spend is small next to the floor, and a mid-Run failure resumes cleanly | Costlier production tier models |
| Deleting lock files | Empty files are harmless, and deleting one races a concurrent lock on Windows | A Run count that makes the directory a nuisance |
