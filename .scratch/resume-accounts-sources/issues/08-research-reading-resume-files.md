# Research: reading resume files

Type: research
Status: open
Assignee: none
Blocked by: none

## Question

How should the server turn an uploaded resume into clean text and structured facts?

- Formats to accept (PDF, DOCX, maybe plain text) and the smallest set of libraries that reads them well on Windows and on Render's Linux: `pypdf`, `pdfplumber`, `pymupdf` (check its AGPL licence), `python-docx`, `docling`. Compare text quality on two-column and table layouts, and install size. Scanned PDFs would need OCR, so decide whether to support or refuse them.
- Upload handling in FastAPI: `UploadFile` and `python-multipart`, a size cap, content-type sniffing, and not writing the file to disk if that can be avoided.
- Structured extraction with the existing cheap LLM through OpenRouter and Pydantic structured output (`kernel/llm.py`): which fields are worth having (titles, skills as written, years, seniority, locations, languages, education), and how to stop invented skills. The Extraction rule already drops any skill not found in the text, so check whether that check can be reused.
- PII: what a resume sends to OpenRouter and LangSmith. The gateway keeps Postings out of LangSmith traces (`gateway.py`'s `_resolve`), so check whether resumes can be kept out the same way.

Use a throwaway script outside the repo, on a sample resume you write yourself. Never use a real person's resume. Capture findings in this ticket's Answer, with long notes in `../assets/`.
