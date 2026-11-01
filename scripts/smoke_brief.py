"""Live smoke test, not run in CI. Spends no job API calls, only cents on the model.

Runs the recorded fixture Postings through Analysis, then the real Brief writer and the Jev critic with its revisions, and
prints the Brief, the Outlook, how often the writer's checks made the model retry and each Insight's critic score. Run it from the repo root: python scripts/smoke_brief.py [model]
"""
import asyncio
import sys
from contextvars import ContextVar
from types import SimpleNamespace

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tracers.context import register_configure_hook

from smoke_analysis import initial_state, run_analysis
from talent_scout.brief.nodes import ROUTERS, make_nodes
from talent_scout.kernel.jev import make_jev
from talent_scout.kernel.llm import make_tiers
from talent_scout.kernel.settings import get_settings
from talent_scout.kernel.state import LogKind

sys.stdout.reconfigure(encoding="utf-8")


class ModelCalls(BaseCallbackHandler):
    """Counts model calls, so anything over one is the checks (or a failing model) forcing a retry."""

    def __init__(self):
        self.count, self.finishes = 0, []

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.count += 1

    def on_llm_end(self, response, **kwargs):
        self.finishes.append(response.generations[0][0].message.response_metadata.get("finish_reason"))


# The writer is called without a config, so the counter is hooked in through a context variable.
_calls: ContextVar[ModelCalls | None] = ContextVar("brief_smoke_calls", default=None)
register_configure_hook(_calls, inheritable=True)


async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "z-ai/glm-5.3-flash"
    state = await run_analysis(initial_state(), model)

    settings = get_settings().model_copy(update={"llm_cheap": [model], "llm_strong": [model], "replay_cache": None})
    tiers = make_tiers(settings)
    nodes = make_nodes(SimpleNamespace(tiers=tiers, settings=settings, jev=make_jev(settings, tiers)))

    calls = ModelCalls()
    _calls.set(calls)
    state = state.model_copy(update=await nodes["write_brief"](state))
    writer_calls, writer_finishes = calls.count, list(calls.finishes)  # the revisions' calls come after
    # The graph's loop: judge, and go back to the writer while an Insight is flagged and revisions remain.
    while True:
        state = state.model_copy(update=await nodes["critic"](state))
        if ROUTERS["critic"](state) == "render":
            break
        for insight, verdict in zip(state.brief_draft.insights, state.critic_verdicts):
            if not verdict.supported:
                print(f"Flagged ({verdict.p_yes:.2f}): {insight.text}")
        state = state.model_copy(update=await nodes["write_brief"](state))
    state = state.model_copy(update=await nodes["render"](state))

    # The Postings table is the fixtures again, so it is cut.
    print(state.brief_markdown.split("## Postings analysed")[0])
    outlook = state.brief.outlook
    print(f"\nOutlook: {outlook.rating.value}. {outlook.reason}")
    note = next(e for e in state.run_log if e.node == "write_brief")
    print(f"Writer: {note.message}; {writer_calls} model call(s), so {writer_calls - 1} retried; finish reasons {writer_finishes}")
    for entry in (e for e in state.run_log if e.node == "critic" and e.kind == LogKind.route):
        print(f"Critic: {entry.message}; scores {entry.data['scores']}")
    print(f"Revisions: {state.revisions}; unsupported at the end: {sum(not v.supported for v in state.critic_verdicts)}")
    print("Caveats:", *(e.message for e in state.run_log if e.kind == LogKind.caveat), sep="\n  ")


if __name__ == "__main__":
    asyncio.run(main())
