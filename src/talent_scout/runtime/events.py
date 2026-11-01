import logging
from pathlib import Path
from typing import Annotated, Literal

from langchain_core.messages import AIMessage

from pydantic import Field

from talent_scout.kernel.state import LogKind
from talent_scout.kernel.types import Model
from talent_scout.runtime.pause import Pause

logger = logging.getLogger(__name__)

TOKEN_NODE = "fetch_agent"
EXTRACT_NODE = "batch_extract"


class NodeStarted(Model):
    type: Literal["node_started"] = "node_started"
    node: str


class NodeDone(Model):
    type: Literal["node_done"] = "node_done"
    node: str
    notes: list[str]
    results: list[str] = []


class Token(Model):
    type: Literal["token"] = "token"
    node: str
    text: str


class Reasoning(Model):
    type: Literal["reasoning"] = "reasoning"
    node: str
    text: str


class ToolCalled(Model):
    type: Literal["tool_called"] = "tool_called"
    name: str
    summary: str


class ToolReturned(Model):
    type: Literal["tool_returned"] = "tool_returned"
    name: str
    summary: str


class ApiCalled(Model):
    type: Literal["api_called"] = "api_called"
    source: str
    cached: bool
    count: int
    failed: bool = False


class ExtractProgress(Model):
    type: Literal["extract_progress"] = "extract_progress"
    done: int
    total: int


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


RunEvent = Annotated[
    NodeStarted | NodeDone | Token | Reasoning | ToolCalled | ToolReturned | ApiCalled | ExtractProgress | Paused | Done | Stopped,
    Field(discriminator="type"),
]

# Never buffered: one fetch_agent turn could push every other event out of the replay buffer.
LIVE_ONLY = (Token, Reasoning)

# Stages and the Gateway emit these as plain dicts, so they never import Runtime.
CUSTOM_EVENTS = {"tool_called": ToolCalled, "tool_returned": ToolReturned, "api_called": ApiCalled}


class ChunkMapper:
    """Turns one Run's stream chunks into events. Done and Stopped come from the Controller."""

    def __init__(self, log_len: int):
        # A node writes the whole run_log, so its notes are whatever lies past the last length seen.
        self._log_len = log_len
        # Extraction fans out as one task per branch. All the starts arrive before the first update, and
        # a rerun replays finished branches as cached updates, so one count per stream stays right.
        self._extract_total = 0
        self._extract_done = 0

    def map(self, mode: str, chunk) -> list[RunEvent]:
        if mode == "updates":
            return self._updates(chunk)
        if mode == "tasks":
            return self._tasks(chunk)
        if mode == "messages":
            return self._messages(*chunk)
        if mode == "custom":
            return self._custom(chunk)
        return []

    def _tasks(self, chunk: dict) -> list[RunEvent]:
        if "input" not in chunk:  # a finish event; updates already carry what we need
            return []
        if chunk["name"] == EXTRACT_NODE:
            self._extract_total += 1
            return [] if self._extract_total > 1 else [NodeStarted(node=EXTRACT_NODE)]
        return [NodeStarted(node=chunk["name"])]

    def _updates(self, chunk: dict) -> list[RunEvent]:
        events = []
        for key, update in chunk.items():
            if key == "__interrupt__":
                events.extend(Paused(pause=i.value) for i in update)
            elif key == EXTRACT_NODE:
                self._extract_done += 1
                events.append(ExtractProgress(done=self._extract_done, total=self._extract_total))
                if self._extract_done == self._extract_total:
                    events.append(NodeDone(node=key, **self._lines(update)))
            elif key != "__metadata__":
                events.append(NodeDone(node=key, **self._lines(update)))
        return events

    def _messages(self, message, metadata: dict) -> list[RunEvent]:
        if not isinstance(message, AIMessage):
            return []
        node = metadata.get("langgraph_node")
        events = []
        for block in message.content_blocks:
            if block["type"] == "text" and node == TOKEN_NODE and block["text"]:
                events.append(Token(node=node, text=block["text"]))
            elif block["type"] == "reasoning" and node != EXTRACT_NODE and block.get("reasoning"):
                events.append(Reasoning(node=node, text=block["reasoning"]))
        return events

    def _custom(self, chunk: dict) -> list[RunEvent]:
        event_class = CUSTOM_EVENTS.get(chunk.get("type"))
        if event_class is None:
            logger.warning("Dropping unknown custom event: %s", chunk.get("type"))
            return []
        return [event_class(**{k: v for k, v in chunk.items() if k != "type"})]

    def _lines(self, update: dict | None) -> dict[str, list[str]]:
        run_log = (update or {}).get("run_log")
        if run_log is None:
            return {"notes": [], "results": []}
        added = run_log[self._log_len:]
        self._log_len = len(run_log)
        return {"notes": [e.message for e in added], "results": [e.message for e in added if e.kind == LogKind.result]}
