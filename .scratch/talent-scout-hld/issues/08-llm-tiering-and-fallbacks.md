# How are LLMs tiered, and how are failures handled?

Type: grilling
Status: resolved

## Question

What LLM structure does the HLD commit to, and what is deferred?

## Answer

Resolved during charting.

- All LLM calls go through **OpenRouter**.
- HLD keeps only the *concept* of tiers (a cheaper tier for batch extraction and question drafting, a stronger tier for planning, brief writing and critique) and a `.with_fallbacks()` chain per tier.
- Malformed structured output: retry with the validation error fed back, then fall back.
- Specific models are decided later, in LLD.
