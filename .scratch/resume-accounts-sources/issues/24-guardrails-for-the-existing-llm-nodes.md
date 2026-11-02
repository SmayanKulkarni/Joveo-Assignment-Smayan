# Guardrails for the existing LLM nodes

Type: grilling
Status: open
Assignee: none
Blocked by: [Research: open-source guardrail frameworks](22-research-open-source-guardrail-frameworks.md), [Research: guard models and PII filters](23-research-guard-models-and-pii-filters.md)

## Question

For every LLM node that exists today, which guardrails does it get, from which open-source tool, where do they live in the code, and what does a Run do when one trips?

Go through the table in [LLM nodes](../assets/llm-nodes.md) one row at a time: `intake`, `clarity_check`, `question`, `plan`, `fetch_agent`, `relevance`, `broaden`, `batch_extract`, `normalise_skills`, `write_brief`, `critic`, `revise` and `jev_fallback`.

- **Per node**: the input rails (prompt injection, jailbreak, off-topic, PII) and output rails (content safety, PII, claims) it needs, or "none, because..." when its input is trusted or its output is narrow enough that a strict schema and code checks already cover it. A Jev verdict is a single yes or no, so say what an injected Posting could actually do there.
- **Structure**: one guard step inside `Tiers` that every call routes through (with a per-`name` policy), or a guard per node, or a framework wrapping the whole graph. Prefer the single seam unless a node needs something only it can have. Decide whether the guard is a new kernel module and which LLD owns it (the Kernel LLD, or a new guardrails section).
- **Which tool**: from the two research tickets, the smallest set of frameworks and models that covers the rails chosen. Fewer dependencies wins when coverage is close, and nothing may break the 512 MB Render limit.
- **Tripping**: for each rail, whether a hit blocks the Run, drops the item (a Posting judged not relevant, with a count), asks the user at a Pause, or only adds a Caveat. Every effect must show up in the Run Notes, under the honesty rules.
- **Cost**: the extra calls and latency per Run, and whether screening runs on every Posting or a sample.
- **Replay and tests**: guard calls must go through the replay cache like LLM and Jev calls, and need fakes in `kernel/testing.py`. Name the red-team fixtures that prove each rail works (an injected Posting, an off-topic request).
- **Tracing**: guard inputs follow the same LangSmith rules as the text they check.

Load `langchain-router` first: this touches the model wrapper and graph nodes.
