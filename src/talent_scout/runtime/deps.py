from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from langgraph.types import Send

from talent_scout.gateway.gateway import JobsGateway
from talent_scout.kernel.jev import Jev
from talent_scout.kernel.llm import Tiers
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.state import State


@dataclass(frozen=True)
class Deps:
    tiers: Tiers
    jev: Jev
    gateway: JobsGateway
    settings: Settings
    # Tests set this to run every stage as its stub, even one that has landed.
    stub_stages: bool = False


Node = Callable[..., Awaitable[dict]]
Router = Callable[[State], str | list[Send]]
