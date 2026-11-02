# 05: Test the Vercel rewrite on a preview deployment

**What to build:** Facts on whether `/api` works through a Vercel rewrite, so sign-in is built on the right cookie design. This one needs a person: the agent drives what it can, and the user does what needs their Vercel and Render access. [Test SSE and sign-in through the Vercel rewrite](../../resume-accounts-sources/issues/29-test-sse-and-sign-in-through-the-vercel-rewrite.md) is the spec.

**Blocked by:** None (can start immediately)

**Status:** needs-human

## Next

Set up, waiting on the user's console run. The probe (`clients/probe.py`, mounted when `PROBE=1`) is live on `https://joveo-assignment-smayan.onrender.com`, and `web/vercel.json` rewrites `/api` to it. Preview: `https://talent-scout-agwxgwrz3-smayan-kulkarnis-projects.vercel.app/`, behind Vercel Authentication, so only a signed-in browser reaches it.

1. On the preview, with `VITE_API_URL` empty for Preview, run the console script that fetches `/api/probe/echo`, `/redirect`, `POST /write` and times `/stream` as an EventSource.
2. Let Render idle about 15 minutes, then hit `/api/probe/echo` again and note what the proxy returns during spin-up.
3. Paste the results back. Then record them, name the design for ticket 06, and delete `probe.py` and its mount in `web.py`.

- [ ] The rewrite is added before the SPA catch-all, with `x-vercel-enable-rewrite-caching: 0` on `/api/:path*`
- [ ] Timed: does an SSE stream arrive event by event, or buffered?
- [ ] Recorded: which `Host` reaches Render, whether `TrustedHostMiddleware` accepts it, and whether `Origin` passes for `write_guard`
- [ ] Recorded: whether `Set-Cookie` and a `__Host-` cookie pass unchanged, including through a redirect, using a throwaway route
- [ ] Recorded: what the proxy returns during Render's spin-up, and whether the SPA copes
- [ ] The result names the design for ticket 06: the rewrite, or the `Partitioned` cookie fallback
- [ ] The throwaway route is removed
