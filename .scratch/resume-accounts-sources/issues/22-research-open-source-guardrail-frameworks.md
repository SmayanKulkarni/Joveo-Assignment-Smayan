# Research: open-source guardrail frameworks

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Which open-source guardrail frameworks could wrap this system's LLM calls, and what would each one cost to fit in?

The calls are listed in [LLM nodes](../assets/llm-nodes.md). They all go through `Tiers.structured` and `Tiers.chat` in `src/talent_scout/kernel/llm.py` (OpenRouter models through `langchain-openrouter`, async, strict JSON schema), plus Jev through `langchain-typesafe`. They are not `create_agent` agents.

For each of **NeMo Guardrails**, **Guardrails AI** (and its Hub validators), **LLM Guard** (Protect AI), and **LangChain's own guardrail middleware** (PII, and any others in v1), find out:

- **Fit with the pins**: Python 3.12, `langchain-core==1.7.2`, `langgraph==1.2.18`, `pydantic==2.14.2`. Does it pull an older LangChain or Pydantic, or `torch`? Its install size, and its licence.
- **How it attaches**: as a wrapper round a Runnable, a separate check called before and after the model, or only as its own LLM client. Can it sit inside `Tiers` (one seam for every node) without replacing `ChatOpenRouter`, the retries or the structured output? LangChain middleware is built for `create_agent`, so check whether it works outside one.
- **Async and streaming**: does it block the event loop?
- **What each check costs**: extra LLM calls (NeMo's self-check rails call a model; through which provider, and can it use our OpenRouter cheap tier?), local models in memory, and latency per call. The API runs on Render's free web service (512 MB RAM, shared CPU), so anything that loads a transformer locally probably doesn't fit. Say so plainly when it doesn't.
- **What it can check**: input rails (prompt injection, jailbreak, off-topic, PII), output rails (toxicity, PII, schema), and retrieval or tool rails. Which of these the system's structured outputs already make moot.
- **Upkeep**: release activity in 2026, and whether Guardrails AI Hub validators need a hosted account or token.

Load `langchain-router` first, and read the LangChain guardrails and middleware docs from it rather than from memory.

Hosted vendor guardrails (AWS Bedrock Guardrails, Azure AI Content Safety, Lakera, and the like) are out of scope. Mention one only where an open-source tool depends on it.

Write long notes in `../assets/research-guardrail-frameworks.md` and a short answer here.

## Answer

Researched 2026-11-02. Long notes, sources, the resolver runs and memory measurements: [research-guardrail-frameworks.md](../assets/research-guardrail-frameworks.md). These are facts; [ticket 24](24-guardrails-for-the-existing-llm-nodes.md) decides what each node gets.

| | NeMo Guardrails 0.24.1 | Guardrails AI 0.11.0 | LLM Guard 0.3.16 | LangChain `langchain` 1.4.7 |
|---|---|---|---|---|
| Licence | Apache-2.0 | Apache-2.0 | MIT | MIT |
| Resolves with the pins | Yes | **No**, needs `rich<15` (repo pins `>=15`) | Yes | Yes |
| Torch | Not in base install | Not in base; most ML validators need it | **Required**, about 3.1 GB on Linux | No |
| Attaches inside `Tiers` | `await check_async(...)` before and after the call | `AsyncGuard.validate(text)` after the call | Sync `scan_prompt`/`scan_output`, needs `to_thread` | Exported `RedactionRule(...).resolve().apply(text)` |
| Extra LLM calls | One per self-check rail, can use OpenRouter cheap tier | Only LLM validators, through litellm | None | None |
| Import memory | +56 MB, no model | +107 MB | n/a (models 500+ MB each) | about 0 |
| 2026 upkeep | 6 releases, active | 18 releases, active; hub shut down 2026-08-25 | **Archived 2026-07-08** | Active |

- **512 MB Render free tier.** Every local ML check is too big: the LLM Guard prompt injection model is 738 MB, NeMo's in-process jailbreak heuristics load `gpt2-large` (3.2 GB), and the Presidio PII rails load spaCy `en_core_web_lg` (588 MB). What fits is rule based (LangChain's PII redaction, regex, ban lists, NeMo's YARA output rail) or an extra LLM call (NeMo self-check, Guardrails AI LLM validators).
- **LLM Guard does not fit and is archived.** It hard-requires torch and `transformers==4.51.3`.
- **NeMo Guardrails** no longer depends on LangChain (since 0.22.0). Its `check_async` runs input or output rails with no generation, so it can sit in `Tiers` without replacing `ChatOpenRouter`, retries or the strict schema. Self-check rails point at OpenRouter with `engine: openai` and `base_url`, but through NeMo's own client, outside the semaphore, retries, cost tracking and replay cache. Its local jailbreak model fails open when torch is missing. Tool rails only run through `generate_async`, where NeMo owns the call.
- **Guardrails AI** conflicts with the repo's `rich>=15` pin; unconstrained, the resolver drops to the 2023 release 0.1.8. Validators are now public PyPI packages (`guardrails-ai-<name>`) and need no account or token; hosted remote inference is gone. Its LLM validators pin `litellm<1.82.6`, which leaves only 1.82.5.
- **LangChain middleware** has only `PIIMiddleware` (email, credit card, IP, MAC, URL; redact, mask, hash or block) and HITL as built-in guardrails, with no injection or toxicity check. The middleware needs `create_agent`, but its `RedactionRule` works on plain strings outside an agent (tested). `OpenAIModerationMiddleware` in `langchain-openai` calls OpenAI's hosted endpoint, so it is out of scope.
- **Already moot:** output schema rails (strict JSON schema and Pydantic do this), and output toxicity or PII on verdict and grounded-fact nodes. Free text a user reads (`question`, `plan` queries, `write_brief`, `revise`) and third-party text going in (Postings, resumes) are where checks would still add something.
