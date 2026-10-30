from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from talent_scout.kernel.types import Model
from talent_scout.runtime.pause import Pause


class NodeDone(Model):
    type: Literal["node_done"] = "node_done"
    node: str
    notes: list[str]


class Paused(Model):
    type: Literal["paused"] = "paused"
    pause: Pause


class Done(Model):
    type: Literal["done"] = "done"
    status: Literal["done", "aborted"]
    paths: list[Path]


class Stopped(Model):
    type: Literal["stopped"] = "stopped"
    node: str | None
    reason: str


RunEvent = Annotated[NodeDone | Paused | Done | Stopped, Field(discriminator="type")]


class ChunkMapper:
    """Turns one Run's stream chunks into events. Done and Stopped come from the Controller."""

    def __init__(self, log_len: int):
        # A node writes the whole run_log, so its notes are whatever lies past the last length seen.
        self._log_len = log_len

    def map(self, mode: str, chunk) -> list[RunEvent]:
        if mode != "updates":
            return []
        events = []
        for key, update in chunk.items():
            if key == "__interrupt__":
                events.extend(Paused(pause=i.value) for i in update)
            elif key != "__metadata__":
                events.append(NodeDone(node=key, notes=self._notes(update)))
        return events

    def _notes(self, update: dict | None) -> list[str]:
        run_log = (update or {}).get("run_log")
        if run_log is None:
            return []
        notes = [entry.message for entry in run_log[self._log_len:]]
        self._log_len = len(run_log)
        return notes
