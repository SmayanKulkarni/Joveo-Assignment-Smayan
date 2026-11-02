# Research: guard models and PII filters

Type: research
Status: open
Assignee: none
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
