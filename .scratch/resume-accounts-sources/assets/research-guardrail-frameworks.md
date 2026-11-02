# Research: open-source guardrail frameworks

Researched 2026-11-02 for [ticket 22](../issues/22-research-open-source-guardrail-frameworks.md). Sources are primary: PyPI JSON metadata, the GitHub repos and REST API, the projects' own docs, and the wheels' source code (downloaded with `pip download --no-deps` and read, never installed in the repo). Dependency fit was checked with `uv pip compile` in a scratch folder outside the repo. Memory numbers come from throwaway `uv run --no-project` environments on Windows, Python 3.12, so treat them as rough guides for Linux on Render. No real LLM calls were made, so no latency was measured.

The pins checked against: Python 3.12, `langchain-core==1.7.2`, `langgraph==1.2.18`, `pydantic==2.14.2`, plus the repo's other pins that matter here (`langchain-openrouter==0.2.9`, `langchain-typesafe==0.0.1a3`, `fastapi==0.162.0`, `httpx==0.28.1`, `rich>=15.0.0`).

## Summary table

| | NeMo Guardrails | Guardrails AI | LLM Guard | LangChain middleware |
|---|---|---|---|---|
| Package, version | `nemoguardrails` 0.24.1 (2026-09-16) | `guardrails-ai` 0.11.0 (2026-08-14) | `llm-guard` 0.3.16 (2025-05-19) | `langchain` 1.4.7 (2026-10-21) |
| Licence | Apache-2.0 | Apache-2.0 | MIT | MIT |
| Resolves with the pins | Yes | **No**: needs `rich<15`, the repo pins `rich>=15` | Yes | Yes |
| Pulls older LangChain or Pydantic | No. LangChain is no longer a core dependency | No (`langchain-core>=1.0,<2`) | No | No |
| Pulls `torch` | No, base install. Some optional rails need it | No, base install. Many validators do | **Yes**, `torch>=2.4`, `transformers==4.51.3` | No |
| Extra download on Linux | about 61 MB (onnxruntime, numpy, fastembed) | about 87 MB (litellm 37 MB) | about 3.1 GB (torch plus CUDA wheels) | about 0.2 MB |
| Import memory measured | +56 MB, no model loaded | +107 MB | not measured (torch alone is too big) | about 0 on top of LangChain |
| Extra LLM calls | One per self-check rail. Can point at OpenRouter | Only for LLM-based validators, through litellm | None | None for PII |
| Fits 512 MB Render free tier | Only with LLM-based and regex rails | Base yes, ML validators no | **No** | Yes |
| 2026 activity | 6 releases, commits on 2026-10-30 | 18 releases, commits in Oct 2026 | **Archived 2026-07-08** | more than 50 releases |

## Render's 512 MB limit and local models

Anything that loads a transformer in the API process does not fit. Sizes of the models these tools load, from the Hugging Face API:

- `protectai/deberta-v3-base-prompt-injection-v2` (LLM Guard's prompt injection scanner): 738 MB safetensors, 739 MB ONNX.
- `openai-community/gpt2-large` (NeMo's in-process jailbreak heuristics): 3,247 MB.
- `unitary/unbiased-toxic-roberta` (the kind of model Detoxify-based toxicity validators use): 499 MB.
- spaCy `en_core_web_lg` (Presidio's default NLP engine, used by NeMo's sensitive data rail, Guardrails AI `detect_pii`, and LLM Guard's Anonymize): 588 MB wheel.
- `all-MiniLM-L6-v2` ONNX (NeMo's default FastEmbed embedding model): 90 MB. This one is small, but it adds to a process that already holds the app.

Each of the first four is larger than the whole 512 MB on its own, before torch and the app. The fit question is settled by which checks run locally, not by which framework is chosen.

## NeMo Guardrails

Sources: [PyPI](https://pypi.org/project/nemoguardrails/), [GitHub NVIDIA-NeMo/Guardrails](https://github.com/NVIDIA-NeMo/Guardrails), [CHANGELOG](https://github.com/NVIDIA-NeMo/Guardrails/blob/develop/CHANGELOG.md), [check messages](https://docs.nvidia.com/nemo/guardrails/latest/run-guardrailed-inference/using-python-apis/check-messages), [model configuration](https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/yaml-schema/model-configuration), [self check](https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog/self-check.md), [LangChain integration](https://docs.nvidia.com/nemo/guardrails/latest/integration-with-third-party-libraries/langchain/langchain-integration), and the 0.24.1 wheel source.

**Fit with the pins.** 0.24.1 resolves with every pin. Its core dependencies are `pydantic>=2.5,<3`, `httpx`, `aiohttp`, `fastembed`, `onnxruntime`, `numpy`, `jinja2`, `lark`, `jsonschema` and a few small ones. LangChain was moved out of the core dependencies in 0.22.0 (2026-05-22); the LangChain code now sits in `nemoguardrails.integrations.langchain` and needs `langchain` installed separately. No torch in the base install. Resolved against the pins, it adds 45 packages, about 61 MB of Linux wheels (onnxruntime 24 MB, numpy 17 MB, pillow 7 MB). Apache-2.0.

**How it attaches.** Three ways:

1. `await rails.check_async(messages, rail_types=[RailType.INPUT])`: runs input or output rails on messages you hand it, with no generation. Returns a `RailsResult` with status PASSED, MODIFIED or BLOCKED. This is the one that fits inside `Tiers`: call it on the text before `call.ainvoke` and on `reply.text` after, and leave `ChatOpenRouter`, the retries and the strict schema alone. Tool rails do not run through `check()` or `check_async()`; only `generate_async()` runs them.
2. `RunnableRails`: a Runnable that wraps a chain or model and runs the rails round it. It makes NeMo own the call, which clashes with the per-model retry and fallback in `Tiers._driver`.
3. `GuardrailsMiddleware` (added 0.21.0): a `create_agent` middleware. Its `abefore_model` and `aafter_model` just call `check_async`. It needs `create_agent`, so it does not fit this system directly.

**Async.** `check_async` is async. The sync `check()` raises `RuntimeError` inside a running loop. NeMo imports `nest_asyncio` but does not apply it unless `DISABLE_NEST_ASYNCIO` is set to something other than true (`patch_asyncio.py`), so by default it does not patch uvicorn's loop. 0.24.0 made streaming fail closed when a rail action fails.

**What each check costs.**

- Self-check input and output rails (`self check input`, `self check output`) prompt an LLM and parse Yes or No. That is one extra LLM call per rail per checked message. The model comes from the `models` list in `config.yml`. `engine: openai` with `parameters.base_url` works for any OpenAI-compatible endpoint, and the configuration reference names OpenRouter. So the self-check can use our cheap OpenRouter model. That client is NeMo's own, so it bypasses `Tiers`: no `llm_concurrency` semaphore, no retries, no cost in `usage_metadata`, no replay cache. LLMRails can instead take a LangChain chat model through `LangChainLLMAdapter`, which needs `langchain` installed and makes the wrapper drop from the IORails engine to LLMRails.
- Measured: importing NeMo and building a `Guardrails` with only the two self-check rails took the process from 32 MB to 88 MB RSS, used the IORails engine, and downloaded no embedding model.
- The docs warn that self-check quality "is strongly dependent on the capability of the LLM to follow the instructions", and point to dedicated safety models (Nemotron Content Safety, Llama Guard 3, ShieldGemma) instead. Those run behind an endpoint, a NIM or a local GPU, not in a 512 MB box. Llama Guard through an OpenAI-compatible endpoint could in principle be an OpenRouter model, if OpenRouter carries one; not checked.
- Local rails in the library, read from the wheel:
  - Jailbreak heuristics (`jailbreak_detection_heuristics`): with no `server_endpoint`, it loads `gpt2-large` with torch in process and logs "NOT RECOMMENDED FOR PRODUCTION". Does not fit.
  - Jailbreak model (`jailbreak_detection_model`): with no endpoint, loads `Snowflake/snowflake-arctic-embed-m-long` with transformers plus an ONNX classifier. If torch or scikit-learn is missing, it logs an error and returns "not a jailbreak", so it **fails open**.
  - Sensitive data detection: Presidio with spaCy `en_core_web_lg` (588 MB). Does not fit.
  - `hf_classifier` (0.23.0): local transformers and torch, or a vLLM, KServe or FMS endpoint. 0.24.0 removed the install extra.
  - Injection detection: YARA rules for SQL, template, code and XSS injection in output text. Needs `yara-python`, no model. This is about code injection in what the model writes, not prompt injection.
  - Regex rail: rule based, no model.
  - Embedding-based dialog rails and the knowledge base use FastEmbed `all-MiniLM-L6-v2` (90 MB ONNX) by default.
  - Many rails in `library/` call hosted vendors (ActiveFence, Cleanlab, Fiddler, GCP Moderate Text, Pangea, Patronus, Private AI, Trend Micro, CrowdStrike and others). Out of scope.

**What it can check.** Input rails (self-check, jailbreak, PII, topic safety, content safety), output rails (self-check, fact checking, hallucination, PII, injection), retrieval rails on retrieved chunks, dialog rails in Colang, and tool-call and tool-result rails (only through `generate_async`).

**Upkeep.** Six releases in 2026 (0.20.0 on 2026-01-22 to 0.24.1 on 2026-09-16), last commit 2026-10-30. Breaking changes land often: 0.22.0 renamed `generate`/`stream` to `generate_async`/`stream_async` and switched the LLM layer to an `LLMModel` protocol; 0.24.0 removed `output_mapping` and the `hf-classifier` extra. Pin the minor version. The GitHub API reports the licence as NOASSERTION, but PyPI metadata says Apache-2.0.

## Guardrails AI and its validators

Sources: [PyPI](https://pypi.org/project/guardrails-ai/), [GitHub guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails), [releases](https://github.com/guardrails-ai/guardrails/releases), [README news](https://github.com/guardrails-ai/guardrails/blob/main/README.md), [issue 1560, hub sunset](https://github.com/guardrails-ai/guardrails/issues/1560), [quickstart](https://www.guardrailsai.com/docs/getting_started/quickstart), [LangChain integration](https://www.guardrailsai.com/docs/integrations/langchain), and the 0.11.0 wheel source.

**Fit with the pins.** 0.11.0 requires `rich>=13.6.0,<15.0.0`. The repo pins `rich>=15.0.0` (used by `clients/cli.py`), so `uv pip compile` fails: "guardrails-ai>=0.11.0 depends on rich>=13.6.0,<15.0.0 and you require rich>=15.0.0". Left unconstrained, the resolver quietly picks `guardrails-ai==0.1.8`, a 2023 release, which is a trap to watch for. With the `rich` pin removed, 0.11.0 resolves with `rich==14.3.4`, `litellm==1.106.6` and `openai==2.54.0` (it needs `openai<3`; `langchain-openai` currently resolves `openai` 3.x, which does not matter unless both are installed). It also pulls `opentelemetry-sdk` and both OTLP exporters, `lxml`, `faker`, `tiktoken`, `pip>=26.1.2`. About 87 MB of extra Linux wheels. `langchain-core>=1.0,<2` and `pydantic>=2.4.2,<3` match the pins. No torch in the base install. Apache-2.0.

**How it attaches.** `Guard().use(Validator(...))` then `guard.validate(text)` or `guard.parse(text)` checks a string with no LLM call. `AsyncGuard` has async `validate` and `parse`. `guard.to_runnable()` gives a LangChain Runnable meant to sit after the model (`prompt | model | guard.to_runnable() | parser`); it calls the guard on the message text and runs as a "parser" step. A Guard can also own the LLM call through litellm, which would replace `ChatOpenRouter`. The validate-only path fits inside `Tiers` as a check before and after `call.ainvoke`.

**Async.** `AsyncGuard` exists. Validators that only have a sync `validate` are run with `loop.run_in_executor`, so a slow local model does not block the loop, but it still takes the shared CPU.

**Hub and tokens.** As of the 2026-07-06 notice, the hub CLI (`guardrails hub install`), the private registry `pypi.guardrailsai.com` and the hosted remote-inference servers `hub.api.guardrailsai.com` were shut down on 2026-08-25. Validators are now public PyPI packages named `guardrails-ai-<name>`. Issue 1560 says "No `guardrails configure` / API key is required anymore". At the time, 50 of 64 validators were on PyPI. Validators that used remote inference must now run their model locally or on your own endpoint. The `use_remote_inferencing` setting still exists in 0.11.0 and defaults to False; the code still points 401s at `guardrailsai.com/hub/keys`.

**What validators cost.** Dependencies of a sample, from PyPI (all published 2026-07-20):

| Validator package | Needs | Fits 512 MB |
|---|---|---|
| `guardrails-ai-regex-match` | `rstr` | Yes |
| `guardrails-ai-ban-list` | `fuzzysearch` | Yes |
| `guardrails-ai-secrets-present` | `detect-secrets` | Yes |
| `guardrails-ai-detect-pii` | Presidio, `nltk`, numpy (spaCy model) | No |
| `guardrails-ai-guardrails-pii` | `gliner`, Presidio | No |
| `guardrails-ai-toxic-language` | `torch`, `transformers`, `detoxify` | No |
| `guardrails-ai-nsfw-text` | `torch`, `transformers` | No |
| `guardrails-ai-detect-jailbreak` | `torch>=2.4`, `transformers>=4.40` | No |
| `guardrails-ai-restrict-to-topic` | `torch`, `transformers`, `openai` | No |
| `guardrails-ai-unusual-prompt` | `litellm<1.82.6` (LLM call) | Memory yes, see below |
| `guardrails-ai-llm-critic` | `litellm<1.82.6` (LLM call) | Memory yes, see below |

The two LLM-based validators pin `litellm<1.82.6`, while `guardrails-ai` 0.11.0 needs `litellm>=1.82.5`, which leaves only the 1.82.5 line. The 0.9.3 release notes say litellm was "urgently pinned below a vulnerable version". litellm can call OpenRouter models, but again outside `Tiers`.

Measured: importing `guardrails` took the process from 32 MB to 139 MB RSS.

**What it can check.** Mostly output validation: schema, regex, PII, toxicity, secrets, topics, plus some input checks (jailbreak, unusual prompt). Its original core feature, validating structured LLM output against a schema and re-asking, overlaps with what `Tiers.structured` already does.

**Upkeep.** 18 releases in 2026, 0.11.0 on 2026-08-14, commits in October 2026. The hub shutdown is a big change this year.

## LLM Guard (Protect AI)

Sources: [PyPI](https://pypi.org/project/llm-guard/), [GitHub protectai/llm-guard](https://github.com/protectai/llm-guard) and its README.

- **Archived.** The repo was archived on 2026-07-08 (commit "Archiving Project (#355)"). The README says "This project and its associated models on Hugging Face are no longer under active development or maintained." Last release 0.3.16 on 2025-05-19. No 2026 releases.
- **Fit.** It resolves with the pins, but it hard-requires `torch>=2.4.0`, `transformers==4.51.3` (exact pin), `presidio-analyzer==2.2.358`, `spacy`, `nltk` and `regex==2024.11.6` (exact pin). Resolved for Linux x86_64 it pulls `torch==2.15.0` and the CUDA wheels, about 3.1 GB of downloads. Python `<3.13`. MIT.
- **How it attaches.** Plain functions: `scan_prompt(scanners, prompt)` and `scan_output(scanners, prompt, output)`. They are synchronous and CPU-bound, so in async code they need `asyncio.to_thread`. They could sit inside `Tiers` as checks, but that is moot.
- **Cost.** The scanners worth having (PromptInjection, Toxicity, Anonymize, BanTopics) load transformer models. The prompt injection model alone is 738 MB. **It does not fit the 512 MB Render free tier**, and with the project archived it should not be added anyway.

## LangChain's own guardrail middleware

Sources: [Guardrails docs](https://docs.langchain.com/oss/python/langchain/guardrails), [built-in middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in), the `langchain` 1.4.7 wheel (`langchain/agents/middleware/pii.py`, `_redaction.py`), and the `langchain-openai` 1.7.3 wheel (`middleware/openai_moderation.py`). The repo's `langchain-middleware` skill covers HITL and custom hooks but not guardrails, so the live docs were read.

**What exists in v1.** The guardrails page documents two built-in middleware: `PIIMiddleware` and `HumanInTheLoopMiddleware`. The rest of the built-in list is limits, retries and fallbacks (`ModelCallLimitMiddleware`, `ToolCallLimitMiddleware`, `ModelRetryMiddleware`, `ModelFallbackMiddleware`, and others). There is no prompt-injection or toxicity middleware in `langchain`. The page shows custom guardrails as examples only: a keyword `ContentFilterMiddleware` on `before_agent`, and a `SafetyGuardrailMiddleware` on `after_agent` that asks a second model for SAFE or UNSAFE. `langchain-openai` ships `OpenAIModerationMiddleware`, which calls OpenAI's hosted moderation endpoint with an OpenAI client; that needs an OpenAI key, not OpenRouter, and is a hosted vendor check.

**PIIMiddleware.** Rule based, no model. Built-in types: `email`, `credit_card` (Luhn checked), `ip`, `mac_address`, `url`. Strategies: `redact` (`[REDACTED_EMAIL]`), `mask` (last 4 kept), `hash`, `block` (raises `PIIDetectionError`). Custom types take a regex or a function. No phone number or name detector is built in, so resume contact details beyond email and URLs need a custom regex. Flags: `apply_to_input` (default on), `apply_to_output`, `apply_to_tool_results`.

**Fit.** `langchain` 1.4.7 needs `langchain-core>=1.6.13`, `langgraph>=1.2.12,<1.3`, `pydantic>=2.7.4`. All match the pins; the only new package is `langchain` itself (about 170 KB). Importing `langchain.agents.middleware` next to `langchain_openrouter` added no measurable memory.

**Outside `create_agent`.** The middleware class itself works on `AgentState` through `before_model` and `after_model` hooks that `create_agent` wires into its graph; there is no Runnable wrapper and no documented way to run it alone. But the detection and redaction code under it is public: `RedactionRule` and `PIIDetectionError` are exported from `langchain.agents.middleware`. Tested in a throwaway env:

```python
from langchain.agents.middleware import RedactionRule
text, matches = RedactionRule("email", "redact").resolve().apply(text)
```

That turned "Mail me at a.b@x.com, card 4111 1111 1111 1111, site https://evil.example/x" into "Mail me at [REDACTED_EMAIL], card **** **** **** 1111, site <url_hash:e9b74d07>", and the `block` strategy raised `PIIDetectionError`. It is plain sync string work, so it can sit inside `Tiers` without blocking the loop in any way that matters. The detectors are module-level functions in a private module (`_redaction.py`), so only the exported names should be relied on.

**Upkeep.** More than 50 `langchain` releases in 2026. The docs note `apply_to_output` on streamed output needs `langchain>=1.3.2`.

## What the structured outputs already make moot

From [LLM nodes](llm-nodes.md), every node but `fetch_agent` returns strict JSON validated by Pydantic, with a retry on bad output.

- **Output schema rails** (Guardrails AI's schema validation, NeMo output format checks) duplicate `_response_format(strict=True)` plus `model_validate_json` plus the feedback retry.
- **Output toxicity and PII on enum, boolean and number fields** are moot: `relevance`, `critic`, `clarity_check` and `jev_fallback` return verdicts, and `batch_extract` returns grounded facts that `_grounded` already ties back to the Posting text.
- **Output rails still have something to check** where a node writes free text that a user reads: the Clarifying Question (`question`), the Search Plan's query strings (`plan`, `broaden`), and Insights and Recommendations (`write_brief`, `revise`).
- **Input rails** matter most where third-party text reaches a model: Posting text into `relevance` and `batch_extract`, and resume text into the new resume parse and matching. A structured output limits what an injection can do but does not stop a verdict being flipped.
- **Tool rails**: `fetch_agent` already has `_bound`, `MAX_FETCHES` and arg errors as `ToolMessage`, and its tool results are counts, not Posting text. NeMo's tool rails also need `generate_async`, which would mean NeMo owning the call.
- **Retrieval rails**: there is no retrieval step. Posting text is passed in the prompt, so an input check on it plays that role.

## Other packages seen

- `langchain-guardrails` 0.0.7 on PyPI: a third-party wrapper over `nemoguardrails>=0.11`, `langchain-core>=0.3.45`. No 2026 releases. Not looked at further.
