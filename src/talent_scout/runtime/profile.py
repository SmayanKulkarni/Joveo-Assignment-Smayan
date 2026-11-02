from collections import Counter
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import StringConstraints, TypeAdapter

from talent_scout.kernel.state import State
from talent_scout.kernel.types import ADZUNA_CURRENCY, CurrencyCode, Dimension, Model, WorkMode

WINDOW = 10
SCALARS = ("role", "country", "currency", "seniority", "employment_type", "work_mode")
LISTS = ("places", "focus")
Field = Literal["role", "country", "currency", "seniority", "employment_type", "work_mode", "places", "focus", "titles"]

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# What a CSM may pin, held to the same rules as the Hiring Request and the plan.
PIN_TYPES = {
    "role": TypeAdapter(Text),
    "country": TypeAdapter(Literal[tuple(ADZUNA_CURRENCY)]),
    "currency": TypeAdapter(CurrencyCode),
    "seniority": TypeAdapter(Text),
    "employment_type": TypeAdapter(Text),
    "work_mode": TypeAdapter(WorkMode),
    "places": TypeAdapter(list[Text]),
    "focus": TypeAdapter(list[Dimension]),
}


class Earlier(Model):
    thread_id: str
    date: date
    role: str
    country: str
    sample_size: int
    median_pay: float | None  # Advertised only
    currency: str | None


class Learned(Model):
    values: dict[str, str | list[str]] = {}
    runs: dict[str, int] = {}  # field -> how many Runs gave that value
    titles: dict[str, int] = {}  # title -> Runs it worked in, commonest first
    earlier: list[Earlier] = []


class RunFacts(Model):
    result: Earlier
    fields: dict[str, str | tuple[str, ...]]  # a field the Run didn't state is absent
    worked_titles: list[str]  # empty unless the Sample met the target


class Entry(Model):
    value: str | list[str]
    runs: int | None  # None when the CSM set it


class ProfileOut(Model):
    values: dict[str, Entry]
    titles: dict[str, int]
    earlier: list[Earlier]
    cleared_at: datetime | None


def facts_of(thread_id: str, created: date, state: State) -> RunFacts | None:
    request, plan = state.hiring_request, state.current_plan
    if request is None or plan is None or state.stats is None:
        return None
    fields = {name: str(getattr(request, name)) for name in SCALARS if getattr(request, name)}
    fields["places"] = tuple(plan.locations)
    fields["focus"] = tuple(sorted(d.value for d in state.focus))
    pay = next((s for s in state.stats.stats if s.id == "comp.advertised.median"), None)
    result = Earlier(
        thread_id=thread_id, date=created, role=request.role, country=request.country, sample_size=len(state.sample),
        median_pay=float(pay.value) if pay else None, currency=pay.unit.split("/")[0] if pay and pay.unit else None,
    )
    return RunFacts(result=result, fields=fields, worked_titles=plan.titles if len(state.sample) >= plan.target_postings else [])


def learn(runs: list[RunFacts]) -> Learned:
    """Worked out by code from these Runs, newest first. No model reads or writes it."""
    values, counts = {}, {}
    for name in (*SCALARS, *LISTS):
        # An empty list means "nothing stated", not a value to learn.
        seen = [r.fields[name] for r in runs if r.fields.get(name)]
        if seen:
            tally = Counter(seen)
            # max returns the first of equals, and `seen` is newest first, so a tie goes to the newest.
            best = max(seen, key=tally.__getitem__)
            values[name], counts[name] = (list(best) if isinstance(best, tuple) else best), tally[best]
    titles = Counter(t for r in runs for t in dict.fromkeys(r.worked_titles))
    return Learned(values=values, runs=counts, titles=dict(titles.most_common()), earlier=[r.result for r in runs])


def shown(learned: Learned, pinned: dict, removed: list[str]) -> tuple[dict[str, Entry], dict[str, int]]:
    """What the CSM sees and a Run would use: learned values, minus the removed, with pins on top."""
    entries = {k: Entry(value=v, runs=learned.runs[k]) for k, v in learned.values.items() if k not in removed}
    entries |= {k: Entry(value=v, runs=None) for k, v in pinned.items()}
    return entries, {} if "titles" in removed else learned.titles
