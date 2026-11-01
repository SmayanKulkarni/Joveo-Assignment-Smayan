# 09: Stop and Resume a Run

**What to build:** a user can stop a running Run, and when one stops for any reason, the page says where and offers Resume, which picks up from that step. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §4 (cancel), §7 (Endings, Stop).

**Blocked by:** 03: Answer a Pause and carry on; 07: See the Run think and search

**Status:** ready-for-agent

- [ ] `POST /api/runs/{id}/cancel` returns `Stopped`, leaves the Run `failed` with `cancelled`, and gives 409 `not_live` with no attached handle
- [ ] The Stop button shows only while the Run is live here, and needs no confirmation
- [ ] `Stopped` with a node shows "Stopped at <Step>. Nothing is lost; Resume retries that step", with the raw reason in a `<details>`
- [ ] A `cancelled` reason reads "You stopped this Run at <Step>"
- [ ] `Stopped` with `node: null` offers no Resume, only a link to `/`
- [ ] Resume posts `answer: null`, and its new stream's base is the state on screen
- [ ] Resume's refusals show on the banner, as they do on a Pause card
- [ ] A "fail" Demo Run stops at Tidy skill names and reaches `done` after Resume, rerunning only that step
- [ ] `pytest` covers cancel then resume, `not_live`, and shutdown leaving a live Run `failed` and resumable
- [ ] Checked by hand: Stop mid-search and resume, and a "fail" Demo Run
