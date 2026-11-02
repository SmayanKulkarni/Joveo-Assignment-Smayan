# Research: open-source guardrail frameworks

Type: research
Status: open
Assignee: none
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
