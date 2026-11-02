# 18: The Demo Run shows Arbeitnow and remote Postings

**What to build:** The Demo Run (`runtime/demo.py`) searches Arbeitnow after Adzuna and USAJOBS, and its Sample holds one remote Posting. The web tests then exercise the event shapes that tickets 01, 02 and 14 added. `web/src/test/demo-run.json` is generated from the Demo Run by `tests/test_web_contract.py` (`UPDATE_DEMO_RUN=1`), so the change goes in `demo.py` and the fixture is regenerated, never edited by hand.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `fetch_agent` in the Demo Run gets a third turn that calls `search_arbeitnow`, with `api_called` source `arbeitnow` and `calls_left` `None`
- [x] One demo Posting comes from Arbeitnow with `remote=True`, region `("Remote",)` and no salary, so the remote label, the "Includes remote" Caveat and a Posting with no pay all appear
- [x] The attribution line names all three sources, in place of today's `attribution=None`
- [x] The plan review Pause payload carries `from_profile` (empty is fine), so the fixture matches `types.ts`
- [x] The Demo Run keeps scoring no Matches and keeps its "Demo Runs score no Matches" note. It has no Customer or Resume, and that's on purpose
- [x] `demo-run.json` is regenerated, `test_web_contract.py` passes, and `feed.test.ts`, `trace.test.ts` and `steps.test.ts` pass against it. Any count those tests assert is updated to match the new events
