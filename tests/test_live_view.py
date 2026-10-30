import io

from rich.console import Console

from talent_scout.clients.cli import LiveView
from talent_scout.runtime.events import (
    ApiCalled, ExtractProgress, NodeDone, NodeStarted, Reasoning, Token, ToolCalled, ToolReturned,
)

DIM = "\x1b[2m"


def make_view():
    out = io.StringIO()
    # A real terminal, so the spinner and the dim style are rendered rather than dropped.
    return LiveView(Console(file=out, force_terminal=True, width=100)), out


def test_prose_streams_and_reasoning_is_dim_with_a_spinner_only_on_structured_nodes():
    view, out = make_view()

    # fetch_agent: a turn with no reasoning, prose around a tool call and an API call.
    view.show(NodeStarted(node="fetch_agent"))
    assert not view.spinning
    view.show(Reasoning(node="fetch_agent", text="Need Adzuna"))
    view.show(Token(node="fetch_agent", text="Searching "))
    view.show(Token(node="fetch_agent", text="Adzuna."))
    view.show(ToolCalled(name="search_adzuna", summary='"data analyst" page 1'))
    view.show(ApiCalled(source="adzuna", cached=True, count=50))
    view.show(ApiCalled(source="usajobs", cached=False, count=0, failed=True))
    view.show(ToolReturned(name="search_adzuna", summary="50 Postings, 38 new"))
    view.show(NodeDone(node="fetch_agent", notes=["done"]))

    # A structured node: the spinner runs until the first reasoning text, and the next node restarts it.
    view.show(NodeStarted(node="plan"))
    assert view.spinning
    view.show(Reasoning(node="plan", text="Weighing radius"))
    assert not view.spinning
    view.show(NodeDone(node="plan", notes=[]))
    view.show(NodeStarted(node="write_brief"))
    assert view.spinning
    view.show(NodeDone(node="write_brief", notes=[]))
    assert not view.spinning

    # Extraction is only a count, and Jev or plain-code nodes get no spinner.
    view.show(NodeStarted(node="batch_extract"))
    view.show(ExtractProgress(done=37, total=142))
    view.show(NodeDone(node="batch_extract", notes=[]))
    view.show(NodeStarted(node="relevance"))
    assert not view.spinning
    view.close()

    text = out.getvalue()
    # Switching from reasoning to prose starts a new line.
    assert DIM + "Need Adzuna" in text and "\nSearching Adzuna.\n" in text
    assert 'search_adzuna: "data analyst" page 1' in text and "search_adzuna: 50 Postings, 38 new" in text
    assert "adzuna: 50 Postings (cached)" in text and "usajobs failed" in text
    assert "drafting plan…" in text and "drafting write_brief…" in text
    assert DIM + "Weighing radius" in text
    assert "extracted 37/142" in text
    assert text.index("Searching Adzuna.") < text.index("✓ fetch_agent") < text.index("Weighing radius")
