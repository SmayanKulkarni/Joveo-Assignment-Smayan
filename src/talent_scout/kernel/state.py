import functools
import inspect
from enum import StrEnum
from typing import Annotated, Any, Literal

from langchain_core.messages import AnyMessage
from langgraph.types import Command, Send
from pydantic import BaseModel, Field, JsonValue, TypeAdapter, ValidationError

from talent_scout.analysis.types import Extraction
from talent_scout.brief.types import MarketBrief
from talent_scout.collection.types import FetchRecord
from talent_scout.kernel.types import (
    Assumption,
    ClarifyingQuestion,
    Dimension,
    HiringRequest,
    MarketStats,
    Model,
    Posting,
    SearchPlan,
)
from talent_scout.request_plan.types import PlanAction, RequestDraft


class LogKind(StrEnum):
    route = "route"
    pause = "pause"
    caveat = "caveat"
    warning = "warning"
    note = "note"


class RunLogEntry(Model):
    node: str
    kind: LogKind
    message: str
    data: dict[str, JsonValue]


class Owner(StrEnum):
    input = "input"
    request_plan = "request_plan"
    collection = "collection"
    analysis = "analysis"
    brief = "brief"
    kernel = "kernel"


def merge(a: dict, b: dict) -> dict:
    # Parallel Send branches write this key in the same super-step, so they need a combiner.
    return {**a, **b}


def _owned_by(owner: Owner, **kwargs: Any) -> Any:
    return Field(json_schema_extra={"owner": owner}, **kwargs)


class State(Model):
    # input: written once by the Run Controller, never by a node
    request_text: str = _owned_by(Owner.input)
    focus: list[Dimension] = _owned_by(Owner.input, default_factory=list)

    hiring_request: HiringRequest | None = _owned_by(Owner.request_plan, default=None)
    questions: list[ClarifyingQuestion] = _owned_by(Owner.request_plan, default_factory=list)
    assumptions: list[Assumption] = _owned_by(Owner.request_plan, default_factory=list)
    search_plan: SearchPlan | None = _owned_by(Owner.request_plan, default=None)
    request_draft: RequestDraft | None = _owned_by(Owner.request_plan, default=None)
    plan_decision: PlanAction | None = _owned_by(Owner.request_plan, default=None)
    plan_feedback: str | None = _owned_by(Owner.request_plan, default=None)

    messages: list[AnyMessage] = _owned_by(Owner.collection, default_factory=list)
    postings: dict[str, Posting] = _owned_by(Owner.collection, default_factory=dict)
    sample: list[str] = _owned_by(Owner.collection, default_factory=list)
    broadened_plans: list[SearchPlan] = _owned_by(Owner.collection, default_factory=list)
    fetches: list[FetchRecord] = _owned_by(Owner.collection, default_factory=list)
    relevance_verdicts: dict[str, bool] = _owned_by(Owner.collection, default_factory=dict)
    fetch_blocked: str | None = _owned_by(Owner.collection, default=None)
    low_data_decision: Literal["broaden", "continue", "abort"] | None = _owned_by(Owner.collection, default=None)
    low_data_guidance: str | None = _owned_by(Owner.collection, default=None)

    extractions: Annotated[dict[str, Extraction], merge] = _owned_by(Owner.analysis, default_factory=dict)
    skill_aliases: dict[str, str] = _owned_by(Owner.analysis, default_factory=dict)  # folded name -> canonical name
    stats: MarketStats | None = _owned_by(Owner.analysis, default=None)

    brief: MarketBrief | None = _owned_by(Owner.brief, default=None)
    brief_markdown: str | None = _owned_by(Owner.brief, default=None)

    run_log: list[RunLogEntry] = _owned_by(Owner.kernel, default_factory=list)

    @property
    def current_plan(self) -> SearchPlan | None:
        return self.broadened_plans[-1] if self.broadened_plans else self.search_plan

    @property
    def sample_postings(self) -> list[Posting]:
        return [self.postings[k] for k in self.sample]


def log(state: State, node: str, kind: LogKind, message: str, /, **data: JsonValue) -> dict:
    entry = RunLogEntry(node=node, kind=kind, message=message, data=data)
    return {"run_log": [*state.run_log, entry]}


class StateWriteError(Exception):
    def __init__(self, node: str, key: str, reason: str):
        super().__init__(f"{node}: bad write to '{key}': {reason}")
        self.node, self.key, self.reason = node, key, reason


@functools.cache
def _adapter(key: str) -> TypeAdapter:
    return TypeAdapter(State.model_fields[key].annotation)


def _owner(key: str) -> str:
    return State.model_fields[key].json_schema_extra["owner"]


def _check_update(node: str, owner: str, state: Any, update: dict) -> None:
    for key, value in update.items():
        if key not in State.model_fields:
            raise StateWriteError(node, key, "not a State field")
        # run_log is open to every node; input fields to none.
        if key != "run_log" and (_owner(key) == Owner.input or _owner(key) != owner):
            raise StateWriteError(node, key, f"belongs to '{_owner(key)}', not '{owner}'")
        try:
            # strict: values must already be model instances, as persistence requires.
            _adapter(key).validate_python(value, strict=True)
        except ValidationError as e:
            raise StateWriteError(node, key, "value has the wrong type") from e

    if "run_log" in update:
        # Send branches get a payload, not State, so they have no log to extend.
        current = getattr(state, "run_log", None)
        if current is None:
            raise StateWriteError(node, "run_log", "this node has no run_log to extend")
        if update["run_log"][: len(current)] != current:
            raise StateWriteError(node, "run_log", "update does not start with the current log")


def _check_sends(node: str, result: Any) -> None:
    for item in result if isinstance(result, list) else [result]:
        if isinstance(item, Send) and not isinstance(item.arg, Model):
            raise StateWriteError(node, item.node, f"Send arg must be a model instance, got {type(item.arg).__name__}")


def _check(node: str, owner: str, state: Any, result: Any) -> None:
    if isinstance(result, BaseModel):
        # Returning State rewrites every set field and skips the per-key checks.
        raise StateWriteError(node, "*", "return a partial dict, not a model")
    if isinstance(result, Command) and isinstance(result.update, dict):
        _check_update(node, owner, state, result.update)
    elif isinstance(result, dict):
        _check_update(node, owner, state, result)
    else:
        _check_sends(node, result)


def owned(node: str, owner: str):
    """Wrap a node or router so a bad write fails here, not in the next node."""

    owner = Owner(owner)  # a typo fails at wiring time, not on the first write

    def wrap(fn):
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def guarded(state, *args, **kwargs):
                result = await fn(state, *args, **kwargs)
                _check(node, owner, state, result)
                return result

        else:

            @functools.wraps(fn)
            def guarded(state, *args, **kwargs):
                result = fn(state, *args, **kwargs)
                _check(node, owner, state, result)
                return result

        return guarded

    return wrap
