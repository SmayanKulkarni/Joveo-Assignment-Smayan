# What the user sees and what the record keeps

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Which Run details reach the user on screen, and which stay only in the record?

The UI currently prints log text meant for debugging: raw plan diffs under "Filter postings", route names such as "(route: analyse)", "Some live text wasn't kept", and every Caveat with its internals.

- One rule for what is user-facing, applied to `turn.notes` in the live view and to the trace panel. Does the server send friendly text, or does the UI map or drop log lines?
- Removing the "Some live text wasn't kept" line (`Stream.tsx`, the `gap` flag in `reducer.ts`). It is sticky, so it stays at the foot of the stream after the turn it was about, and its check counts drafting nodes whose tokens are never shown.
- Which Caveats matter to a reader, with a limit of one or two plain lines, and their wording. For example, "Broadened 2 time(s): titles: [...]" becomes "We widened the search to find enough postings", and a dropped location must be said plainly. A Weak Sample and a search wider than the place asked for look like the ones that change how far to trust the Brief.
- What is left of Run Notes on screen. Plans, source counts and internal Caveats stay complete in `brief.json` and `brief.md`, and the attribution line must stay visible.

## Answer

Decided by the agent, as the user told it to make every decision on 2026-11-01. Open to change once the user reads it.

**The rule: a line reaches the screen only if the reader can act on it or it changes how far to trust the Brief.** Everything else stays in the record.

- **The server writes the friendly text.** A new `LogKind.result` marks lines meant for readers, and `NodeDone` gains `results: list[str] = []`. The live view and trace panel show only these, and never `notes`. Mapping debug strings in the UI would break whenever a message changed. Existing `run_log` messages stay as they are for `scout show`.
- **The lines:** `collect` "Found 80 postings" (with ", 12 duplicates" if any), `relevance` "51 are the role", `broaden` "Widened the search". Other Steps show their label and check alone. `fromLog` filters on `kind`. An old Run shows the same labels without these lines.
- **Tool cards.** The model still gets "Refused: ...", while the emitted summary becomes "Skipped: search limit reached". Bad arguments and unknown tools read "Didn't run". Pills say "Adzuna" rather than `adzuna`.
- **"Some live text wasn't kept" goes:** the line in `Stream.tsx`, the `gap` flag and its check in `reducer.ts`. It told the reader nothing they could act on.
- **At most two plain Caveats on screen, from a new pure `reader_notes(brief)`,** first matches in this order:
  1. Places widened: "We searched the whole country, not only Mumbai."
  2. A "Places not searched" Caveat: "We couldn't search Thane."
  3. Weak Sample: "Only 12 postings against the 20 we aimed for, so treat this as a rough guide."
  4. Any broaden: "We widened the search to find enough postings."
  5. "Old data" Caveat: "Most of these postings are over 30 days old."
  6. "Mostly federal" Caveat: "Most of these postings are US federal jobs."
  7. "One source failed" Caveat: "One job source didn't answer, so this rests on the other."
  Skills from snippets, assumed pay periods and critic or Jev degradation stay in the record, and the charts say what they rest on.
- **Computed on read, not stored.** `reader_notes` goes on `RunDetail`, so earlier Runs get them and `brief.json` keeps its bytes.
- **Run Notes on screen** move into a closed "How this was researched", unchanged and complete, including every Caveat. This reverses "Run Notes stay open" from [Brief view](08-brief-view.md), because the reader notes now carry what affects trust. The attribution line moves out of the fold to the foot of the Brief, always visible. `brief.json` and `brief.md` don't change.
