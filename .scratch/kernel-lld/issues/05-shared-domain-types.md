# Shared domain types

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 02

## Question

What are the fields, types and invariants of the Pydantic domain types that cross component boundaries?

Hiring Request, Clarifying Question (+ answer), Assumption, Search Plan, Posting, per-Posting extraction, Insight with Evidence and Confidence Tag, Hiring Outlook.

Particular pressure points:
- **Posting identity**: `source` + `source_id` as the key; what the dedupe key looks like.
- **Posting salary**: carried raw (amount range, currency, Adzuna's unstated period, USAJOBS `RateIntervalCode`, `salary_is_predicted`, federal pay-table flag) so the Analysis LLD can normalise later without a schema change.
- **Domain and region**: Adzuna category / `location.area`, USAJOBS job family mapping hook (needed later by Gateway L2).
- **Expiry fields**: close date (hard) vs created date (soft).
- **Description**: Adzuna's 500-char snippet vs USAJOBS full text; does the type say which?
- Which types are also LLM structured-output schemas (Search Plan, extraction, brief), and what that implies for field descriptions and optionality.

Inputs: [Adzuna](../../talent-scout-hld/issues/13-research-adzuna-api-facts.md) and [USAJOBS](../../talent-scout-hld/issues/14-research-usajobs-api-facts.md) research, `GLOSSARY.md`.

## Answer (2026-10-30)

Grilled in three rounds. Everything below goes in `talent_scout/kernel/types.py`.

**What the Kernel holds.** A type lives here only if one component writes it and another reads it (the Gateway counts as a component):
- **Kernel**: Posting (with Salary, Source and PayPeriod), Evidence, HiringRequest, Clarifying Question, Assumption, Search Plan, and Market stats (Stat, Dimension).
- **Analysis LLD**: the per-Posting extraction and the Stat catalogue.
- **Brief LLD**: Insight, Confidence Tag, Client Recommendation, Hiring Outlook and Market Brief.

**Conventions**:
- Every model uses `ConfigDict(frozen=True, extra="forbid")`.
- Enums are `StrEnum`, money is `float`, and dates are `date`.

**LLM-schema policy**:
- A type is used directly as a `with_structured_output` schema only when the model writes every field. When code adds fields, the stage defines a narrower draft schema.
- Every field of an LLM-facing type has a `Field(description=...)` giving its meaning and units, never instructions.
- Optional fields are `T | None` with no default, because strict `json_schema` makes every property required anyway.
- Validator errors are what the LLM tier factory feeds back on retry.

**Raw JSON to Posting.** The Gateway's mapper converts raw responses into Postings. L1 caches the raw response, so replay stays faithful. Tools and Collection see only `list[Posting]`. The mapper handles every source quirk:
- derives the currency from the Adzuna country
- maps `RateIntervalCode` to a period
- maps `location.area` to a region
- maps the USAJOBS family to a Domain
- accepts `salary_is_predicted` as either "0"/"1" or an int
- caps descriptions at `MAX_DESCRIPTION_CHARS = 4000`
- swaps a reversed salary range and drops a salary that has neither bound
- skips any Posting that still fails validation, and counts the skips

```python
class Source(StrEnum): adzuna, usajobs
class PayPeriod(StrEnum): annual, monthly, biweekly, weekly, daily, hourly, unknown

class Salary(BaseModel):
    min: float | None          # at least one of min/max; min <= max
    max: float | None
    currency: str              # ISO 4217, ^[A-Z]{3}$
    period: PayPeriod          # Adzuna always `unknown`
    predicted: bool            # Adzuna salary_is_predicted; False for USAJOBS

class Posting(BaseModel):
    source: Source
    source_id: str
    title: str
    company: str | None
    location: str              # display string
    region: tuple[str, ...]    # Adzuna location.area; USAJOBS (country, state, city) of first location
    domain: str | None         # Adzuna category tag; USAJOBS family mapped onto it, None until mapped
    posted_at: date            # soft expiry, trend
    closes_at: date | None     # USAJOBS only, hard expiry
    description: str           # Adzuna <=500-char snippet; USAJOBS capped full text
    url: str
    salary: Salary | None      # None = pay not disclosed
    # computed: key = f"{source}:{source_id}"
```

Notes on Posting:
- **Identity and dedupe.** `key` is a plain `str`. Postings with the same key merge as a no-op. Collapsing the same job across locations or sources by fingerprint is a Collection rule, not a field.
- **USAJOBS salary.** If a posting lists several `PositionRemuneration` entries, the mapper takes the first.
- **No federal-pay flag.** It is equivalent to `source == usajobs`.
- **Fields left out.** There is no snippet flag, no contract type or time, and no remote flag, because no stage needs them.

```python
class WorkMode(StrEnum): onsite, hybrid, remote
class RequestField(StrEnum): role, location, seniority, employment_type, work_mode, currency, purpose

class HiringRequest(BaseModel):          # intake's LLM schema; role/location non-blank
    role: str
    location: str
    seniority: str | None                # free text as given
    employment_type: str | None
    work_mode: WorkMode | None
    currency: str | None                 # ISO 4217 for the brief
    purpose: str | None

class ClarifyingQuestion(BaseModel):     # drafted via a narrower stage schema (answer is code-filled)
    about: RequestField
    text: str
    options: list[str]
    answer: str | None

class Assumption(BaseModel):
    about: RequestField
    value: str
    reason: str

class SearchPlan(BaseModel):             # plan's (and broaden's) LLM schema; replaced whole, never patched
    titles: list[str]                    # non-empty, primary first
    country: str                         # ^[a-z]{2}$
    location: str
    radius_km: int                       # >= 0
    max_days_old: int                    # >= 1; also the soft-expiry window
    target_postings: int                 # >= 1; Sufficiency target
    category: str | None
```

Notes on these types:
- **HiringRequest** has no raw text field (the original wording goes in `run_log`) and no `--focus` (that's a Run option, decided in ticket 06).
- **Re-asks** are counted from earlier questions with the same `about`; there is no attempt counter.
- **SearchPlan** has no sources field (the fetch_agent model picks the tools) and no rationale field (the reasoning goes in `run_log`).

```python
class Dimension(StrEnum): demand, compensation, skills, competition, titles_seniority

class Evidence(BaseModel):
    posting_keys: list[str]              # before-validator sorts + dedupes
    # computed: count

class Stat(BaseModel):
    id: str                              # unique within MarketStats, e.g. "comp.median"
    dimension: Dimension
    label: str
    value: float | str
    unit: str | None
    evidence: Evidence

class MarketStats(BaseModel):
    sample_size: int
    stats: list[Stat]
```

Market stats are a flat list, so the Kernel fixes only the shape of a Stat:
- **Analysis owns the Stat catalogue.** Its LLD decides which ids exist, so adding a figure never changes the Kernel.
- **Brief cites Stat ids.** Insights point to Stat `id`s, and code expands those ids into Evidence. The LLM never types Posting keys, so Evidence comes from the Sample by construction.

**Validators**:
- **Reject**: Salary (the rules noted on its fields), duplicate Stat ids in MarketStats, and the SearchPlan and HiringRequest rules above. Rejections on LLM-filled types feed the retry.
- **Normalise**: Evidence keys are sorted and deduplicated.
- **Left to the stages**: cross-object checks, such as Evidence keys being in the Sample or 1–3 questions per Pause.

**Glossary**: added **Region** and **Stat**.

**Handed to [State schema, reducers and run_log](06-state-schema-and-run-log.md)**:
- `broaden` (Collection) revises the Search Plan, but Request & Plan owns that slice, which breaks the single-writer rule.
- Where the `--focus` Run option lives in state.
