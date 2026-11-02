# 10: Upload and correct a Resume

**What to build:** On a Customer's Resume tab, a CSM drops a PDF or DOCX or pastes text, sees the parsed facts, and corrects them. A new upload replaces the old Resume. [Research: reading resume files](../../resume-accounts-sources/issues/08-research-reading-resume-files.md), items 7 and 8 of [What a Resume is for](../../resume-accounts-sources/issues/17-what-a-resume-is-for.md) and [Guardrails for the resume and profile nodes](../../resume-accounts-sources/final-decisions.md#guardrails-for-the-resume-and-profile-nodes) are the spec. Where they differ, Final decisions wins: employer, languages and education are not extracted, and no `data_collection` or `zdr` routing is added.

**Blocked by:** 08: Customers

**Status:** done

- [x] A `resumes` table holds `customer_id` as key, `text`, `facts` and `uploaded_at`; no original file is kept and nothing touches disk
- [x] The upload is a raw body capped at 2 MB and sniffed by magic bytes: pypdf layout mode for PDF, the standard library for DOCX
- [x] Refusals are 404, 413, 415, 422 for scanned or unreadable files, and 502 when parsing fails, each with a message saying what to do
- [x] Contact details are redacted by the three regexes before one cheap structured call, which runs outside the graph with tracing and caching off
- [x] The schema holds only role titles and dates, up to 30 skills, seniority and locations, with no free-text field
- [x] Every string is grounded with `fold` and `mentions`, the skill length rule applies, and total years are computed in code
- [x] `GET`, `PATCH` and `DELETE` on the Resume work; additions show "added by CSM"; a new upload warns that edits will be lost
- [x] Deleting a Customer now also removes their Resume
- [x] Red-team fixtures pass, all fictional: white-text injection, stated sensitive traits, and invented skills
- [x] One live check of field quality on a fictional Resume, since the research couldn't run one
