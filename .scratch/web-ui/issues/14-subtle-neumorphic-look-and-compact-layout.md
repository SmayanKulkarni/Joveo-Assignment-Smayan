# Subtle neumorphic look and compact layout

Type: prototype
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What should the app look like so it stops feeling tall, blocky and unfriendly?

Prototype the Search Plan editor, the clarify card with multi-select chips, and one Brief section in `.scratch/web-ui/prototype/`, then decide from them.

- Tokens in `web/src/styles.css`: surface colour, raised and inset shadows, radii, and how far the neumorphism goes. It stays subtle.
- Text and control contrast. Neumorphism is known to lose edges, so inputs, focus rings and the disabled state must remain clear (WCAG AA).
- The editor's layout: titles as removable chips with an always-available add box, and short fields sharing rows, so it fits one screen at desktop width and stacks on a phone.
- Readable labels for every raw value: "IT Jobs" for `it-jobs`, "PR, Advertising & Marketing Jobs" for `pr-advertising-marketing-jobs`, and country names for `IN`. Where the label table lives, with the wire values unchanged.
- Whether radius, days and target stay number boxes or become something friendlier.
- Print still works. Dark mode stays deferred.

## Answer

Decided by the agent, as the user told it to make every decision on 2026-11-01. Open to change once the user reads it.

[Prototype](../prototype/look/index.html), on real Brief data, with `?depth=flat|subtle|strong`. Chose **subtle**: strong makes cards look like buttons, and flat doesn't change how the app feels.

- **Tokens** in `web/src/styles.css`: `--bg #eef0f3` as the one surface, `--ink #1f2430`, `--muted #535c6b`, `--edge #7d8796`, `--accent #2f5d50`, `--focus #1f5fd0`; `--raised 5px 5px 12px rgba(150,160,178,.38), -5px -5px 12px rgba(255,255,255,.85)`, a smaller `--raised-sm`, and `--inset` for inputs. Radii 14 for cards, 8 for inputs, 99 for chips.
- **Neumorphism stops at the surface.** Controls keep a real 1px `--edge` border, because shadow alone loses the edge. Measured against `--bg`: ink 13.59, muted 5.91, edge 3.18, focus 5.10, white on accent 7.49, warning 6.09 on its own tint. All meet AA. Focus is a solid 2px outline. Disabled is a dashed border and muted text, not `opacity: .4`.
- **Editor.** Titles and Places are chip boxes with an always-open add input (Enter adds, x removes), no limit. Short fields share a 4-column grid, two columns on a phone. At 665 px wide it is 451 px tall, so it fits one screen. No overflow at 375 px.
- **Friendlier fields.** Radius ("Within") and days ("Posted in the last") become selects with presets, 5, 10, 25, 50, 100 km and 7, 14, 30, 60 days, adding the plan's own value when it isn't a preset. Radius is disabled with no place. Target stays a number box, as any value is meaningful.
- **Labels.** One new `web/src/labels.ts` with a 20-row category table with a raw fallback. Country names come from native `Intl.DisplayNames`, so no table. Wire values don't change.
- **Print** drops the shadows, uses white and gives cards a hairline. Dark mode stays deferred.
- **Sidebar and Run header** (the fog): they carry no log text, so they need only the tokens. No ticket.
