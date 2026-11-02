from datetime import UTC, date, datetime

from test_accounts_api import ALICE, BOB, customer_of, hosted, sign_in, start, wait_idle  # noqa: F401

from talent_scout.runtime.profile import Earlier, RunFacts, learn


def run(role="Data Engineer", *, titles=(), places=(), day=1, **fields) -> RunFacts:
    result = Earlier(thread_id=f"t{day}", date=date(2026, 1, day), role=role, country="us", sample_size=30, median_pay=None, currency=None)
    return RunFacts(result=result, fields={"role": role, "country": "us", "places": places, **fields}, worked_titles=list(titles))


def test_each_field_takes_its_commonest_value_and_a_tie_goes_to_the_newest():
    # Newest first, as the controller passes them.
    learned = learn([run("Analyst", seniority="senior", day=3), run("Engineer", day=2), run("Engineer", seniority="junior", day=1)])
    assert (learned.values["role"], learned.runs["role"]) == ("Engineer", 2)
    assert learned.values["seniority"] == "senior"  # 1 against 1: the newest
    assert "currency" not in learned.values and "places" not in learned.values  # never stated


def test_titles_count_once_per_run_and_only_for_runs_that_met_the_target():
    learned = learn([run(titles=["A", "B", "A"], day=3), run(titles=["B"], day=2), run(titles=[], day=1)])
    assert learned.titles == {"B": 2, "A": 1}
    assert [e.thread_id for e in learned.earlier] == ["t3", "t2", "t1"]


def test_list_fields_are_learned_whole():
    assert learn([run(places=("Austin", "Dallas"))]).values["places"] == ["Austin", "Dallas"]


ANSWERS = {
    "clarify": {"answers": ["Austin, Texas"]},
    "plan_review": {"action": "approve", "plan": None, "feedback": None},
    "low_data_review": {"action": "broaden", "guidance": None},
}


def finished(client, customer_id) -> str:
    thread_id = start(client, customer_id).json()["thread_id"]
    while pause := wait_idle(client, thread_id)["pause"]:
        client.post(f"/api/runs/{thread_id}/resume", json={"answer": ANSWERS[pause["kind"]]})
    return thread_id


def test_a_done_run_teaches_the_profile_and_deleting_it_unteaches(hosted):
    sign_in(hosted, ALICE)
    acme = customer_of(hosted)
    assert hosted.get(f"/api/customers/{acme}/profile").json()["values"] == {}
    first, second = finished(hosted, acme), finished(hosted, acme)
    profile = hosted.get(f"/api/customers/{acme}/profile").json()
    assert profile["values"]["role"]["runs"] == 2 and len(profile["earlier"]) == 2

    hosted.delete(f"/api/runs/{first}")
    assert [e["thread_id"] for e in hosted.get(f"/api/customers/{acme}/profile").json()["earlier"]] == [second]
    hosted.delete(f"/api/runs/{second}")
    assert hosted.get(f"/api/customers/{acme}/profile").json()["values"] == {}


def test_only_the_last_ten_done_runs_count(hosted):
    sign_in(hosted, ALICE)
    acme = customer_of(hosted)
    for _ in range(11):
        finished(hosted, acme)
    assert len(hosted.get(f"/api/customers/{acme}/profile").json()["earlier"]) == 10


def test_pinned_beats_learned_removed_is_never_relearned_and_clearing_forgets_older_runs(hosted):
    sign_in(hosted, ALICE)
    acme = customer_of(hosted)
    url = f"/api/customers/{acme}/profile"
    finished(hosted, acme)
    learned_role = hosted.get(url).json()["values"]["role"]["value"]

    pinned = hosted.patch(url, json={"set": {"role": "Data Scientist", "work_mode": "remote"}}).json()
    assert pinned["values"]["role"] == {"value": "Data Scientist", "runs": None}
    assert hosted.patch(url, json={"set": {"country": "xx"}}).status_code == 422
    assert hosted.patch(url, json={"set": {"titles": ["x"]}}).status_code == 422

    removed = hosted.patch(url, json={"remove": ["role"]}).json()
    assert "role" not in removed["values"] and "work_mode" in removed["values"]
    finished(hosted, acme)  # a recompute must not bring the role back
    assert "role" not in hosted.get(url).json()["values"]
    assert hosted.patch(url, json={"set": {"role": learned_role}}).json()["values"]["role"]["value"] == learned_role

    assert hosted.delete(url).status_code == 204
    cleared = hosted.get(url).json()
    assert cleared["values"] == {} and cleared["earlier"] == [] and cleared["cleared_at"]
    finished(hosted, acme)  # only Runs after the clear count
    assert len(hosted.get(url).json()["earlier"]) == 1
    assert datetime.fromisoformat(cleared["cleared_at"]) < datetime.now(UTC)


def test_another_csms_profile_is_a_404_and_deleting_the_customer_removes_it(hosted):
    sign_in(hosted, ALICE)
    acme = customer_of(hosted)
    finished(hosted, acme)
    sign_in(hosted, BOB)
    for call in (hosted.get, lambda p: hosted.patch(p, json={}), hosted.delete):
        assert call(f"/api/customers/{acme}/profile").status_code == 404

    sign_in(hosted, ALICE)
    assert hosted.delete(f"/api/customers/{acme}").status_code == 204
    left = hosted.portal.call(hosted.app.state.controller.accounts._run, "SELECT 1 FROM customer_profiles WHERE customer_id = ?", (acme,))
    assert left == []


def test_a_failed_recompute_is_logged_and_the_run_still_finishes(hosted, monkeypatch, caplog):
    sign_in(hosted, ALICE)
    acme = customer_of(hosted)

    async def broken(*_):
        raise RuntimeError("db hiccup")

    monkeypatch.setattr(hosted.app.state.controller.accounts, "save_learned", broken)
    thread_id = finished(hosted, acme)
    assert hosted.get(f"/api/runs/{thread_id}").json()["record"]["status"] == "done"
    assert "Relearning the profile" in caplog.text


def test_an_aborted_run_does_not_count(hosted):
    sign_in(hosted, ALICE)
    acme = customer_of(hosted)
    thread_id = start(hosted, acme).json()["thread_id"]
    wait_idle(hosted, thread_id)
    hosted.post(f"/api/runs/{thread_id}/cancel")
    wait_idle(hosted, thread_id)
    assert hosted.get(f"/api/customers/{acme}/profile").json()["earlier"] == []
