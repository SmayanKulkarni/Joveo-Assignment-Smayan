# Pause forms

Type: grilling
Status: open
Assignee: none
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
