# Kernel LLD

The low-level design of the Kernel (component A in [HLD](../HLD.md) §3), precise enough to build from. Items marked ⏳ are not Kernel decisions: they belong to the named stage or Runtime LLD. Deliberate deferrals live in [future-scope.md](future-scope.md).

Source tickets (each holds the full reasoning):
- [Shared domain types](../../.scratch/kernel-lld/issues/05-shared-domain-types.md)
- [State schema, reducers and run_log](../../.scratch/kernel-lld/issues/06-state-schema-and-run-log.md)
- [LLM tier factory](../../.scratch/kernel-lld/issues/07-llm-tier-factory.md)
- [Jev wrapper and thresholds](../../.scratch/kernel-lld/issues/08-jev-wrapper-and-thresholds.md)
- Research: [OpenRouter tiers](../../.scratch/kernel-lld/issues/01-research-openrouter-llm-tiers.md), [Pydantic state contract](../../.scratch/kernel-lld/issues/02-research-langgraph-pydantic-state-contract.md), [langchain-typesafe](../../.scratch/kernel-lld/issues/03-research-langchain-typesafe-api.md), [live smoke test](../../.scratch/kernel-lld/issues/04-live-smoke-test-openrouter-jev-langsmith.md)

## 1. What the Kernel is

The first thing built, imported by every other component. It owns:
- the shared domain types
- the graph state schema and its one reducer
- `run_log` (including Caveats), the write guard, and the `log()` helper
- the Jev wrapper and every Jev threshold
- the LLM tier factory and the OpenRouter balance check
- settings, and the replay cache for LLM and Jev responses

It does **not** own:
- stage-private state fields or stage-private types (each stage's LLD adds them)
- prompts and Jev question text (stages)
- graph wiring, checkpointer, Store, per-Run LangSmith metadata (Runtime)

## 2. Layout and conventions

```
src/talent_scout/
  kernel/
    types.py        # shared domain types
    state.py        # State, log(), owned(), StateWriteError
    thresholds.py   # Jev cuts
    jev.py          # Jev wrapper
    llm.py          # Tiers, LLMExhausted, check_balance()
    settings.py     # Settings, get_settings()
    replay.py       # SQLite replay cache for LLM and Jev (pass 2)
    events.py       # emit(): guarded custom stream events (pass 3, Runtime LLD §10)
    testing.py      # fake_classifier, FakeToolChatModel
  <stage>/types.py  # stage-owned types; may import only kernel.types
```

- `uv`, Python 3.12, `pytest`. Settings come from the root `.env`, loaded before the first LangChain call, because LangSmith caches its env vars (§13).
- Pydantic v2 everywhere. Every model, `State` included, uses `ConfigDict(frozen=True, extra="forbid")`.
- Enums are `StrEnum`, money is `float`, and dates are `date`.
- **Import direction:** `kernel/state.py` imports the stage `types.py` modules, which import only `kernel.types`. Nothing loops.
- **Keep model module paths stable.** Checkpoints store class paths, so moving a model breaks rehydration.

## 3. Domain types (`kernel/types.py`)

**Rule:** a type lives in the Kernel only if one component writes it and another reads it (the Gateway counts as a component). Types read inside a single component stay with that component:
- **Analysis:** Extraction and the Stat catalogue
- **Brief:** Insight, Confidence Tag, Client Recommendation, Hiring Outlook, MarketBrief

```python
class Source(StrEnum): adzuna, usajobs
class PayPeriod(StrEnum): annual, monthly, biweekly, weekly, daily, hourly, unknown

class Salary(BaseModel):
    min: float | None          # at least one bound; min <= max
    max: float | None
    currency: str              # ISO 4217, ^[A-Z]{3}$
    period: PayPeriod          # Adzuna is always `unknown`
    predicted: bool            # Adzuna salary_is_predicted; False for USAJOBS

class Posting(BaseModel):
    source: Source
    source_id: str
    title: str
    company: str | None
    location: str              # display string
    region: tuple[str, ...]    # source's place hierarchy, country first
    domain: str | None         # Adzuna category; USAJOBS family mapped onto it
    posted_at: date            # soft expiry, trend
    closes_at: date | None     # USAJOBS only, hard expiry
    description: str           # Adzuna <=500-char snippet; USAJOBS capped at 4000
    url: str
    salary: Salary | None      # None = pay not disclosed
    # computed: key = f"{source}:{source_id}"

class WorkMode(StrEnum): onsite, hybrid, remote
class RequestField(StrEnum): role, location, seniority, employment_type, work_mode, currency, purpose

class HiringRequest(BaseModel):          # role and location non-blank
    role: str
    location: str
    seniority: str | None
    employment_type: str | None
    work_mode: WorkMode | None
    currency: str | None
    purpose: str | None

class ClarifyingQuestion(BaseModel):
    about: RequestField
    text: str
    options: list[str]
    answer: str | None                   # filled by code, never by the LLM

class Assumption(BaseModel):
    about: RequestField
    value: str
    reason: str

class SearchPlan(BaseModel):             # replaced whole, never patched
    titles: list[str]                    # non-empty, primary first
    country: str                         # ^[a-z]{2}$
    location: str
    radius_km: int                       # >= 0
    max_days_old: int                    # >= 1; also the soft-expiry window
    target_postings: int                 # >= 1; the Sufficiency target
    category: str | None

class Dimension(StrEnum): demand, compensation, skills, competition, titles_seniority

class Evidence(BaseModel):
    posting_keys: list[str]              # sorted + deduped on input
    # computed: count

class Stat(BaseModel):
    id: str                              # e.g. "comp.median"
    dimension: Dimension
    label: str
    value: float | str
    unit: str | None
    evidence: Evidence

class MarketStats(BaseModel):
    sample_size: int
    stats: list[Stat]                    # Stat ids unique
```

Key points:
- **Posting identity** is `key` (`source:source_id`). The same key twice is the same Posting. Collapsing Duplicates (one job posted in several places or by both sources) is one Gateway rule, `coalesce`, which Collection re-applies across Fetches; it isn't a field ([Gateway query interface](../../.scratch/gateway-lld/issues/02-gateway-query-interface.md)).
- **The Gateway's mapper** turns raw API JSON into Postings and absorbs every source quirk: currency from country, `RateIntervalCode` to period, family to Domain, reversed salary ranges, the description cap. Postings that still fail validation are skipped and counted. Tools only ever see `list[Posting]`.
- **LLM-schema policy:** a type is used directly as a structured-output schema only when the model fills every field. Otherwise the stage defines a narrower draft schema.
  - Every field has a `Field(description=...)` stating its meaning and units.
  - Optional fields are `T | None` with no default, because strict `json_schema` makes every field required anyway.
  - Validator errors are what gets fed back on a retry.
- **Stats are a flat list.** Analysis decides which Stat ids exist, so adding a figure never touches the Kernel. Brief cites Stat ids, and code expands them into Evidence, so the LLM never types a Posting key.

## 4. State schema (`kernel/state.py`)

```python
class State(BaseModel):                     # frozen, extra="forbid"
    # every field carries Field(json_schema_extra={"owner": ...})

    # --- input: Run Controller writes once via invoke; no node writes
    request_text: str
    focus: list[Dimension] = []             # [] = all

    # --- Request & Plan
    hiring_request: HiringRequest | None = None
    questions: list[ClarifyingQuestion] = []
    assumptions: list[Assumption] = []
    search_plan: SearchPlan | None = None   # the approved plan

    # --- Collection
    messages: list[AnyMessage] = []
    postings: dict[str, Posting] = {}       # keyed by Posting.key
    sample: list[str] = []                  # Relevant Posting keys, in order
    broadened_plans: list[SearchPlan] = []

    # --- Analysis
    extractions: Annotated[dict[str, Extraction], merge] = {}   # the only reducer
    stats: MarketStats | None = None

    # --- Brief
    brief: MarketBrief | None = None
    brief_markdown: str | None = None

    # --- Kernel: every node writes, through log()
    run_log: list[RunLogEntry] = []

    @property
    def current_plan(self) -> SearchPlan | None: ...   # broadened_plans[-1], else search_plan
    @property
    def sample_postings(self) -> list[Posting]: ...    # postings[k] for k in sample
```

| Key | Owner | Written by | On loops |
|---|---|---|---|
| `request_text`, `focus` | input | Run Controller | never change |
| `hiring_request` | Request & Plan | `intake` (refined after answers) | |
| `questions` | Request & Plan | `clarity_check` adds, `clarify` fills answers | never cleared |
| `assumptions` | Request & Plan | Request & Plan nodes | |
| `search_plan` | Request & Plan | `plan` | replaced on `plan_review` reject |
| `messages` | Collection | `fetch_agent`, `tools` | `[]` on each `broaden` |
| `postings` | Collection | `collect` | kept across attempts |
| `sample` | Collection | `relevance` | recomputed each attempt |
| `broadened_plans` | Collection | `broaden` appends | |
| `extractions` | Analysis | `batch_extract` × N | |
| `stats` | Analysis | `stats` | |
| `brief`, `brief_markdown` | Brief | `render` | |
| `run_log` | Kernel | every node via `log()` | never cleared |

Why it looks like this:
- **One flat model, not one sub-model per stage.** LangGraph puts reducers only on top-level fields. A nested `state.analysis` model would be a single replace-only value, so the parallel `batch_extract` writes would crash with `InvalidUpdateError`.
- **Frozen.** In LangGraph, `state.postings["x"] = p` inside a node silently does nothing, because only *returned* updates are saved. Frozen turns that into an immediate error, so every change has to come back as `{"postings": ...}`.
- **Search Plan split.** `broaden` belongs to Collection but revises the plan. Giving Collection its own `broadened_plans` keeps one writer per slice, and `current_plan` reads both. The attempt count is `len(broadened_plans)`: no counter to drift, and every revision shows up in Run Notes for free.
- **`sample` holds keys, not Postings.** Analysis and Brief look Postings up in `postings`, so there's one copy of each.
- **`focus` reuses `Dimension`,** so `--focus compensation` needs no new type. What each focus value changes is ⏳ the Request & Plan LLD; Clients only pass it through ([Runtime LLD](runtime.md) §12).
- ⏳ Stage LLDs add their private fields here: the Brief draft, critic verdicts and revision state; `plan_review` feedback; and each stage's routing-decision fields.
- ⏳ The `preferences` slice is added by the Long-term memory LLD.

## 5. Reducers

**Every slice is replace-only (`LastValue`) except `extractions`.** Nothing appends on its own. A node that wants to add writes the old value plus the new one:

```python
return {"postings": {**new_by_key, **state.postings}}   # first copy seen wins
```

The only place a reducer is truly required is **two writers on the same key in the same super-step**, which in this graph is just the `Send` fan-out. N `batch_extract` branches each write `extractions` at once, and a branch only sees its payload, not the full state, so it can't append by hand. Hence `merge` = `{**a, **b}` on that one field.

Elsewhere a reducer would only be a convenience, and explicit writes read better:
- `add_messages` gives replace-by-id and `RemoveMessage`, which nothing here needs.
- An append reducer on `run_log` would protect against a node wiping it. The write guard catches that instead (§8).

`Send` is kept over one node running `asyncio.gather`. With `Send`, branches that finished keep their writes and only a failed branch reruns on resume. It is also the HLD's graph shape.

## 6. Reset semantics

| Loop | Changes | Kept |
|---|---|---|
| `clarify` → `clarity_check` | `questions` rewritten with answers; an Assumption is added if the re-ask cap is hit | earlier questions (re-asks are counted from them) |
| `plan_review` reject → `plan` | `search_plan` replaced | everything else; nothing has been fetched yet |
| → `broaden` | the new plan is appended to `broadened_plans`; `messages` = `[]`; `sample` is recomputed by the next `relevance` | `postings` |
| `critic` → `write_brief` | ⏳ draft and verdicts replaced (Brief LLD) | `stats`, `sample` |
| Pause re-entry, or a kill mid-node | nothing: an uncommitted node wrote nothing | everything |

**Why reset messages:** the Postings are already safe in `postings`. Old tool chatter costs tokens and can pull the model back toward the old plan. With replace-only, the reset is just `broaden` returning `{"messages": []}`.

## 7. Routing

**Rule: routers are pure functions of state.** LangGraph routers can't write state. So the node *before* a router does the work, stores the outcome in a slice it owns, and writes a `route` entry to `run_log`; the router only reads that slice. The router costs nothing, and it gives the same answer every time it is replayed.

| After | Outcomes | Decided by / router reads |
|---|---|---|
| `clarity_check` | `clarify` · `plan` | The Jev clarity `Judgement` stored by `clarity_check`. A vague answer is re-asked at most once (HLD), counted from earlier `questions` with the same `about`; once the cap is hit, go to `plan` with an Assumption. |
| `plan_review` ⏸ | `fetch_agent` · `plan` · END | The user's answer (approve / edit / reject + feedback / abort). The Pause node writes only the answer; an edit writes `search_plan`. |
| `fetch_agent` | `tools` · `collect` | `messages[-1].tool_calls` |
| `relevance` | `Send`×N → `batch_extract` · `broaden` · `low_data_review` | `relevance` writes `sample` and the Sufficiency verdict: `len(sample)` vs `current_plan.target_postings`. Attempts left = cap − `len(broadened_plans)`. |
| `low_data_review` ⏸ | `broaden` · `Send`×N · `stats` · END | The user's answer. The `stats` edge exists because a fan-out with zero branches would stall the Run. |
| `critic` | `write_brief` · `render` | ⏳ critic verdicts and revision cap (Brief LLD) |

- Every `Send` payload is a model instance, not a dict. The guard enforces this.
- ⏳ The caps (attempts, revisions) and the names of the decision fields belong to the stage LLDs.

## 8. Write guard

LangGraph validates what a node *reads* but never what it *writes*, and never `Send` payloads. A bad write blows up in the next node, blaming the wrong one, or leaks into the final output if it came from the last node.

`owned(node, owner)` fixes both. The Kernel exports it, and Runtime wraps every node and router with it when wiring the graph. It raises `StateWriteError(node, key, reason)` when:
1. an update key belongs to another owner (`run_log` is open to every node; `"input"` fields to none)
2. a value fails its field's type, checked with a cached `TypeAdapter` (the `ValidationError` is chained). This is cheap because values are already model instances.
3. a `run_log` update doesn't start with the current log, which means something was wiped
4. a router returns a `Send` whose `arg` isn't a model instance

## 9. `run_log`

```python
class LogKind(StrEnum): route, pause, caveat, warning, note

class RunLogEntry(BaseModel):        # frozen, extra="forbid"
    node: str
    kind: LogKind
    message: str
    data: dict[str, JsonValue]       # plain JSON only

def log(state, node, kind, message, **data) -> dict:
    ...                              # {"run_log": [*state.run_log, entry]}
```

- **Narrative only:** routing decisions and reasons, Jev outcomes, Caveats, skip counts, and the original request wording.
- **Caveats are the transparency channel.** A `caveat` entry records a limitation that affects how far the user can trust the Market Brief. `data` may carry `dimension` and `posting_keys`. **Brief must render every Caveat in Run Notes**; `warning` and `note` entries stay internal. Stages decide when to raise one, and each stage LLD lists its Caveats. Known so far:
  - Postings the Gateway mapper dropped (counted)
  - a Posting skipped after `LLMExhausted` (§12)
  - continuing at `low_data_review` with too few Postings, or broadening N times
  - old or soft-expired Postings in the window, and the age of cached jobs data in replay (§14)
  - Jev input truncated, or Jev falling back to the LLM (§11)
  - one jobs source failing while the other succeeded
- **Backend errors are never Caveats.** A Run killed by `LLMExhausted`, a 401 or a bug stops the Run; Clients show "Stopped at <node>: <reason>. Resume with `scout resume <id>`" ([Runtime LLD](runtime.md) §9, §12), and the details go to logs and LangSmith. A successful LLM fallback isn't shown either, because the fallback's output passes the same validation and can't change a job-related conclusion.
- **No copies of domain objects.** Run Notes are built by Brief from `run_log` plus the slices (`questions`, `assumptions`, `current_plan` / `broadened_plans`, `sample`). This narrows the wording of HLD §9; what Run Notes contain is unchanged.
- **`data` is plain JSON** because strict msgpack blocks models stored in untyped fields.
- **No timestamps.** List order is event order, LangSmith has the times, and replay transcripts stay byte-identical.
- `batch_extract` branches never log, since they can't append (§5). `stats` writes one summary entry.

## 10. Persistence and serialization rules

From the Pydantic-state research. The Runtime parts are built per the [Runtime LLD](runtime.md).
- Nodes return **partial dicts whose values are model instances**, never the full `State`. Returning `State` rewrites every set field. Model instances keep each node's state read around 0.01 ms, against about 0.6 ms for dicts on 1,000 Postings.
- `LANGGRAPH_STRICT_MSGPACK=true`, and no `Any` anywhere in persisted state. Compile then allowlists every type reachable from the schema automatically. Interrupt payload types that aren't in state go into `allowed_msgpack_modules`.
- Validators re-run when a checkpoint loads, so a model that becomes stricter can fail on an old checkpoint.
- Graph output and `get_state().values` are raw dicts with unwritten defaults missing, so the Run Controller wraps them with `State.model_validate(...)` (Runtime LLD §6).
- ⏳ Long-term memory: Store values are written with `model_dump(mode="json")` and read with `model_validate`, and the Store gets its own autocommit connection. Nothing opens the Store before pass 6 (Runtime LLD §16).

## 11. Jev wrapper

One long-lived `TypeSafeClassifier` (`langchain-typesafe==0.0.1a3`, `typesafe/jev-1.14`, OpenRouter `base_url` and key) behind a thin class.

```python
Placement = Literal["clarity", "relevance", "critic"]

await jev.judge(placement, state: dict, questions: dict[str, Noul]) -> dict[str, Judgement]
# Judgement: outcome: bool, p_yes, cut, model, source ("jev" | "llm_fallback"), truncated, reason
```

- **Noul only.** All three placements are yes/no questions. Several questions share one request. Stages write the question text so that "yes" is the side that must clear the bar.
- **Thresholds:** one cut per (model, placement) in a dict literal in `thresholds.py`; `outcome = p_yes >= cut`.
  - **No uncertain band:** there is no Pause to send "uncertain" to.
  - **All cuts start at 0.5**, marked untuned.
  - The cut is picked by the longest config key that is a prefix of the returned model id (Jev returns dated snapshots). An unknown model fails loudly.
  - Construction checks that every placement has a cut for every model in the chain.
- **Fallbacks:** `jev-1.14` with `with_retry` (3 attempts with backoff on 429, 5xx, connection errors and timeouts), then `with_fallbacks` to an LLM adapter on the cheap tier.
  - The adapter is `tiers.structured("cheap", ...)` (§12). It returns `{id: {answer, reason}}`, mapped to `p_yes` of 0 or 1 with model `llm:cheap`, so routers don't change.
  - A Judgement with `source="llm_fallback"` or `truncated=True` was made with less information, so the calling stage logs a Caveat for it.
  - It never falls back on 400/422 (our bug) or 402 (same OpenRouter account). Those propagate.
- **32 KB guard:** measure the compact JSON size against 30,000 bytes. Over budget, truncate the longest string field with `…[truncated]` until it fits, and set `truncated=True`. Never raise.
- **Concurrency:** one `asyncio.Semaphore(8)` for the whole process, set from settings.
- **Tracing:** LangSmith already traces and prices Jev, so there's no `@traceable` and no HTTP hook. Each call passes `run_name=f"jev:{placement}"`, tags, and the cut and model as metadata.
- **Tests:** constructor injection, `Jev(classifier, cuts)`. `make_jev(settings)` builds the real chain, and `fake_classifier({...})` returns canned answers.
- **Replay:** when `REPLAY_CACHE` is set, `judge` looks up (model chain, sha256 of the request JSON) in the replay cache before calling, and stores the response after (§14).
- **Tuning:** 20–40 *hard* labelled examples per placement in `evals/jev/<placement>.jsonl`. A script sweeps the cut from 0.05 to 0.95 and prints precision, recall and F1. Relevance optimises precision; clarity optimises recall of "ambiguous". A human edits `thresholds.py`. Re-run whenever the model id changes.

## 12. LLM tier factory (`kernel/llm.py`)

```python
Tier = Literal["cheap", "strong"]

class Tiers:
    def __init__(self, chains: dict[Tier, list[BaseChatModel]], settings: Settings): ...
    def structured(self, tier, schema: type[M], *, system: str, name: str,
                   max_tokens: int | None = None) -> Runnable[str, M]: ...
    def chat(self, tier, *, tools: list[BaseTool], name: str,
             max_tokens: int | None = None) -> Runnable[list[AnyMessage], AIMessage]: ...

def make_tiers(settings) -> Tiers: ...        # real ChatOpenRouter chains
async def check_balance(settings) -> float: ...  # GET /api/v1/key; raises below the floor
class LLMExhausted(Exception): tier, name, attempts   # chained to the last error
```

- **Two entry points, async only.** `structured` serves intake, plan, extraction, brief writing, the critic and Jev's LLM fallback. `chat` exists only for `fetch_agent`, which needs tools and its own message history; tools are bound to each model *before* the chain is built, because a fallback wrapper has no `bind_tools`. Stages own every prompt.
- **Prompt prefix by signature.** `structured` takes its fixed `system` text when built, and its input is only the variable user content, so stable instructions and schema always come first (HLD §5). No Claude `cache_control` (future-scope).
- **Models, testing phase.** Both tiers run `deepseek/deepseek-v4.1-flash` ($0.045/$0.50 per M) → `minimax/minimax-m3.1-flash` ($0.15/$0.60): two providers, 1M context, both verified live with strict `json_schema` under `provider.require_parameters: true`. The tier names stay in code, so `LLM_CHEAP` / `LLM_STRONG` in `.env` restore the research picks (future-scope).
- **Reasoning and output room.** Every call sends `reasoning: {effort}`, `low` for cheap and `medium` for strong. Live, DeepSeek at default effort spent 178 of 200 output tokens reasoning on a 3-field extraction, and MiniMax rejects `reasoning.enabled: false`. `max_tokens` defaults to 2,048 (cheap) and 8,192 (strong), overridable per call, never below 1,000. It is a ceiling, not a charge: about $0.02 per heavy Run at low effort, about $0.12 if every call used 1,000 output tokens.
- **Structured call, parsed by us.** The model is bound to a strict `json_schema` response format built from the schema with `convert_to_openai_tool(schema, strict=True)`, and the factory validates the raw content with `schema.model_validate_json`. `with_structured_output`'s parser is not used, because in json_schema mode it raises inside the call and loses the raw output the retry needs. Schemas follow the LLM-schema policy in §3.
- **Validation retry.** On a `ValidationError`, resend the same prompt plus the bad output as an `AIMessage` and a `HumanMessage` with the Pydantic error text and "return corrected JSON". One feedback retry per model, so at most 4 attempts over the 2-model chain.
- **Transport failures.** Each model gets `with_retry` (3 attempts, jittered backoff) on 429, 5xx, timeouts, connection errors and 402 (usually in-flight spend, which clears), then falls to the next model with an explicit exception list: provider errors, including an error body returned with HTTP 200. A small loop does this instead of `with_fallbacks`, because `with_fallbacks` re-raises the first error and `LLMExhausted` must chain to the last. Never fall back on 400, 401 or 422 (our bug) or 402 (same account); those propagate. 60 s timeout per call.
- **Streaming path.** LangGraph's `messages` stream mode sends every call through `_astream`, not `_create_chat_result`. `_CostedOpenRouter` overrides it so a mid-stream error frame, a `ValueError` from the stream or an empty stream raises `_ProviderError` and gets the same retry and fallback. Cost is set after the chunks merge, in `_agenerate_with_cache` (a private langchain-core method; re-check on upgrades), because chunk addition rejects a float in `usage_metadata`. The 60 s timeout then applies per read, not per call.
- **Chain exhausted.** `LLMExhausted.attempts` counts validation attempts plus 3 per model that failed on transport. `LLMExhausted` propagates by default: the Run stops at that node, the checkpoint stays at the last committed step, and `scout resume` reruns only that node. A stage may catch it where losing one item is acceptable (⏳ Analysis: skip one Posting) and must then log a Caveat.
- **Concurrency.** One process-wide `asyncio.Semaphore` (20, from settings) around every call, so Runtime needs no LangGraph `max_concurrency` for spend.
- **Balance.** The Run Controller calls `check_balance` before starting or resuming a Run and refuses below the floor (default $0.25), skipping it when `replay_cache` is set (Runtime LLD §6). It reads `effective_budget.remaining_usd` from `GET /api/v1/key`, the tightest of the key limit and the guardrail budgets; a null budget means uncapped and always passes.
- **Tracing and cost.** The outer runnable gets `run_name=f"llm:{name}"`. Each model is tagged `tier:<tier>` and `model:<id>` before wrapping, since `with_config` on a wrapped runnable names only the outer chain. Metadata carries `tier` and `name`. `ChatOpenRouter` runs reach LangSmith without cost, so a `ChatOpenRouter` subclass copies `response_metadata["cost"]` into `usage_metadata["total_cost"]`, which LangSmith reads as the run's `total_cost` (confirmed live; prompt and completion cost stay empty). The structured runnable returns only the schema instance: which model answered and how many retries ran is visible only in LangSmith, and nothing about it goes in `run_log`.
- **Build pass.** HLD §11 puts fallbacks in pass 2. The chain is a list, so pass 1 can run a 1-model chain with no code change.

## 13. Settings (`kernel/settings.py`)

One `Settings(BaseSettings)` (`pydantic-settings`) read from the root `.env`. `get_settings()` is cached, and on first load it exports the LangSmith env vars to `os.environ`, before any LangChain call reads them. `make_tiers`, `make_jev` and the Gateway all take this one object.

| Setting | Default |
|---|---|
| `openrouter_api_key`, `adzuna_app_id`, `adzuna_app_key`, `usajobs_api_key`, `usajobs_user_agent`, `langsmith_api_key` | required from `.env` (`adzuna_app_key` is read from `ADZUNA_API_KEY`) |
| `langsmith_tracing`, `langsmith_project` | from `.env`; exported with `langsmith_api_key` |
| `llm_cheap`, `llm_strong` (comma list in `.env`) | `deepseek/deepseek-v4.1-flash,minimax/minimax-m3.1-flash` |
| `reasoning_cheap`, `reasoning_strong` | `low`, `medium` |
| `max_tokens_cheap`, `max_tokens_strong` (each ≥ 1,000) | 2,048, 8,192 |
| `llm_concurrency`, `jev_concurrency` | 20, 8 |
| `balance_floor_usd` | 0.25 |
| `replay_cache` (path) | unset = off |
| `gateway_db` (path) | `.cache/gateway.sqlite` |
| `adzuna_daily_limit` | 25 |
| `l1_ttl_hours` | 24 |
| `l2_fresh_days` | 7 |
| `runs_db` (path) | `.cache/runs.sqlite` |
| `runs_dir` (path) | `runs` |

## 14. Replay cache (`kernel/replay.py`, pass 2)

Off by default. Setting `REPLAY_CACHE=<path>` switches on replay for the whole graph; the Gateway reads the same setting for jobs data, so HLD §7's "the whole graph runs from cached responses" holds as written.
- **LLM:** a ~25-line `BaseCache` on stdlib `sqlite3`, installed with `set_llm_cache()`. LangChain keys it on the messages plus the model id and parameters, so prompt edits, model changes and feedback retries all miss correctly. Written by hand to avoid the `langchain-community` dependency.
- **Jev:** a second table in the same file, used by `jev.judge` (§11).
- **A replayed Run is always obvious to the user.** ⏳ Brief: `render` puts a replay banner at the top of the Market Brief, read from settings ("Replayed run: jobs data, LLM and Jev responses came from the replay cache, not live sources"). ⏳ Collection logs a Caveat with the age of the oldest cached jobs response used, because replay ignores L1's TTL.
- Cache hits repeat the original cost in metadata. That's harmless.

## 15. Test seams

Every external call is injected through a constructor, so tests swap fakes without touching stage code. Offline tests use fakes; recorded Runs use the replay cache (§14).

| Seam | Real | Fake |
|---|---|---|
| LLM | `make_tiers(settings)` | `Tiers({...: [GenericFakeChatModel(...)]})` with canned JSON strings. This runs the real parse, feedback-retry and fallback code. |
| LLM with tools | same | `FakeToolChatModel` in `kernel/testing.py`: a few-line `GenericFakeChatModel` subclass whose `bind_tools` returns itself |
| Jev | `make_jev(settings)` | `Jev(fake_classifier({...}), cuts)` |
| Jobs APIs | `make_gateway(settings)` | `make_gateway(settings, transport=httpx.MockTransport(...))` for Gateway tests, `FakeGateway(results)` for stage tests ([Gateway LLD](gateway.md) §15) |

Live smoke tests use `minimax/minimax-m3.1-flash` and spend cents.

## 16. Build checklist (walking skeleton, pass 1)

Each step leaves one small `pytest` file behind.
1. `pyproject.toml` (`uv`, Python 3.12): `langgraph`, `langgraph-checkpoint-sqlite`, `langchain-core`, `langchain-openrouter`, `langchain-typesafe==0.0.1a3`, `langsmith`, `pydantic`, `pydantic-settings`, `pytest`. Pin the versions from the research.
2. `settings.py`. Test: the `max_tokens` floor rejects 999, and a comma list parses into a chain.
3. `types.py`. Test: Posting `key`, Salary bounds, Evidence sorting and dedup, unique Stat ids.
4. `state.py`: `State`, `merge`, `log()`, `owned()`, `StateWriteError`. Test: each of the four guard rules raises, and `log()` appends.
5. `thresholds.py` and `jev.py` with `fake_classifier`. Test: longest-prefix cut lookup, an unknown model fails, truncation sets `truncated`.
6. `llm.py` with `FakeToolChatModel`. Test: a bad-then-good fake response passes on the feedback retry, two bad responses per model reach the next model, and the chain running out raises `LLMExhausted`.
7. One live smoke script (not in CI): one `structured` call per tier, one Jev call, and a check that cost shows up in LangSmith.

Pass 2 adds the second model in each chain, Jev's LLM fallback hop and `replay.py`.

## 17. Deferred

See [future-scope.md](future-scope.md): the preferences slice, calibrated Jev cuts, Jev Choice/Score, the `jev-1.13` hop, per-call Jev ids, `run_log` timestamps, the production tier models, and Claude `cache_control`.
