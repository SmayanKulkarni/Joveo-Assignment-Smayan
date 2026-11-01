# 06: Find earlier Runs in the sidebar

**What to build:** every Run sits in a chat-style sidebar, with the ones waiting on the user pinned at the top. Clicking one opens it, and the list keeps itself current without a stream of its own. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §5.

**Blocked by:** 02: Start a Run and watch it reach a Pause

**Status:** done

Scope limits, each lifted by a later ticket:
- Opening a Run navigates to it, but what it shows for each status is finished by 08.
- The running dot is static until 11.

- [x] The frame is the 272 px sidebar and the centred column, with New Run returning to `/`
- [x] "Needs you" is pinned, shown only when non-empty, holds every `paused` and `failed` Run in bold, newest first, and they don't repeat below
- [x] Other Runs sit under Today, Yesterday, Previous 7 days and Earlier, by calendar day of `updated_at` in the browser's timezone
- [x] A row is an ellipsised title, a badge and a relative time; each badge has its word, so colour is never alone
- [x] The list polls every 3 s while any row is `running` and every 15 s otherwise, and on window focus
- [x] It also refetches after the user starts, resumes, cancels or answers
- [x] A stream's terminal event triggers one refetch after 300 ms, because the row lags the event
- [x] The sidebar opens no stream
- [x] When the open Run's `status` or `updated_at` changes and the page holds no stream, the page refetches and re-attaches
- [x] Under about 900 px the sidebar is a slide-over from a header button showing how many Runs need the user
- [x] Grouping, including the timezone day boundary, has a Vitest test
- [x] Checked by hand with Demo Runs in every status, and at phone width
