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
| Several Postings per Jev request | Measured on 200 stored Postings: one shared request judged 25 relevant Postings not relevant and 1 the other way, while one request per Posting repeated with no flips. Raising concurrency gives similar speed with no such shift | A labelled set showing shared-request verdicts are better, with the cut re-tuned for them |
| A Caveat on normal L2 reads | Up to 7 days old is within the data's expected freshness | `l2_fresh_days` being raised |

## Analysis

| Item | Why it's left out | Brings it back |
|---|---|---|
| A Jev veto on each skill merge | It agreed with all 12 probed merges, so it would add a placement, a threshold and many calls to catch nothing. Never tried against a bad merge | Over-merging appearing in live runs despite the tight prompt |
| Splitting a bad Batch in half and retrying | Bad output hasn't been seen at 8,192 tokens, and a Caveat covers the loss | The "Postings not extracted" Caveat firing on real Runs |
| Detecting employer boilerplate in skills | Ranking by distinct employers already demotes it | A single employer's text still topping skills in live runs |
| Live FX rates | A dependency and a failure mode, and they'd change Stats on replay | Using the Brief for budgets where a stale rate matters |
| Salary amounts read from Posting text | An LLM reading figures is what the "Python computes" rule avoids, and structured fields exist | A market where structured pay is nearly always missing |
| A stripped title for grouping | Code can't remove locations or levels without damaging real variants | Title Stats proving too fragmented to use |
| Advertised and estimated pay reconciled into one figure | There's no honest way to weight a model's guess against a stated salary | A published accuracy figure for Adzuna's estimates |

## Brief

| Item | Why it's left out | Brings it back |
|---|---|---|
| Real talent supply data | Job APIs only show demand, so the Outlook reads demand pressure and says so | A candidate-side data source |
| A fourth "not rated" Outlook | The spec requires exactly one of three, so a stated default is used instead | A reader mistaking the default for a finding |
| Tuned Outlook and Confidence thresholds | They're judgement checked on one role | Sample runs across roles showing a threshold misfires |
| A tuned critic cut | Needs a labelled set, and it ships at 0.5 | The `evals/jev/critic.jsonl` sweep in Kernel §11 |
| Judging the Summary with the critic | Accurate Summaries scored under 0.2, so every Run would hit the cap | A question that scores long claims fairly |
| Judging claims against Postings | Postings changed no outcome in the probe, and lowered accurate scores | Stats proving too coarse to catch a real fault |
| Checking number words | Rare, and the critic sees them | A wrong number word reaching a Brief |
| Keeping valid Insights from a failed draft | `LLMExhausted` doesn't carry output, and the rule-written draft covers this | The Brief written by rule Caveat firing on real Runs |
| A key-figures table in the Markdown | `brief.json` has every Stat, and coverage gives each Dimension a line | Clients asking for the figures an Insight left out |
| Dates on the Brief | A clock would make replayed Briefs differ | Taken from the newest `fetched_at` if a reader needs it |

## Runtime and Clients

| Item | Why it's left out | Brings it back |
|---|---|---|
| Persisted event history | `get_run` rebuilds what matters from `run_log`, the pending Pause and status | A client that must show tokens or tool lines after a reload |
| Detaching a CLI from a live Run | The Controller lives in the CLI process and dies with it | Infra shell workers owning the task |
| Partial-field display of structured output | Fragments stay provisional until the node finishes, and a drafting state reads fine | Wanting the Brief to appear as it's written |
| Message IDs on `Token`, to clear an abandoned attempt | A retried `fetch_agent` turn is rare, and the cost is cosmetic | Retried text proving confusing in live use |
| Balance checks between nodes | A Run's spend is small next to the floor, and a mid-Run failure resumes cleanly | Costlier production tier models |
| Deleting lock files | Empty files are harmless, and deleting one races a concurrent lock on Windows | A Run count that makes the directory a nuisance |

## Web UI

| Item | Why it's left out | Brings it back |
|---|---|---|
| Dark mode | A second palette needs its own contrast checks. Colours are all custom properties, so it stays cheap | A user asking for it |
| Deleting, renaming or searching Runs | The Controller has no such methods, and read-only history is enough | A Run list long enough to need it |
| A global event feed for the sidebar | Polling one small SQLite read is enough, and the Controller offers no such feed | Many tabs or Runs making the polling noticeable |
| Tool call IDs on events | `tools` emits results in call order, so pairing by name is exact | Tools that return out of order |
| Resuming a stream from an event ID | Events have no sequence number and tokens aren't buffered, so a reconnect rebuilds | A Run long enough to overflow the 5,000-event buffer |
| Exposing answer models as JSON Schema | Three typed forms read better than generated ones | A Pause kind added often enough to justify a generic form |
| Auth, remote access and a `--host` flag | One local user, and the server can spend quota, so it binds loopback only | The Infra shell's multi-user phase |
