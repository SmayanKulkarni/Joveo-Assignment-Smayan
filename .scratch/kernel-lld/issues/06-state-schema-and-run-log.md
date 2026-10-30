# State schema, reducers and run_log

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 05

## Question

What is the Pydantic graph state: each slice's key, owning component, type and reducer, and the shape of the `run_log` the Kernel owns?

- Slices per [docs/HLD.md](../../../docs/HLD.md) §3: Request & Plan, Collection (messages, Postings, Sample, attempt count), Analysis (extractions keyed by Posting, stats), Brief (draft, critic verdicts, rendered output), preferences, `run_log`.
- **Reducers**: Postings across broaden attempts (merge by key vs replace); extraction merge from the `Send` fan-out; messages (`add_messages`), and whether they reset between broaden attempts; `run_log` append-only.
- **Reset semantics**: what clears when `broaden` or a `plan_review` reject loops back.
- **`run_log` entry**: fields (node, kind, message, data, timestamp?), the kinds Run Notes need (routing decision with reason, Clarifying Question + answer, final Search Plan, Assumption), and whether timestamps break deterministic replay.
- How the "stage-private fields are added by the stage's LLD" rule is expressed in code (one schema file each stage extends, or composed sub-models).

Input from [Shared domain types](05-shared-domain-types.md):
- **Search Plan ownership.** `broaden` (Collection) produces a new Search Plan, but Request & Plan owns the plan slice. Decide who writes it: a Collection-owned "current plan" slice, moving `broaden` into Request & Plan, or something else.
- **`--focus`.** It is a Run option, not part of the Hiring Request, so it needs its own slice.
- **Type facts.** Posting identity is `key` (`source:source_id`), so a Postings reducer can merge by key. All domain types are frozen.

## Answer (2026-10-30)

Grilled in three rounds. Everything below goes in `talent_scout/kernel/state.py`.

**Layout.** One flat `State(BaseModel)`, `ConfigDict(frozen=True, extra="forbid")`, fields grouped in comment blocks by owner. Stage-owned types (Extraction, MarketBrief, ...) live in that stage's `types.py`, which may import only `kernel.types`; `kernel/state.py` imports them, so there is no cycle. Nested slice sub-models were rejected: LangGraph puts reducers only on top-level fields, so a nested slice is `LastValue` and the parallel `batch_extract` writes would raise `InvalidUpdateError`. Frozen because mutating `state` in place is a silent no-op in LangGraph; a node must return an update.

**Reducers.** Every slice is `LastValue`: a node returns the whole new value (`{"postings": {**state.postings, **new}}`). The only reducer is `extractions` (merge by key), because the `Send` fan-out has N branches writing it in one super-step and a branch sees only its payload. `Send` stays (dropping it loses per-branch retry on resume and changes the HLD graph).

**Slices.**

| Key | Owner | Type (default) | Written by | Reset |
|---|---|---|---|---|
| `request_text` | input | `str` (required) | Run Controller | never |
| `focus` | input | `list[Dimension]` (`[]` = all) | Run Controller | never |
| `hiring_request` | Request & Plan | `HiringRequest \| None` | `intake` (refined after answers per that LLD) | |
| `questions` | Request & Plan | `list[ClarifyingQuestion]` (`[]`) | `clarity_check` adds, `clarify` fills answers | never; re-asks counted from it |
| `assumptions` | Request & Plan | `list[Assumption]` (`[]`) | Request & Plan nodes | |
| `search_plan` | Request & Plan | `SearchPlan \| None` | `plan` | rewritten on `plan_review` reject |
| `messages` | Collection | `list[AnyMessage]` (`[]`) | `fetch_agent`, `tools` | `[]` on each `broaden` |
| `postings` | Collection | `dict[str, Posting]` (`{}`) | `collect`; first copy seen wins | kept across attempts |
| `sample` | Collection | `list[str]` (`[]`), Posting keys in order | `relevance` | recomputed each attempt |
| `broadened_plans` | Collection | `list[SearchPlan]` (`[]`) | `broaden` appends | |
| `extractions` | Analysis | `Annotated[dict[str, Extraction], merge]` (`{}`) | `batch_extract` x N | |
| `stats` | Analysis | `MarketStats \| None` | `stats` | |
| `brief` | Brief | `MarketBrief \| None` | `render` | |
| `brief_markdown` | Brief | `str \| None` | `render` | |
| `run_log` | Kernel (all nodes) | `list[RunLogEntry]` (`[]`) | everyone via `log()` | never; prefix-checked |

Read-only `@property` views: `current_plan` (last of `broadened_plans`, else `search_plan`) and `sample_postings`. Attempt count is `len(broadened_plans)`; there is no counter slice. Stage-private fields (Brief draft, critic verdicts, `plan_review` feedback, each stage's decision fields) are added here by their stage LLDs. `preferences` is left to the Long-term memory LLD.

**Search Plan and `broaden`.** Request & Plan owns the approved `search_plan`; Collection owns `broadened_plans`. One writer per slice, and every revision reaches Run Notes without extra logging.

**Messages reset.** `broaden` returns `{"messages": []}`, so the next `fetch_agent` round starts from the new `current_plan`; fetched Postings stay in `postings`.

**Routing.** Routers are pure functions of state. The node before a router stores its outcome in a slice it owns (e.g. a clarity `Judgement`, a Sufficiency verdict) and writes a `route` entry to `run_log`; the router only reads that slice. No extra LLM or Jev call.

**`run_log`.** Narrative only: routing decisions and reasons, Jev outcomes, fallbacks used, skip counts, the original request wording. Domain objects are not copied in; Brief builds Run Notes from `run_log` plus the slices (questions, assumptions, `current_plan`, `sample`). This narrows HLD §9's wording; Run Notes content is unchanged.

```python
class LogKind(StrEnum): route, pause, warning, note

class RunLogEntry(BaseModel):   # frozen, extra="forbid"
    node: str
    kind: LogKind
    message: str
    data: dict[str, JsonValue]  # plain JSON: strict msgpack blocks models in untyped fields
```

No timestamp: list order is event order, LangSmith has the times, and replay transcripts stay byte-identical. `batch_extract` branches never log; `stats` writes one summary entry. Helper: `log(state, node, kind, message, **data) -> {"run_log": [*state.run_log, entry]}`.

**Write guard.** Each field carries `Field(json_schema_extra={"owner": ...})` (`"input"`, `"kernel"`, or a component). The Kernel exports `owned(node, owner)`; Runtime applies it to every node at wiring. It raises `StateWriteError(node, key, reason)` when:
- an update key's owner is not this node's owner (`run_log` is writable by all; `"input"` by none),
- a value fails its field's type, checked with a cached `TypeAdapter` (the `ValidationError` is chained),
- a `run_log` update does not start with the current log.

Routers are wrapped the same way and raise `StateWriteError` for a `Send` whose `arg` is not a model instance, since LangGraph validates neither node outputs nor `Send` payloads.

**Left out:** recorded in [docs/lld/future-scope.md](../../../docs/lld/future-scope.md).
