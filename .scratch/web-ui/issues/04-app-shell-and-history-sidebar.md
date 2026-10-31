# App shell and history sidebar

Type: prototype
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

How does the app look and navigate, so that earlier Runs sit in a sidebar the way Claude and ChatGPT list chats?

- The page frame: sidebar, a main column for the Run (request, live stream, Pauses, Brief), and where the trace graph sits in relation to it (side panel, top strip or collapsible drawer).
- A sidebar row: the title (`RunRecord.summary`, first 80 characters), a status badge for `running | paused | done | aborted | failed`, a relative time, and the grouping (Today, Yesterday, Earlier). Which rows are attention-worthy (`paused`, `failed`), and how a `running` row shows itself live.
- A "New Run" entry and the composer: request box, focus chips for the `Dimension` values plus the `salary` alias, and the empty state.
- Routing: `/` for a new Run and `/runs/:id` for an opened one, so a Run is a link; what opening a finished, paused, failed or running Run shows first.
- How the sidebar learns of changes (poll `list_runs`, or ride the event stream), given the Controller offers no global feed.

Raise fidelity cheaply: a static React/HTML mock with fake data covering each status, reviewed in the browser by the agent. The resolution records the layout, the sidebar row design and the routes, and links the mock.

## Answer

Decided by the agent (the user delegated every decision on 2026-10-31) after reviewing three structurally different frames on one page: [the prototype](../prototype/shell/index.html), switched with `?variant=A|B|C` or the arrow keys. It is throwaway and holds fake data for every status.

**Winner: frame A's skeleton, with C's attention grouping and B's progress bar.**
- A (fixed sidebar, centred column, trace panel at the right) is the closest to the Claude and ChatGPT idiom the user asked for, and gives the Run the full height.
- B hides history behind a button, which is not a sidebar. Kept from it: a thin full-width progress bar and the compact stage strip, but only as the narrow-screen layout.
- C's "Needs you" group is the best idea in the set: a user with five Runs open needs to see which ones are waiting on them. Its flat History list lost the date groups, so those stay from A.

**Layout.**
- Left: sidebar, 272 px. Centre: one column, max 740 px, holding the request bubble, the live stream or the Pause card, then the Brief. Right: the trace panel, 250 px, shown on any opened Run and absent on a new one.
- Under about 900 px wide, the sidebar becomes a slide-over opened from a header button (with a count of Runs needing the user), and the trace panel collapses to a one-line stage strip under the header, with the thin progress bar below it. This settles most of the "responsive depth" fog.

**Sidebar.**
- Top: product name, then a "New Run" button.
- A **Needs you** group is pinned above the date groups, shown only when non-empty: every `paused` and `failed` Run, newest first. These rows are bold. They appear only here, not again in their date group.
- Below it, `running` and finished Runs under Today, Yesterday, Previous 7 days and Earlier, by calendar day of `updated_at` in the browser's timezone, newest first.
- A row is the title (`RunRecord.summary`, one line, ellipsised by CSS), then a status badge and a relative time. No rename, delete or search (out of scope).
- Badge words: `running` "Running" (blue, pulsing dot, the one live signal), `paused` "Needs you" (amber), `failed` "Stopped" (red), `done` "Done" (green), `aborted` "Aborted" (grey). Each badge pairs its colour with a word, so colour is never alone.
- The selected row gets a white background and a hairline border.

**Composer (the New Run page).** A centred heading, one textarea, the five `Dimension` values as toggle chips (Demand, Compensation, Skills, Competition, Titles & seniority), and a Start button. The CLI's `salary` alias is not offered: the Compensation chip is the same Dimension. Enter submits and Shift-Enter adds a line. A blank request is not submittable.

**Routes.** `/` is the composer, `/runs/:id` an opened Run, so every Run is a link. Start navigates to `/runs/:id` once the API returns the thread ID. An unknown ID shows "Run not found" with a link to `/`. What an opened Run shows first, by status:
- `running`: the request, then the live stream attached from the buffer (needs re-attach, decided in [Web API and hosting](03-web-api-and-hosting.md)).
- `paused`: the request and the Pause card.
- `failed`: the request and a "Stopped at <step>" banner with Resume.
- `aborted`: the request and the reason, no Brief.
- `done`: the request, then the Brief.

**How the sidebar learns of changes.** It polls `GET list Runs`: every 3 s while any row is `running` and every 15 s otherwise, plus a refetch on window focus and right after the user starts, resumes, cancels or answers. Polling needs no Controller change and the list is small (one SQLite read, no lock). The open Run's own state still comes from its event stream, and a stream's terminal event triggers one immediate refetch. A global feed is not built.

**Not settled here** (left to the named tickets): the stream and Pause card content ([Live Run view](06-live-run-view.md), [Pause forms](07-pause-forms.md)), the Brief ([Brief view](08-brief-view.md)), and the trace panel's real contents, which are a placeholder of four stage rows in the prototype ([Trace graph](05-trace-graph.md)). Dark mode stays in the fog.
