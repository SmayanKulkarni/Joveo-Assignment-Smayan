# Research: Jev on OpenRouter

Type: research
Status: resolved
Findings: branch `research/jev-on-openrouter`, file `research/jev-on-openrouter.md`

## Question

How is Jev (TypeSafe's decision model) exposed on OpenRouter, and can it serve the three placements in [Where does Jev make routing decisions?](07-jev-placement.md)?

Specifically:
- Model id(s) on OpenRouter, pricing, rate limits.
- API shape: OpenAI-style chat completions only, or the TypeSafe `/v1/systemone` classifier contract (Noul / Choice / Score with probabilities)?
- Does it return probabilities / confidence through OpenRouter, or only text? If only text, how are probabilities obtained (logprobs?), and what is lost?
- Can `langchain-typesafe`'s `TypeSafeClassifier` be pointed at OpenRouter via `base_url`, or is a thin adapter needed?
- Fallback: if Jev on OpenRouter cannot return probabilities, what are the realistic options (direct TypeSafe API, LangSmith Gateway BYOK, LLM structured-output classifier)?

## Answer

Full findings on branch `research/jev-on-openrouter` (commit `d596f2a`), file `research/jev-on-openrouter.md`. Verified against source and a mocked request; no live call yet (no key in env), so the first real call is the confirmation step.

- **Available, with full probabilities.** `typesafe/jev-1.14` (alias `~typesafe/jev-latest`; `jev-1.13` still listed). $0.042/M input, output free, cost in `usage.cost`. No published rate limit.
- **Not a chat model**: no `/chat/completions`, no logprobs involved. Hidden from the default model list (`?output_modalities=decisions` shows it).
- **Two endpoints, one OpenRouter key**: `POST /api/v1/systemone` (TypeSafe-native contract) and `POST /api/alpha/decisions` (OpenRouter's cross-vendor decisions format). Both return Noul probability, Choice per-label distribution + confidence, Score expected value + per-level distribution + confidence.
- **`TypeSafeClassifier` works unchanged**: `base_url="https://openrouter.ai/api"`, OpenRouter key, pin `model="typesafe/jev-1.14"`.
- **Watch-outs for LLD**: the classifier drops `usage.cost` and request id; set both or neither Noul criteria sides; keep each request under ~32 KB of text (above that Jev switches to a slower, less accurate long-context mode), which affects long Posting descriptions and the critic.
- **Fallback order**: OpenRouter decisions endpoint via thin wrapper → direct TypeSafe → LangSmith Gateway BYOK (skill-sourced, unconfirmed in docs) → LLM structured output (loses distributions).

Consequence for the HLD: the Decision Provider component reaches Jev through OpenRouter with the same key as the LLMs; no extra credential.
