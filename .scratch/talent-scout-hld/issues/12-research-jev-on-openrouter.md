# Research: Jev on OpenRouter

Type: research
Status: open
Findings: branch `research/jev-on-openrouter`, file `research/jev-on-openrouter.md`

## Question

How is Jev (TypeSafe's decision model) exposed on OpenRouter, and can it serve the three placements in [Where does Jev make routing decisions?](07-jev-placement.md)?

Specifically:
- Model id(s) on OpenRouter, pricing, rate limits.
- API shape: OpenAI-style chat completions only, or the TypeSafe `/v1/systemone` classifier contract (Noul / Choice / Score with probabilities)?
- Does it return probabilities / confidence through OpenRouter, or only text? If only text, how are probabilities obtained (logprobs?), and what is lost?
- Can `langchain-typesafe`'s `TypeSafeClassifier` be pointed at OpenRouter via `base_url`, or is a thin adapter needed?
- Fallback: if Jev on OpenRouter cannot return probabilities, what are the realistic options (direct TypeSafe API, LangSmith Gateway BYOK, LLM structured-output classifier)?
