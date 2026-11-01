# Many places and titles in a Search Plan

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Research: searching many titles and places on Adzuna](12-research-adzuna-many-titles-and-places.md)

## Question

How does one Run search several places and as many titles as the user wants, without breaking the Adzuna quota?

"Mumbai" can mean Mumbai, Navi Mumbai and Thane, but `HiringRequest.location` and `SearchPlan.location` each hold one string, and `Fetch` carries one place. Titles are capped at 4 in three places: `SearchPlan.titles`, the plan prompt and `MAX_TITLES` in `PlanEditor.tsx`. `MAX_FETCHES` (6 per Attempt) is the real ceiling, so removing the visible cap alone would let a user add titles that never get searched.

- The Search Plan's shape: `locations: list[str]` or something else, and what `HiringRequest.location` becomes.
- How a multi-select Clarifying Question answer travels: `ClarifyForm` sends one string per question, and only some questions should allow several answers. Which ones, and who says so?
- How the fetch budget spreads across titles × places, and what the user is told if some combinations go unsearched. Titles must not have a hard limit in the UI.
- Broaden's limits. The screenshot Run asked for Mumbai, then broaden blanked the location, so the Brief headed "Mumbai" rests on a country-wide search. It also produced the joined title "Brand Marketing Intern Content Marketing Intern". May broaden ever leave places the user chose?
- Compatibility: earlier Runs in the sidebar and their checkpoints hold the single `location`, and the replay cache keys on it. They must still open.
- What changes in the CLI Pause text and `brief/markdown.py`.

## Answer

Decided by the agent, as the user told it to make every decision on 2026-11-01. Open to change once the user reads it.

Live check run for this ticket, 5 Adzuna calls on `in` with `title_only=marketing`: Mumbai 5 km 110, Mumbai 50 km 122, Thane 10 km 6, Navi Mumbai 10 km 9, `location0=India&location1=Maharashtra` 204. The 50 km page returned ads whose `area` is Navi Mumbai and Thane, and 110 + 6 + 9 less the 3 Mumbai-area ads the small searches also returned is 122. So one wide search covers that metro. [Details](assets/research-adzuna-many-titles-and-places.md#live-check-2026-11-01).

- **Shape.** `SearchPlan.locations: list[str]` replaces `location`, with `[]` meaning country-wide and one shared `radius_km`. `HiringRequest.location` stays one string, the user's words ("Mumbai, Navi Mumbai, Thane"), since it only heads the Brief and feeds prompts. `Fetch.location` stays one place, so L1, L2 and Gateway replay keys don't change.
- **Same metro means one search.** `PLAN_SYSTEM` merges places in one metro area into one centre with a wider radius (Mumbai 50 km for those three). Separate cities stay separate. There is no gazetteer, so this is the model's judgement, visible and editable at plan review.
- **Multi-select.** Only `about == location` questions allow several answers, decided by the UI from `about`. Chips become checkboxes, and the answer is sent joined with ", ", so `ClarifyAnswer.answers: list[str]` doesn't change and intake copies it as usual. `QUESTION_SYSTEM` is told to offer the areas a place could include, and never an "Other" option, because the text box is always there. That also settles the fog on how other ambiguous places get their options.
- **Titles have no limit.** `max_length` goes from `SearchPlan.titles` and `MAX_TITLES` from the editor. `PLAN_SYSTEM` still suggests about 4, because each one costs a call.
- **Budget.** The per-Attempt cap becomes `max(MAX_FETCHES, titles x places)`, so a title the user adds does get searched. The real ceiling stays the daily guard in `gateway/store.py`, and running out already reaches `low_data_review` through `fetch_blocked`. `_fetch_input` lists the combinations in order, the primary title in every place first, so what a short budget drops is the least important.
- **The search tools take `location`.** A new model argument, blank meaning the first place. A value not in the plan is refused with an error `ToolMessage`, so the model still can't leave the approved plan.
- **What the user is told.** Plan review shows "3 titles x 2 places = 6 searches. 5 Adzuna calls left today." It is information, not a refusal. `PlanReviewPayload` gains `calls_left: int | None = None`, and the count is arithmetic in the client. A chosen place with no search at all raises the Caveat "Places not searched: Thane".
- **Broaden may never drop places.** Code pins `locations`, as it pins `country` and `target_postings`, and "a country-wide search" leaves `BROADEN_SYSTEM`. Only the user can go wider: `low_data_review` gets a "Search the whole country" checkbox, sent as `LowDataAnswer.whole_country: bool = False`. Broaden may still widen the radius up to the 100 km limit.
- **Joined titles.** "Brand Marketing Intern Content Marketing Intern" came from the model fitting five titles into a cap of four. The cap is gone, and `BROADEN_SYSTEM` and `PLAN_SYSTEM` say each title is one job title. `PLAN_SYSTEM` also says a bare place name, as "Mumbai, India" never matches a region in `store.py`'s `_fits`.
- **Compatibility.** A `model_validator(mode="before")` on `SearchPlan` turns an old `location` into `locations`, so old checkpoints and Briefs open. It isn't in the schema the LLM sees. New fields all have defaults. `Fetch` keys survive, but LLM replay entries for prompts holding the plan will miss, so sample Runs are recorded after this ships.
- **CLI and Markdown.** `render_plan` prints the list, or "country-wide" when empty. `_plan` in `brief/markdown.py` does the same. `match_totals` is keyed per title and place, as totals for one title would overwrite each other. USAJOBS makes one call per place like Adzuna, because several-location calls are unverified and it isn't metered.
