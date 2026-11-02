# 16: The Resume tab

**What to build:** A Customer page gets a Resume tab between Runs and Profile. There a CSM drops a PDF or DOCX, or pastes text, then sees the parsed facts and corrects them. Ticket 10 built the API for this, but nothing in the web app calls it, so today a Resume can only reach a Customer through the API. The Customer page and Upload items of [Resume, profile and sign-in screens](../../resume-accounts-sources/final-decisions.md#resume-profile-and-sign-in-screens) are the spec, and the endpoints in `clients/resumes.py` are the contract.

**Blocked by:** None (can start immediately)

**Status:** needs-human

- [x] `CustomerPage`'s tabs are Runs, Resume and Profile, in that order
- [x] `types.ts` gains `ResumeFacts` (`roles` with `title`, `start` and `end`; `skills` with `name` and `added`; `seniority`; `locations`; `years`), and `ResumeInfo` carries `facts` and `replaced` beside `uploaded_at`
- [x] `client.ts` gains `uploadResume(id, body: Blob | string)` as a raw `PUT`, `correctResume(id, patch)` as `PATCH`, and `deleteResume(id)`, all through `call` so a 401 still signs the CSM out
- [x] With no Resume (`GET` gives 404 `no_resume`), the tab is a drop zone with a file picker and a paste box. Pasted text goes up as the same raw body, because the server sniffs bytes, not `Content-Type`
- [x] While the upload is in flight the zone says "Reading the resume", and it can't be sent twice
- [x] Each refusal shows the server's `message` as-is: 413 `too_big`, 415 `unknown_type`, 422 `unreadable`, 502 `parse_failed` and 503 `no_model`. The UI doesn't rewrite them, because they already say what to do
- [x] The facts show as an editable form: role rows with title, start and end; a skill list you can add to or remove from; seniority; locations; and years shown read-only, because code computes it. Saving sends only the changed fields as `PATCH`
- [x] A skill with `added: true` shows an "added by CSM" tag. The server sets that flag, and the UI never does
- [x] Field limits match the API (titles up to 100 characters, dates up to 30, and the role, skill and location caps from `resume.py`), and a 422 shows next to the form
- [x] "Replace Resume" asks for confirmation first, warning that the CSM's edits will be lost, then goes back to the drop zone. "Delete Resume" also asks for confirmation
- [x] After an upload, a correction or a delete, the Composer's "Using the Resume uploaded on <date>" line updates without a reload
- [x] Tests (Vitest, `fetch` stubbed like `client.test.ts`): the upload sends the raw body, a refusal's message is shown, the patch sends only changed fields, and an added skill is tagged
- [ ] Checked by hand in local mode: upload a fictional PDF, correct a skill, start a Run, and see the Resume line in Run Notes
