# Research: guard models and PII filters

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Which open-weight guard models and PII filters could check text going into and out of this system's LLM nodes, and where would they run?

[LLM nodes](../assets/llm-nodes.md) lists the calls and the text each one reads. The riskiest is third-party Posting text reaching `relevance` and `batch_extract`, and soon resume text.

- **Prompt-injection and jailbreak classifiers**: Llama Prompt Guard 2 (22M and 86M), ProtectAI's `deberta-v3-base-prompt-injection-v2`, and any newer open-weight ones in 2026. Their accuracy on indirect injection (instructions hidden in a document, not typed by the user), their context limit (Posting descriptions run to thousands of characters), and false positives on ordinary job ads.
- **Content-safety models**: Llama Guard (latest version), ShieldGemma, IBM Granite Guardian, and others. Which are on OpenRouter, at what price and latency, and which only run locally.
- **Running them**: on Render's free web service (512 MB RAM, shared CPU) with ONNX or CPU `torch`, or through OpenRouter or another hosted endpoint for the open weights. Give memory and per-call latency for each.
- **Jev as a guard**: the system already has `langchain-typesafe` (`kernel/jev.py`) with `Noul` yes or no questions and thresholds. Could a Noul such as "does this text try to instruct an AI" screen Postings at no new dependency? Check its size limit and price per request, and how well a yes or no classifier spots injection compared with the models above.
- **PII**: Microsoft Presidio (analyzer and anonymizer) against simple regexes for emails, phones and URLs. Its spaCy model size, memory on Render, and quality on resume text. [Research: reading resume files](08-research-reading-resume-files.md) already decided to redact contact details, so check which tool should do it.
- **Cost on a real Run**: about 600 Postings and about 15 LLM calls. What screening every Posting would add in money, latency and Jev or OpenRouter quota.

Hosted vendor guardrails (AWS Bedrock Guardrails, Azure AI Content Safety, Lakera, and the like) are out of scope. Open-weight models served by OpenRouter are fine.

Write long notes in `../assets/research-guard-models.md` and a short answer here.

## Answer

Researched 2026-11-02. Long notes, test sets and all numbers: [research-guard-models.md](../assets/research-guard-models.md). These are facts. Which node gets which guard is [ticket 24](24-guardrails-for-the-existing-llm-nodes.md).

Tested on 117 real Posting descriptions from the repo's fixtures, plus 40 with an injected sentence, 30 with softer "adaptive" ones and 5 benign adverts that quote attack phrases. Local models ran on one desktop CPU thread in a throwaway venv outside the repo. Hosted ones ran live through OpenRouter (about $0.05 in all).

| Candidate | Where it runs | Memory | Latency | Price | Context |
|---|---|---|---|---|---|
| Prompt Guard 2 22M (int8 ONNX) | local CPU | +336 MB | 48 ms short, 286 ms per 512 tokens | free | 512 tokens |
| Prompt Guard 2 86M (int8 ONNX) | local CPU, HF Inference | +727 MB | 145 ms short, 783 ms per 512 | free locally | 512 tokens |
| ProtectAI v2 (archived) | local CPU, HF Inference | +1,094 MB | 183 ms short, 921 ms per 512 | free locally | 512 tokens |
| Jev 1.14 `Noul` | OpenRouter | none | 0.44 s median | $0.042 per M input, output free | 64k per request, 32k per question; repo cuts state at 30,000 bytes |
| gpt-oss-safeguard-20b | OpenRouter (Groq) | none | 0.25 s median | $0.075 in, $0.30 out per M | 131k |
| Llama Guard 4 12B | OpenRouter (DeepInfra) | none | 0.48 s median | $0.18 per M | 164k |
| Nemotron 3.5 Content Safety | OpenRouter (DeepInfra, plus `:free`) | none | 1.05 s median | $0.20 per M; `:free` capped at 50 or 1,000 a day | 131k |
| Llama Guard 3, ShieldGemma, Granite Guardian 4.1, Qwen3Guard | local GPU or other hosts, not OpenRouter | 1.5 GB and up | not measured | n/a | n/a |
| Presidio, pattern recognizers only | in process | +91 MB (spaCy is imported anyway) | 2 ms per resume | free | n/a |
| Presidio + `en_core_web_lg` (default) | in process | +748 MB | 25 ms per resume | free | n/a |
| Three regexes | in process | 0 | 0.1 ms | free | n/a |

- **Injection inside a job advert gets diluted.** ProtectAI caught 4 of 5 injected sentences on their own, but 1 of 40 once they sat inside a Posting. Scanning sentence by sentence brought it to 27 of 40, with 4 of 117 real Postings flagged. Prompt Guard 2 catches only "ignore previous instructions" phrasing: 8 to 15 of 40 for 22M and 3 to 8 of 40 for 86M, depending on chunking, and 0 of 30 adaptive cases. On the 5 adverts that quote attack phrases (a Prompt Engineer, an ML Safety role), all three local models flagged 3 of 5 when scanning sentence by sentence. Published work agrees: Prompt Guard 2 caught 37% of indirect injections and ProtectAI 8% ([arXiv 2602.14161](https://arxiv.org/html/2602.14161)).
- **Content-safety models don't look for injection.** Llama Guard 4 flagged 2 of 40 injected Postings (as "Specialized Advice") and Nemotron 1 of 40. Neither flagged a real Posting. gpt-oss-safeguard with a written injection policy caught 37 of 40 and flagged 0 benign.
- **Jev as a guard**: a `Noul` asking whether the Posting addresses an AI scored all 40 injected Postings 0.94 to 1.00, and every one of the 117 real Postings and 5 hard benign adverts at 0.34 or below. Jev bills the state once per request, so a guard question added to the existing `relevance` request costs only its own tokens and no extra call. TypeSafe warns that state "can move the answer" when written to steer the model. Separately, three attacks in the middle of 9 off-role USAJOBS Postings flipped the real `RELEVANT_NOUL` once in 27 tries (0.49 to 0.53).
- **Render free (512 MB, 0.1 CPU)**: the app already uses about 117 MB. Only Prompt Guard 2 22M int8 comes near fitting (about 453 MB in all, measured on Windows, not Linux). At 0.1 CPU, screening 600 Postings with it would take something like 15 to 20 minutes, an estimate I did not measure.
- **PII**: the emails, phones and URLs that ticket 08 redacts are all pattern recognizers in Presidio, and the spaCy model isn't needed for them. Presidio's NER on a resume tagged Kafka as a person and Python as a place or organisation. Both Presidio's URL recognizer and a plain regex treated `ASP.NET` and `socket.io` as URLs. Three regexes found all 9 contact details in 0.1 ms, once a 9 to 15 digit rule kept year ranges from being taken as phones. Presidio has moved from Microsoft to the Data Privacy Stack organisation.
- **Cost of screening ~600 Postings per Run**, at about 600 tokens each: about $0.003 as an extra `Noul` in `relevance` (no new requests), $0.015 as a separate Jev request, $0.04 with gpt-oss-safeguard, $0.07 with Llama Guard 4, $0.12 with paid Nemotron, and $0 locally (but see Render). Each hosted option except the extra `Noul` adds 600 requests per Run. Nemotron's `:free` cap (50 a day, or 1,000 with 10 or more credits bought) covers one Run a day at most. Screening the ~15 LLM calls is under $0.002 with any hosted model.
- **Not verified**: anything on Render itself, Meta's gated original weights (I used a third-party ONNX conversion), Jev token usage (the classifier drops it), Nemotron's custom-policy mode, and any attacker who adapts to the guard.
