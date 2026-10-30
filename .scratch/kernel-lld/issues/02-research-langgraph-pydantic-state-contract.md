# Research: LangGraph/LangChain contract for Pydantic state and structured output

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by:
Findings: branch `research/langgraph-pydantic-state-contract` (commit `4172fde`), file `research/langgraph-pydantic-state-contract.md`

## Question

What do current LangGraph and LangChain versions guarantee for a Pydantic-everywhere Kernel?

- Current stable versions of `langgraph`, `langgraph-checkpoint-sqlite`, `langchain-core`, `langchain-openai`, and Python support.
- **Pydantic `BaseModel` as the graph state schema**: how `Annotated` reducers work on model fields; what nodes receive (model instance) vs return (partial dict or model); when validation runs and its cost; known caveats (defaults, `Send` payloads with a Pydantic state, subgraphs, `add_messages` on a Pydantic field).
- **Checkpoint serialization**: do Pydantic v2 models (nested, with enums, datetimes, `Decimal`) round-trip through `SqliteSaver` / `JsonPlusSerializer` and `SqliteStore`? Any msgpack allowlist / "unregistered type" deserialization warnings or settings in recent versions, and what must be configured.
- **Structured output failures**: behaviour of `with_structured_output(schema, include_raw=True)` on a malformed response (what `parsing_error` holds), and the idiomatic way to retry with the validation error fed back.
- **Fallbacks**: does `.with_fallbacks()` compose with `with_structured_output` (fallback per tier model, each structured), and which exceptions trigger it.
- **Tracing**: confirm LangSmith picks up chat-model calls from env vars alone (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`) and how to set `run_name`/tags on a bound model.

## Answer

Full findings on branch `research/langgraph-pydantic-state-contract` (commit `4172fde`), file `research/langgraph-pydantic-state-contract.md` (ends with an 8-point LLD recommendation). Sourced from package source and run in a scratch venv against a mock OpenAI endpoint. Not tested: real OpenRouter models and async variants.

- **Versions**: langgraph 1.2.18, langgraph-checkpoint 4.3.1, checkpoint-sqlite 3.1.2, langchain-core 1.7.2, langchain-openai 1.7.3, langsmith 0.14.16, pydantic 2.14.2; Python 3.10+ (target 3.12). Pydantic everywhere works, with rules.
- **State validation**: `Annotated` reducers on model fields work, and each node receives a freshly validated instance (on every node's input, contrary to the docs). Writes are never validated, so a bad write fails at the next node's read (wrong blame) or leaks silently from the last node.
- **Node return rule**: return partial dicts. Returning the whole model double-appends reducer lists. `Send` payloads aren't validated, so build them as model instances. `invoke()` returns a raw dict missing never-written fields.
- **Checkpoints**: nested models, enums, datetimes, `Decimal`, UUID and Pydantic interrupt payloads round-trip across processes. By default each type logs an "unregistered type … will be blocked" warning. `LANGGRAPH_STRICT_MSGPACK=true` makes `compile()` allowlist every type reachable from the schema; `Any` fields come back as plain dicts.
- **Store**: `SqliteStore` can't take models or `Decimal`s (`model_dump(mode="json")` / `model_validate`), and needs its own autocommit connection (sharing with `SqliteSaver` raises a nested-transaction error). Mainly a Runtime LLD concern.
- **Structured output**: in `ChatOpenAI`'s json_schema mode a malformed response raises `ValidationError` inside the call, so `include_raw` can't catch it. In function_calling mode failures give `parsed=None, parsing_error=None`, so check `parsed is not None`. No built-in retry; feeding the error back as a `ToolMessage` worked on the second try. Behaviour under `ChatOpenRouter` is not verified.
- **Fallbacks**: `.with_fallbacks()` composes with `with_structured_output` in either order and every fallback gets the schema. Any exception triggers it by default, but `include_raw`-caught parse failures don't.
- **Tracing**: env vars alone trace a model call, but they're read once and cached, so set them before the first call. `.with_config(run_name, tags)` on a structured runnable names only the outer chain, so set it on the model before `with_structured_output`.
