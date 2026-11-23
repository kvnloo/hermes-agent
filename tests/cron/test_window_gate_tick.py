"""The tick applies the decision-window gate to due jobs that opt in.

A job with neither ``window_class`` nor ``stale_after_s`` is dispatched exactly as before and
the window provider is never consulted. A held job keeps its due instant (it fires on a later
tick once its window opens) and says why in ``last_fire_error``; a stale recurring occurrence is
dropped and the job moves to its next slot. Design: NousResearch/hermes-agent#158538.

Every fixture here is synthetic.
"""
from datetime import timedelta

import pytest

import cron.jobs as J
import cron.scheduler as S
from cron import scheduler_window_gate
from cron.decision_window import WindowClass
from cron.job_definition import JOB_DEFINITION_FIELDS, merge_job_definition


@pytest.fixture
def cron_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "cron").mkdir(parents=True)
    (home / "scripts").mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(J, "HERMES_DIR", home)
    monkeypatch.setattr(J, "CRON_DIR", home / "cron")
    monkeypatch.setattr(J, "JOBS_FILE", home / "cron" / "jobs.json")
    monkeypatch.setattr(J, "OUTPUT_DIR", home / "cron" / "output")
    monkeypatch.setattr(S, "_hermes_home", home)
    monkeypatch.setattr(S, "_sweep_mcp_orphans", lambda: None)
    S._running_job_ids.clear()
    return home


@pytest.fixture
def dispatched(monkeypatch):
    fired = []

    def fake_process(job, adapters, loop, verbose):
        fired.append(job["id"])
        return True

    monkeypatch.setattr(S, "_process_due_job", fake_process)
    return fired


class Fixed:
    def __init__(self, value):
        self.value = value

    def current(self, now):
        return self.value


def _use_provider(monkeypatch, provider):
    monkeypatch.setattr(scheduler_window_gate, "resolve_window_provider", lambda: provider)


def _make_due(job_id: str, minutes_ago: float = 1) -> str:
    stored = J.load_jobs()
    slot = (J._hermes_now() - timedelta(minutes=minutes_ago)).replace(microsecond=0).isoformat()
    next(r for r in stored if r["id"] == job_id)["next_run_at"] = slot
    J.save_jobs(stored)
    return slot


def _stored(job_id):
    return next(j for j in J.load_jobs() if j["id"] == job_id)


def test_existing_job_fires_as_before_without_consulting_a_provider(cron_home, dispatched, monkeypatch):
    monkeypatch.setattr(scheduler_window_gate, "resolve_window_provider",
                        lambda: pytest.fail("no job opted in: the provider must not be resolved"))
    job = J.create_job(prompt="synthetic digest", schedule="every 1h", name="plain", deliver="local")
    assert "window_class" not in job and "stale_after_s" not in job
    due = _make_due(job["id"])

    S.tick(verbose=False)

    assert dispatched == [job["id"]]
    stored = _stored(job["id"])
    assert stored["next_run_at"] != due
    assert stored.get("last_fire_error") is None


def test_create_job_persists_the_window_fields(cron_home):
    job = J.create_job(prompt="synthetic question", schedule="every 1d", deliver="local",
                       window_class="Wind_Down", stale_after_s="5400")
    stored = _stored(job["id"])
    assert stored["window_class"] == "wind_down"
    assert stored["stale_after_s"] == 5400.0


def test_create_job_rejects_bad_window_fields(cron_home):
    with pytest.raises(ValueError, match="window_class"):
        J.create_job(prompt="x", schedule="every 1h", window_class="lunchtime")
    with pytest.raises(ValueError, match="stale_after_s"):
        J.create_job(prompt="x", schedule="every 1h", stale_after_s=0)
    assert J.load_jobs() == []


def test_a_one_shot_cannot_wait_for_a_window(cron_home):
    run_at = (J._hermes_now() + timedelta(hours=1)).replace(microsecond=0).isoformat()
    with pytest.raises(ValueError, match="recurring"):
        J.create_job(prompt="x", schedule=run_at, window_class="peak")


def test_update_job_sets_and_clears_the_window_fields(cron_home):
    job = J.create_job(prompt="synthetic review", schedule="every 1d", deliver="local")
    J.update_job(job["id"], {"window_class": "trough", "stale_after_s": 3600})
    assert _stored(job["id"])["window_class"] == "trough"
    with pytest.raises(ValueError, match="window_class"):
        J.update_job(job["id"], {"window_class": "later"})
    J.update_job(job["id"], {"window_class": None, "stale_after_s": None})
    stored = _stored(job["id"])
    assert stored.get("window_class") is None and stored.get("stale_after_s") is None


def test_update_checks_the_window_against_the_new_schedule(cron_home):
    job = J.create_job(prompt="synthetic review", schedule="every 1d", deliver="local", window_class="trough")
    # ``repeat`` in the same update leaves the schedule a string until the update applies it.
    J.update_job(job["id"], {"schedule": "every 2h", "repeat": 3})
    assert _stored(job["id"])["schedule"]["kind"] == "interval"
    run_at = (J._hermes_now() + timedelta(hours=1)).replace(microsecond=0).isoformat()
    for updates in ({"schedule": run_at}, {"schedule": run_at, "repeat": 1}):
        with pytest.raises(ValueError, match="recurring"):
            J.update_job(job["id"], updates)


def test_held_job_keeps_its_due_instant_and_says_why(cron_home, dispatched, monkeypatch):
    _use_provider(monkeypatch, Fixed(WindowClass.TROUGH))
    held = J.create_job(prompt="synthetic decision", schedule="every 1h", deliver="local", window_class="peak")
    plain = J.create_job(prompt="synthetic digest", schedule="every 1h", deliver="local")
    held_due = _make_due(held["id"])
    _make_due(plain["id"])

    S.tick(verbose=False)

    assert dispatched == [plain["id"]]
    stored = _stored(held["id"])
    assert stored["next_run_at"] == held_due, "the slot is held, not consumed"
    assert "pending_slot" not in stored and stored["last_run_at"] is None
    detail = stored["last_fire_error"]["detail"]
    assert detail.startswith("Held:") and "trough" in detail and "peak" in detail


def test_held_job_fires_on_the_tick_its_window_opens(cron_home, dispatched, monkeypatch):
    provider = Fixed(WindowClass.TROUGH)
    _use_provider(monkeypatch, provider)
    job = J.create_job(prompt="synthetic decision", schedule="every 1h", deliver="local", window_class="peak")
    _make_due(job["id"])
    S.tick(verbose=False)
    assert dispatched == []

    provider.value = WindowClass.PEAK
    S.tick(verbose=False)
    assert dispatched == [job["id"]]


def test_stale_recurring_occurrence_is_dropped_and_the_job_moves_on(cron_home, dispatched, monkeypatch):
    _use_provider(monkeypatch, Fixed(WindowClass.PEAK))
    job = J.create_job(prompt="synthetic nudge", schedule="every 1h", deliver="local",
                       window_class="peak", stale_after_s=60)
    due = _make_due(job["id"], minutes_ago=10)

    S.tick(verbose=False)

    assert dispatched == []
    stored = _stored(job["id"])
    assert stored["next_run_at"] != due
    assert J._instant_after(J._ensure_aware(J.datetime.fromisoformat(stored["next_run_at"])), J._hermes_now())
    assert "pending_slot" not in stored
    assert "stale" in stored["last_fire_error"]["detail"]


def test_a_profile_distribution_keeps_the_window_fields(cron_home):
    assert {"window_class", "stale_after_s"} <= JOB_DEFINITION_FIELDS
    local = J.create_job(prompt="synthetic", schedule="every 1h", deliver="local")
    merged = merge_job_definition(local, {**local, "window_class": "peak", "stale_after_s": 900})
    assert merged["window_class"] == "peak" and merged["stale_after_s"] == 900
