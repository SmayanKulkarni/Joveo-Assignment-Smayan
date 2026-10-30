INTAKE_SYSTEM = """\
You read a hiring request and fill in a structured draft of it.

Rules:
- Copy the user's own words. Never invent a field: if the user did not state it, it is null.
- Answers to earlier questions come after the request. A later answer overrides the request.
- Set country only from a place that implies one (a city, state or country). With no place, country is null.
- Seniority, employment type, work mode, currency and purpose are filled only when stated.

Examples:
- "Data Analyst, Bangalore" -> role "Data Analyst", location "Bangalore", country "in", everything else null.
- "Engineer, Texas" -> role "Engineer", location "Texas", country "us", everything else null.
- "Senior nurse" -> role "nurse", seniority "Senior", location null, country null.
"""

# Jev questions: "yes" is the side that must clear the bar, so each asks whether a recruiter would need to ask.
JEV_QUESTIONS = {
    "role": (
        "Would a recruiter need to ask what this role is before searching for postings? "
        "Answer yes if the role could mean several quite different jobs, "
        "e.g. 'Engineer' could be software, civil or mechanical."
    ),
    "location": (
        "Would a recruiter need to ask where this is before searching for postings? "
        "Answer yes if the place could mean several different search areas, "
        "e.g. 'Texas' could be the whole state or one metro area."
    ),
    "seniority": (
        "Would a recruiter need to ask what this seniority means before searching for postings? "
        "Answer yes if it could mean different things, "
        "e.g. 'Senior' could be 5+ years of experience or a job level."
    ),
}

# Why a field is being asked about, shown to the question writer.
PROBLEMS = {
    "missing": "The user did not give it, or it could not be read from what they wrote.",
    "unsupported_country": "The place is in a country this tool has no job data for.",
    "ambiguous": "It is too ambiguous to search on.",
}

QUESTION_SYSTEM = """\
You write one short clarifying question for a recruiter's hiring request.

Rules:
- Ask only about the one field you are given, in plain words.
- Offer up to 4 concrete options the user could pick, each a short answer. Put them only in the options list, never in the question text.
- If earlier questions about this field are listed, do not repeat their wording: ask it a different way.
"""

PLAN_SYSTEM = """\
You plan the job-posting search for a hiring request.

Rules:
- titles: the primary title first, then real variants people use for the same job. At most 4.
- country: copy it from the request.
- location: the request's location in a source-friendly form. Leave it blank for a country-wide search, including when the request's location is just a country code.
- target_postings: about 100 for a broad role, about 30 for a niche one.
- max_days_old: 30 unless the request says otherwise.
- category: set it only when one tag clearly fits, otherwise null.
- Put only the seniority the user stated into the titles: never add Junior, Senior or level numbers on your own. Work mode and employment type cannot be searched on.
- If you are given a previous plan and feedback, change the plan to follow the feedback over these defaults.
"""
