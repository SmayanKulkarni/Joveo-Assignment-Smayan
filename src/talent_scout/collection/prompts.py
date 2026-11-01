from langchain_typesafe import Noul, NoulCriteria

FETCH_SYSTEM = """\
You gather job postings for a market study of one role. You search by calling tools, and you cannot see which postings are relevant, so you gather a raw pile that is larger than the target.

Rules:
- Pick the source for each search from the tool descriptions. On a US Run, try both sources for the primary title. Spend the metered source carefully, and drop a source whose results are off-role.
- Search each plan title, primary title first, in every place the plan lists. Pass the place as `location`, exactly as the plan spells it. You may also search a close variant of a title.
- Gather about 1.5 times the target in raw postings, and stop early when a title's total shows it is exhausted.
- Page a title only if its total says it has more matches than you have seen.
- Stop when you have enough, or when a call is refused. Reply without a tool call to stop.
- Do not repeat a search listed as already done.
"""

BROADEN_SYSTEM = """\
You widen a job-posting search that found too few relevant postings. You are given the hiring request, the plan that fell short, what each search found, and some titles that were rejected as not the role.

Rules:
- Pick the moves most likely to help: more title variants, a wider radius, an older max_days_old, dropping the category, or replacing a noisy title.
- Each title is one job title, never a list of titles joined together.
- Use the totals and rejected titles to choose. A title with few matches is exhausted, so a wider search helps more than the same title. A rejected title shows a noisy keyword, so replace it.
- Follow the user's guidance over these defaults when it is given.
- Keep country, locations and target_postings as they are. They are restored by code anyway.
- Stay within the limits of the plan format. Do not drop or change the primary role.
"""

# "Yes" is the side that must clear the bar (Kernel LLD 11), so the criteria describe both sides.
RELEVANT_NOUL = Noul(
    instructions=(
        "Is this job posting really an advertisement for the researched role? "
        "Ignore seniority and location: a junior, senior or unlevelled posting for the same role is still the role."
    ),
    criteria=NoulCriteria(**{
        "true": "The posting advertises the researched role, or a close variant of its title.",
        "false": (
            "A different job that shares a keyword (e.g. 'Data Entry Analyst' for 'Data Analyst'), "
            "or a general talent pool or public notice that is not an advertisement for the role."
        ),
    }),
)
