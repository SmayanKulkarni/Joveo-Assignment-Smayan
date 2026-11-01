# Research: reading resume files

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

How should the server turn an uploaded resume into clean text and structured facts?

- Formats to accept (PDF, DOCX, maybe plain text) and the smallest set of libraries that reads them well on Windows and on Render's Linux: `pypdf`, `pdfplumber`, `pymupdf` (check its AGPL licence), `python-docx`, `docling`. Compare text quality on two-column and table layouts, and install size. Scanned PDFs would need OCR, so decide whether to support or refuse them.
- Upload handling in FastAPI: `UploadFile` and `python-multipart`, a size cap, content-type sniffing, and not writing the file to disk if that can be avoided.
- Structured extraction with the existing cheap LLM through OpenRouter and Pydantic structured output (`kernel/llm.py`): which fields are worth having (titles, skills as written, years, seniority, locations, languages, education), and how to stop invented skills. The Extraction rule already drops any skill not found in the text, so check whether that check can be reused.
- PII: what a resume sends to OpenRouter and LangSmith. The gateway keeps Postings out of LangSmith traces (`gateway.py`'s `_resolve`), so check whether resumes can be kept out the same way.

Use a throwaway script outside the repo, on a sample resume you write yourself. Never use a real person's resume. Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

Researched 2026-11-02. Long notes, test tables and working code: [research-resume-parsing.md](../assets/research-resume-parsing.md).

### Recommendation

- Accept PDF, DOCX and plain text (pasted or uploaded). Refuse `.doc`, images and scanned PDFs.
- PDF: **pypdf only** (BSD-3, 4 MB, no deps), with `extract_text(extraction_mode="layout")` for the LLM. Ground against layout plus plain text.
- DOCX: **stdlib `zipfile` + `xml.etree`**, about 40 lines, no python-docx. It reads text boxes, which python-docx misses.
- Scanned PDFs: refuse with a 422 when fewer than about 200 non-space characters come out. No OCR.
- Upload: send the file as the **raw request body** and read `request.stream()` with a 2 MB cap, then sniff magic bytes (`%PDF-`, or a zip holding `word/document.xml`). No python-multipart, and nothing touches disk.
- Extraction: one cheap-tier `Tiers.structured` call for roles (title, employer, start, end as written), skills as written (at most 30), seniority (reusing `Seniority`), locations, spoken languages and optionally education. Compute total years **in code** from the grounded dates. Never extract name, email or phone.
- Grounding: reuse `fold` + `mentions`, not `_grounded` itself, on every string field.
- PII: redact emails, phones and URLs before the call, and add `data_collection: "deny"` to the OpenRouter provider prefs. Run parse and extract in the FastAPI handler, outside the graph, under `ls.tracing_context(enabled=False)`. Keep raw text out of State. Build the resume models with `cache=False` so the replay cache never stores the prompt.

### Key findings

- **Text quality** on a fictional two-column resume with a table, drawn once column by column and once row by row across columns: only pypdf's layout mode read both cleanly. pdfplumber interleaved the columns line by line. pypdf plain mode and pymupdf `get_text()` followed stream order, so they interleaved on the row-by-row file. pymupdf4llm moved sections around. pdfplumber's `extract_tables()` gave exact cells, but the LLM doesn't need them. All extractors returned 0 characters on the scanned copy. pypdf "is not OCR software" ([pypdf docs](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)).
- **Install size**, measured: pypdf 4 MB; pdfplumber about 47 MB (pdfminer.six, Pillow, cryptography, pypdfium2); pymupdf 2.0 about 185 MB (it now pulls onnxruntime, numpy and networkx) and is AGPL-3.0 or commercial ([PyMuPDF about](https://pymupdf.readthedocs.io/en/latest/about.html)); python-docx about 12 MB with lxml; docling resolves 122 packages on Linux, torch and 15 CUDA packages among them ([docling install](https://docling-project.github.io/docling/getting_started/installation/)).
- **DOCX**: python-docx dropped a VML text box completely. The stdlib walk found it once the duplicate `mc:Fallback` copy was dropped. ElementTree is safe from external entities, and expat 2.4.1+ blocks billion laughs ([Python xml docs](https://docs.python.org/3.12/library/xml.html)). The test interpreter has expat 2.7.1.
- **Uploads**: `UploadFile` needs python-multipart, which isn't in `uv.lock`, and it spools to disk past a limit ([FastAPI request files](https://fastapi.tiangolo.com/tutorial/request-files/)). Starlette 1.10.0 sets that limit at 1 MB (`spool_max_size`), and its `max_part_size` only caps non-file fields. Tested: a 3 MB upload rolled to disk with no cap. The raw-body reader returned 413 on oversized bodies, chunked ones too, and 415 on unknown bytes.
- **Grounding**: `mentions(fold(s), fold(text))` ran unchanged on resume text. It kept Python, "Apache Airflow", C#, "SQL Server", the job titles, employers and dates, and rejected invented C++, Terraform and the respelling "Postgres". It can't catch hidden keyword stuffing, because pypdf extracts invisible text too.
- **OpenRouter** doesn't store prompts unless Input & Output Logging is switched on ([data collection](https://openrouter.ai/docs/guides/privacy/data-collection)). `data_collection: "deny"` and `zdr: true` restrict which providers see the text ([provider selection](https://openrouter.ai/docs/guides/routing/provider-selection)).
- **LangSmith**: `_resolve` only hides the gateway span. Postings already reach LangSmith through the `batch_extract` LLM run's prompt, so copying `_resolve`'s approach won't protect resumes. Tested with a recording client: `ls.tracing_context(enabled=False)` around the LLM call dropped that run even with the parent's `config` passed, but the enclosing traced runnable still logged the resume as its input ([conditional tracing](https://docs.langchain.com/langsmith/conditional-tracing)).
- **Replay cache**: when `replay_cache` is set, `_LLMCache.update` writes the full prompt to SQLite. LangChain's `cache=False` on the model skips it.

### Not verified

- A live OpenRouter call on the sample resume. Field quality and the invented-skill rate of the cheap model are untested.
- That an endpoint taking strict `json_schema` stays available for the cheap models once `data_collection: "deny"` or `zdr: true` is added.
- Real Word and Canva exports (only generated files were tested), including whether Word always pairs `mc:Choice` with `mc:Fallback` for text boxes.
- Encrypted PDFs. pypdf needs `cryptography` for AES, so the plan is to refuse any PDF that `decrypt("")` can't open.
- Whether `Client(hide_inputs=...)` passed through `tracing_context(client=...)` blanks LangChain runs. My test client bypassed the hiding code, so the result was unusable, and `enabled=False` is simpler anyway.
- What AGPL section 13 obliges ([AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html)). I didn't fetch the text, and it's moot once pymupdf is out.
- Package sizes on Render's Linux image (measured on Windows wheels).
