# 05: Read the Market Brief

**What to build:** when a Run finishes, the Market Brief appears on the page for a customer success manager to read, check against its Evidence, download and print. A Run with no Brief says why. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §9, §4 (downloads), §7 (Endings).

**Blocked by:** 03: Answer a Pause and carry on

**Status:** in-progress (not yet checked in print preview or against a real Brief from `runs/`)

Scope limits, each lifted by a later ticket:
- Folding the turns under "How this Run went" needs turns with content, so it lands with 07 if that isn't done yet.

- [x] On `Done`, the client fetches `RunDetail`, retrying up to 5 times at 200 ms while it says `running`
- [x] The sections follow §9's order, rendered from structured data, with no Markdown renderer and no raw HTML
- [x] Confidence Tags, Outlook ratings and Caveats each read correctly without colour
- [x] Run Notes are open, with Caveats first
- [x] The replay banner and Weak Sample notice appear only when they apply, with `brief/markdown.py`'s wording
- [x] `Evidence` expands inline to the cited Stats and the Postings, ten at first, then "Show all"
- [x] Evidence counts use `posting_keys.length`, and an Outlook with empty `stat_ids` shows no Evidence
- [x] Posting links open in a new tab with `rel="noopener noreferrer"`, and a null `url` shows no link
- [x] Missing recommendations and zero Insights show the Markdown's wording
- [x] `brief.json` and `brief.md` download; a Run with no Brief gets 404 `no_brief`, and the page offers no links
- [x] An `aborted` Run shows the request, "This Run ended without a Brief", the reason and a link to `/`
- [x] `@media print` hides the app's chrome and buttons, and needs no script
- [x] Downloads and `no_brief` are covered in `pytest`
- [ ] Checked by hand with `demo_brief`, with one real Brief from `runs/`, and in print preview (`demo_brief` checked; the real Brief and print preview are not)
