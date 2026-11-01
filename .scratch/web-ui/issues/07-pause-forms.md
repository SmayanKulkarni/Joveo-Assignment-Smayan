# Pause forms

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Web API and hosting](03-web-api-and-hosting.md)

## Question

How does each Pause kind render as an inline card in the stream and take an answer?

- `clarify`: each `ClarifyingQuestion` with its options as chips plus a free-text field, and skipping a question.
- `plan_review`: the Search Plan and Assumptions shown readably, with approve / edit / reject (feedback) / abort. How `edit` works in a browser: a structured form over `SearchPlan`'s fields, or the JSON editor the CLI uses with inline validation.
- `low_data_review`: the counts, plans tried and any block reason, with broaden (optional guidance) / continue / abort.
- `InvalidAnswer`: how the errors show against the same card, with no state changed.
- A Pause on reopening a paused Run from the sidebar, and a Pause answered in another tab.
- Reuse of `clients/pauses.py`'s text formatting, or a typed rendering that replaces it for the web.

Resolution is one card design per kind and the answer payload each posts.

## Answer

Decided by the agent (the user delegated every decision on 2026-10-31). The refusal shapes were checked in the spike described in [Web API and hosting](03-web-api-and-hosting.md). Every card posts to `POST /api/runs/{id}/resume` as `{answer: <payload>}`. `PlanReviewAnswer` has no field defaults and forbids extras, so all three of its keys are always sent (**verified:** omitting them is refused).

| Kind | Action | `answer` payload |
|---|---|---|
| `clarify` | Send | `{answers: string[]}`, one per question in order, `""` for a skipped one |
| `plan_review` | Approve | `{action: "approve", plan: null, feedback: null}` |
| | Edit | `{action: "edit", plan: <SearchPlan>, feedback: null}` |
| | Reject | `{action: "reject", plan: null, feedback: "<text>"}` |
| | Abort | `{action: "abort", plan: null, feedback: null}` |
| `low_data_review` | Search wider | `{action: "broaden", guidance: "<trimmed>" or null}` |
| | Continue | `{action: "continue", guidance: null}` |
| | Abort | `{action: "abort", guidance: null}` |

**`clarify`: "A quick question" or "A few quick questions".** Each question has its text, its `options` as real radio inputs styled as chips, and a free-text box. Picking a chip fills the box, and typing clears the chip, so one value is sent. Blank is a skip, which `clarify` already handles by position. The button reads "Send answers", or "Continue without answering" when all are blank.

**`plan_review`: "Check the search plan".** A readable list, not field names: Titles as chips, Where (`location` or "Country-wide", with the country code in capitals), Radius, Posted within N days, Target N Postings, Category (or "Any"). Below it, Assumptions as "seniority: Senior, because …". Actions: Approve (primary), Edit, Ask for a different plan, Abort.

**`edit` is a structured form, not the CLI's JSON editor.** A customer success manager should not be editing JSON, and `SearchPlan` is seven flat fields:
- `titles`: 1 to 4 text rows, with add and remove
- `country` and `category`: selects from `/api/meta`, the same sets the validators check, with `category` also offering "Any"
- `location`: text, blank meaning country-wide
- `radius_km` (0 to 100), `max_days_old` (1 to 60), `target_postings` (20 to 200): number inputs with those limits

The HTML limits only help. The server stays the check. "Use this plan" submits.

**`low_data_review`: "Too few Postings".** "Only 3 relevant Postings found; the target is 20." "Fetched 50, rejected 47 as not the role, over 1 Attempt." Then `blocked` if set, Adzuna calls left if known, and the plans tried in a `<details>`. A guidance textarea, optional, feeds "Search wider". Then "Continue with 3 Postings" and Abort. Guidance is blank-to-null as in `low_data_answer`, in TypeScript.

**Abort is two-step everywhere**, an inline "Abort this Run? Yes / No", because it is the one irreversible answer.

**`InvalidAnswer`.** The card stays, values kept. `errors` with `loc[0] === "plan"` show under the field named by `loc[1]`, anything else at the top of the card. Reject's feedback is also blocked client-side when blank. Buttons disable while posting.

**Other refusals.**
- `run_locked`: retry once after 300 ms, then "This Run is open elsewhere".
- `not_resumable`, or `invalid_answer` saying the Run isn't waiting: "Answered elsewhere", then refetch `RunDetail` and rebuild.
- `balance_too_low` or `upstream`: the message at the top of the card, and the Run stays `paused`, so it can be retried.

**After answering,** the card collapses to a one-line record in the stream ("You approved the plan", "You answered 2 questions"), then the new stream opens. On a reload, the record is the raw message of the `pause` entry in `run_log` ("plan approve").

**Reopening.** A `paused` Run's card renders from `RunDetail.pause`, identical to a live one. **Another tab:** the sidebar poll sees the open Run's `status` or `updated_at` change, and the page refetches and re-attaches. So a stale card lasts at most one poll interval, and anything posted in that gap meets the refusals above. A stale answer can only pass if the Run is at a later Pause of the same kind, which needs a reject loop plus a second tab, and that is accepted.

**`clients/pauses.py` stays, for the CLI alone.** The web renders typed payloads, since text formatted for a terminal has no chips or fields to style. Its "shared by every client" docstring and `event_line`'s mention of Streamlit get corrected when Streamlit goes.
