# LLM nodes: what each one reads and what already guards it

Taken from the code at `a38bdb2` on 2026-11-02 while charting the guardrail tickets. These are facts, not decisions. [Guardrails for the existing LLM nodes](../issues/24-guardrails-for-the-existing-llm-nodes.md) decides what to add.

Every LLM call goes through one seam: `Tiers.structured` or `Tiers.chat` in `src/talent_scout/kernel/llm.py`. Each call has a `name`, and the model sits behind OpenRouter. Jev calls go through `Jev` in `kernel/jev.py`, and when Jev fails they fall back to `jev_fallback`, which is a cheap LLM call.

## Guards that exist today

- **Strict JSON schema** on every `structured` call (`_response_format`, `strict=True`), Pydantic validation, and one retry with the validation error as feedback.
- **`max_tokens`** for each tier, a floor of 1000, and a length cut-off that is never retried.
- **Concurrency and retries**: `llm_concurrency` semaphore, 3 retries on provider errors, then the next model in the tier.
- **Grounding by code**: `analysis/nodes.py:_grounded` drops any skill or years figure not found in the Posting's own text. `normalise_skills` may alias only names the model was shown.
- **Jev critic** on every Insight in the Brief, which sees only the Stats the claim cites, and a `revise` loop for flagged Insights.
- **Honesty rules**: Stats are computed by code, Advertised and Estimated pay are never pooled, and Assumptions and Caveats go in the Run Notes.
- **Tool bounds**: `_bound` offers `fetch_agent` only the tools that suit the plan, `MAX_FETCHES` caps tool calls, and bad tool args come back as an error `ToolMessage`.
- **Trust boundary**: the web API checks `Origin` and the access code. Postings stay out of LangSmith traces (`gateway.py:_resolve`).

There is no input screening, no prompt-injection check, no PII filter on model input, and no content-safety check on model output.

## The nodes

| Node (`name`) | File | Tier / kind | Reads untrusted text from | Writes | Guards today |
|---|---|---|---|---|---|
| `intake` | `request_plan/nodes.py` | cheap, structured `RequestDraft` | The user's request text and answers to Clarifying Questions | Hiring Request draft | Schema |
| `clarity_check` | `request_plan/nodes.py` | Jev `Noul` per field, `jev_fallback` | The draft and request text | Which fields are ambiguous | Jev cuts in `kernel/thresholds.py`, a Caveat when the fallback or a shortened text is used |
| `question` (in `clarify`) | `request_plan/nodes.py` | cheap, structured `QuestionDraft` | The draft and request text | A Clarifying Question shown to the user | Schema |
| `plan` | `request_plan/nodes.py` | strong, structured `SearchPlan` | The Hiring Request, Assumptions, and plan rejection feedback typed by the user | Search Plan | Schema, plan approval Pause |
| `fetch_agent` | `collection/nodes.py` | cheap, tool calling | The plan and tool summaries (counts, not Posting text) | Tool calls to jobs APIs | `_bound`, `MAX_FETCHES`, `_cap`, arg errors as `ToolMessage` |
| `relevance` | `collection/nodes.py` | Jev `RELEVANT_NOUL` per Posting, `jev_fallback` | **Posting title and description from third-party APIs** | Relevant or not | Jev cuts, a Caveat on degraded verdicts |
| `broaden` | `collection/nodes.py` | strong, structured `SearchPlan` | The plan and fetch totals | A wider Search Plan | Schema |
| `batch_extract` | `analysis/nodes.py` | cheap, structured `BatchFacts` | **Posting descriptions, many per batch** | Skills, seniority, years, employer type | Schema, `_grounded`, `ref` range check |
| `normalise_skills` | `analysis/nodes.py` | cheap, structured `SkillGroups` | Skill names that came from Posting text | Skill aliases | Schema, alias only names shown |
| `write_brief` | `brief/nodes.py` | strong, structured | The Hiring Request, Caveats and Stats (never Posting text) | Insights and Recommendations | Schema, Insight cap, Jev critic |
| `critic` | `brief/nodes.py` | Jev `CRITIC_NOUL` per Insight | The claim and its cited Stats | Supported or not | Jev cuts |
| `revise` | `brief/nodes.py` | strong, structured | Flagged Insights, Caveats and Stats | Revised Insights | Schema, the critic runs again |
| `jev_fallback` | `kernel/jev.py` | cheap, structured verdicts | Whatever Jev was asked about | Verdicts | Schema |

## Nodes this map adds (not built yet)

- **Resume parse**: one cheap structured call on the resume text, with contact details redacted first ([Research: reading resume files](../issues/08-research-reading-resume-files.md)). The resume is untrusted text from the user.
- **Resume matching**: scoring and explaining Matches, shaped by [Matching Postings to a Resume](../issues/18-matching-postings-to-a-resume.md). It reads Posting text and resume facts side by side.
- **Profile learning**: maybe an LLM summary of earlier Runs, depending on [What a User Profile holds](../issues/16-what-a-user-profile-holds.md). If the profile is written by an LLM and read by later Runs, injected text could persist across Runs.

## Where injected text can reach a model

1. The user's own request, answers and plan feedback reach `intake`, `question`, `plan` and `clarity_check`. The user is signed in, so this mostly risks misuse (off-topic or abusive requests) more than an attack on someone else.
2. **Third-party Posting text reaches `relevance` and `batch_extract`.** This is indirect prompt injection from data nobody vetted. The outputs are narrow (a verdict, or grounded facts), which limits the damage, but a verdict can still be flipped.
3. Resume text (new) reaches resume parse and matching.
4. A profile written by an LLM (new, maybe) would carry text from one Run into later ones.
