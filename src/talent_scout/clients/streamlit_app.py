import json
import queue
import re

import streamlit as st

from talent_scout.clients.cli import LOW_DATA_CHOICES, REFUSALS, event_line
from talent_scout.clients.pauses import render_pause
from talent_scout.clients.streamlit_bridge import Live, get_bridge
from talent_scout.kernel.types import Dimension
from talent_scout.request_plan.types import PlanAction
from talent_scout.runtime.controller import InvalidAnswer, RunView
from talent_scout.runtime.events import ExtractProgress, NodeDone, Stopped
from talent_scout.runtime.registry import RunStatus

LOW_DATA_ACTIONS = list(LOW_DATA_CHOICES.values())
POLL_S = 1


def _go_live(live: Live) -> None:
    st.session_state["live"] = live
    st.rerun()


def _refusal_line(error: Exception) -> str:
    # An HTTPError can have an empty message, so the class name goes first.
    return f"{type(error).__name__}: {error}"


def _invalid_answer_lines(error: InvalidAnswer) -> str:
    lines = []
    for item in error.errors:
        where = ".".join(map(str, item.get("loc", ())))
        lines.append(f"- {where + ': ' if where else ''}{item['msg']}")
    return "That answer was not accepted:\n" + "\n".join(lines)


def _submit(thread_id: str, answer: dict | None, problems) -> None:
    """Resume the Run. A bad answer is shown in the slot above the form, which stays as it is."""
    try:
        live = get_bridge().resume(thread_id, answer)
    except InvalidAnswer as e:
        problems.error(_invalid_answer_lines(e))
    except REFUSALS as e:
        problems.error(_refusal_line(e))
    else:
        _go_live(live)


def _clarify_form(thread_id: str, pause, problems) -> None:
    with st.form("clarify"):
        # Options are suggestions: a typed value is accepted, and leaving it empty skips the question.
        picks = [
            st.selectbox(f"Answer {n}", question.options, index=None, accept_new_options=True)
            for n, question in enumerate(pause.payload.questions, 1)
        ]
        if st.form_submit_button("Submit"):
            _submit(thread_id, {"answers": [pick or "" for pick in picks]}, problems)


def _plan_review_form(thread_id: str, pause, problems) -> None:
    with st.form("plan_review"):
        action = st.radio("Action", list(PlanAction), format_func=lambda a: a.value, horizontal=True)
        plan_json = st.text_area("Plan JSON (used by edit)", pause.payload.plan.model_dump_json(indent=2), height=260)
        feedback = st.text_input("What should change? (used by reject)")
        if not st.form_submit_button("Submit"):
            return
    plan = None
    if action is PlanAction.edit:
        try:
            plan = json.loads(plan_json)
        except json.JSONDecodeError as e:
            problems.error(f"The plan is not valid JSON: {e}")
            return
    reject_feedback = feedback.strip() or None if action is PlanAction.reject else None
    _submit(thread_id, {"action": action, "plan": plan, "feedback": reject_feedback}, problems)


def _low_data_form(thread_id: str, problems) -> None:
    with st.form("low_data_review"):
        action = st.radio("Action", LOW_DATA_ACTIONS, horizontal=True)
        if st.form_submit_button("Submit"):
            _submit(thread_id, {"action": action}, problems)


def _pause_page(thread_id: str, pause) -> None:
    st.text(render_pause(pause))
    problems = st.container()
    match pause.kind:
        case "clarify":
            _clarify_form(thread_id, pause, problems)
        case "plan_review":
            _plan_review_form(thread_id, pause, problems)
        case "low_data_review":
            _low_data_form(thread_id, problems)


def _brief_page(view: RunView) -> None:
    state = view.state
    st.markdown(state.brief_markdown or "")
    json_col, markdown_col = st.columns(2)
    json_col.download_button("Download JSON", state.brief.model_dump_json(indent=2), "brief.json", "application/json")
    markdown_col.download_button("Download Markdown", state.brief_markdown or "", "brief.md", "text/markdown")


def _drain(live: Live) -> None:
    """Show node lines until the Run stops, pauses or finishes, then redraw from its real status."""
    last = bar = None
    with st.status("Run in progress", expanded=True) as status:
        while True:
            try:
                event = live.events.get(timeout=POLL_S)
            except queue.Empty:
                # Streamlit only notices a pending rerun at a st call, so a quiet node must not block it.
                status.update()
                continue
            if event is None:
                break
            last = event
            if isinstance(event, NodeDone):
                st.write(f"✓ {event.node}" + (f" — {'; '.join(event.notes)}" if event.notes else ""))
            elif isinstance(event, ExtractProgress):
                bar = bar or st.progress(0.0)
                bar.progress(min(event.done / event.total, 1.0), text=f"extracted {event.done}/{event.total}")
            elif line := event_line(event):  # tokens and reasoning give None, so they stay off this page
                st.text(line)  # text, since tool summaries carry search queries that markdown would mangle
        failed = isinstance(last, Stopped)
        status.update(label="Stopped" if failed else "Finished", state="error" if failed else "complete")
    del st.session_state["live"]
    st.rerun()


def _run_page(thread_id: str) -> None:
    if st.button("All Runs"):
        st.query_params.clear()
        st.rerun()
    live = st.session_state.get("live")
    try:
        view = get_bridge().get_run(thread_id)
    except REFUSALS as e:
        st.error(_refusal_line(e))
        return
    record = view.record
    st.text(f"Run {record.thread_id} · {record.status} · {record.summary}")  # text, since the request is user input
    if live and live.thread_id == thread_id:
        _drain(live)
    match record.status:
        case RunStatus.running:
            st.info("Run in progress")
            st.button("Refresh")
        case RunStatus.paused:
            _pause_page(thread_id, view.pause)
        case RunStatus.failed:
            st.error(f"Stopped at {view.stopped_at}: {record.error}")
            problems = st.container()
            if st.button("Resume"):
                _submit(thread_id, None, problems)
        case RunStatus.done:
            _brief_page(view)
        case RunStatus.aborted:
            log = view.state.run_log if view.state else []
            st.warning(f"Aborted: {log[-1].message if log else record.error or 'no reason recorded'}")


def _runs_table() -> None:
    records = get_bridge().list_runs()
    if not records:
        return
    # A markdown link to ?thread= reloads the page into that Run's own view.
    rows = ["| Run | Status | Request | Updated (UTC) |", "|---|---|---|---|"]
    for r in records:
        # The request is user text, so markdown syntax in it is escaped to stay plain.
        request = re.sub(r"([\\|\[\]!`*_<>])", r"\\\1", r.summary.replace("\n", " "))
        rows.append(f"| [{r.thread_id}](?thread={r.thread_id}) | {r.status} | {request} | {r.updated_at:%Y-%m-%d %H:%M} |")
    st.markdown("\n".join(rows))


def _home_page() -> None:
    with st.form("start"):
        request = st.text_area("Hiring request")
        focus = st.multiselect("Focus", [d.value for d in Dimension])
        submitted = st.form_submit_button("Start")
    if submitted:
        if not request.strip():
            st.error("The request can't be blank")
        else:
            try:
                live = get_bridge().start(request.strip(), [Dimension(f) for f in focus])
            except REFUSALS as e:
                st.error(_refusal_line(e))
            else:
                st.query_params["thread"] = live.thread_id
                _go_live(live)
    _runs_table()


st.set_page_config(page_title="Talent Scout")
st.title("Talent Scout")
if (thread := st.query_params.get("thread")) is None:
    _home_page()
else:
    _run_page(thread)
