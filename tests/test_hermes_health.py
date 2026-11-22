"""The per-home health ledger: cross-process warn-once, and still-failing conditions that stay visible.

Measured on a 9-profile install over ~46h: 7,217 of 9,899 WARNING+ lines (73%) were seven
"Skill ... is shadowed" notices re-emitted by every fresh kanban-worker/TUI process (515
processes x 7), while a plugin hook failing with EPERM on every approval logged one WARNING per
process and then only DEBUG — nothing recorded that it was still failing.
"""

import json
import logging
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import hermes_health


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    hermes_health._reset_for_tests()
    yield
    hermes_health._reset_for_tests()


def _warnings(caplog, needle):
    return [r for r in caplog.records if r.levelno == logging.WARNING and needle in r.getMessage()]


def test_warn_once_survives_a_new_process(tmp_path, caplog):
    """A fresh process (simulated by clearing in-memory state) must not re-warn within the ttl."""
    log = logging.getLogger("test.health")
    with caplog.at_level(logging.DEBUG, logger="test.health"):
        for _ in range(5):
            hermes_health._reset_for_tests()  # what a new kanban worker process starts with
            hermes_health.warn_once(log, "skill_shadowed", "a\0b", "Skill '%s' is shadowed", "reflect")
    assert len(_warnings(caplog, "shadowed")) == 1
    [row] = hermes_health.conditions()
    assert row["count"] == 5 and row["severity"] == hermes_health.NOTICE


def test_warn_once_really_crosses_processes(tmp_path):
    """Two real interpreter processes share one ledger: only the first warns."""
    repo = Path(hermes_health.__file__).resolve().parent
    code = textwrap.dedent("""
        import logging, sys
        sys.path.insert(0, sys.argv[1])
        import hermes_health
        print(hermes_health.warn_once(logging.getLogger("x"), "k", "key", "msg"))
    """)
    env = {"HERMES_HOME": str(tmp_path / "home"), "PATH": "/usr/bin:/bin"}
    outs = [subprocess.run([sys.executable, "-c", code, str(repo)], env=env, capture_output=True, check=True,
                           text=True, timeout=60).stdout.strip().splitlines()[-1] for _ in range(3)]
    assert outs == ["True", "False", "False"]


def test_warn_once_rewarns_after_ttl(caplog):
    log = logging.getLogger("test.health")
    with caplog.at_level(logging.WARNING, logger="test.health"):
        hermes_health.warn_once(log, "k", "x", "notice", now=1000.0, ttl=60)
        hermes_health.warn_once(log, "k", "x", "notice", now=1030.0, ttl=60)
        hermes_health.warn_once(log, "k", "x", "notice", now=1061.0, ttl=60)
    assert len(_warnings(caplog, "notice")) == 2


def test_record_counts_repeats_and_throttles_writes(monkeypatch):
    writes = []
    real_save = hermes_health._save
    monkeypatch.setattr(hermes_health, "_save", lambda p, c: (writes.append(1), real_save(p, c)))
    for _ in range(50):
        hermes_health.record("plugin_hook_failure", "k", "EPERM")
    assert len(writes) == 1  # one write per WRITE_THROTTLE_S, not one per call
    monkeypatch.setattr(hermes_health, "WRITE_THROTTLE_S", 0.0)
    hermes_health.record("plugin_hook_failure", "k", "EPERM")
    [row] = hermes_health.active_failures()
    assert row["count"] == 51  # the throttled repeats were flushed, not lost


def test_resolve_hides_from_active_failures():
    hermes_health.record("cron_job_error", "job1", "cron job x: boom")
    assert [r["key"] for r in hermes_health.active_failures()] == ["job1"]
    assert hermes_health.resolve("cron_job_error", "job1") is True
    assert hermes_health.active_failures() == []
    assert hermes_health.conditions(include_resolved=True)[0]["resolved_at"]


def test_unwritable_ledger_falls_back_to_plain_warning(tmp_path, monkeypatch, caplog):
    """A full or read-only disk must not swallow the warning or raise into the caller."""
    def boom(*a, **k):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(hermes_health, "_save", boom)
    log = logging.getLogger("test.health")
    with caplog.at_level(logging.WARNING, logger="test.health"):
        assert hermes_health.warn_once(log, "k", "x", "still said") is True
    assert hermes_health.record("k2", "y", "z") is None
    assert len(_warnings(caplog, "still said")) == 1


def test_ledger_is_bounded(monkeypatch):
    monkeypatch.setattr(hermes_health, "MAX_ENTRIES", 5)
    for i in range(12):
        hermes_health.record("k", f"key{i}", "s", now=float(i))
    data = json.loads(hermes_health.ledger_path().read_text())
    assert len(data["conditions"]) == 5
    assert {c["key"] for c in data["conditions"].values()} == {f"key{i}" for i in range(7, 12)}


def test_repeated_hook_failure_stays_visible_in_ledger(tmp_path, monkeypatch, caplog):
    """The plugin dispatcher demotes repeats to DEBUG; the ledger must still count them."""
    from hermes_cli.plugins import PluginManager
    monkeypatch.setattr(hermes_health, "WRITE_THROTTLE_S", 0.0)
    manager = PluginManager()

    def on_request(**kwargs):
        raise PermissionError(1, "Operation not permitted", "approvals.jsonl")

    manager._hooks.setdefault("pre_tool_call", []).append(on_request)
    with caplog.at_level(logging.DEBUG, logger="hermes_cli.plugins"):
        for _ in range(4):
            manager.invoke_hook("pre_tool_call", tool_name="t", args={})
    assert len(_warnings(caplog, "on_request")) == 1
    [row] = hermes_health.active_failures()
    assert row["kind"] == "plugin_hook_failure" and row["count"] == 4
    assert "Operation not permitted" in row["summary"]


def test_shadowed_skill_warns_once_across_processes(tmp_path, caplog):
    """The production path: resolve_skill_catalog re-run by a fresh process must not re-warn."""
    from agent import skill_utils
    local, ext = tmp_path / "local", tmp_path / "ext"
    for root, body in ((local, "LOCAL"), (ext, "EXTERNAL")):
        (root / "reflect").mkdir(parents=True)
        (root / "reflect" / "SKILL.md").write_text(f"---\nname: reflect\n---\n{body}\n")
    entries = [
        {"name": "reflect", "tier": skill_utils.TIER_LOCAL, "root": local, "path": local / "reflect" / "SKILL.md"},
        {"name": "reflect", "tier": skill_utils.TIER_EXTERNAL, "root": ext, "path": ext / "reflect" / "SKILL.md"},
    ]
    with caplog.at_level(logging.DEBUG, logger="agent.skill_utils"):
        for _ in range(3):
            skill_utils._SHADOW_CHECKED.clear()  # a new process
            hermes_health._reset_for_tests()
            out = skill_utils.resolve_skill_catalog(entries)
    assert [e["status"] for e in out] == ["unique", "shadowed"]
    assert len(_warnings(caplog, "is shadowed")) == 1
    assert hermes_health.conditions()[0]["count"] == 3


def test_cron_run_failure_is_recorded_and_success_resolves(monkeypatch):
    from cron import jobs
    job = {"id": "abc123", "name": "nightly"}
    jobs._record_run_outcome(job, False, "provider exploded", None, None, "2026-11-21T00:00:00")
    [row] = hermes_health.active_failures()
    assert row["kind"] == "cron_job_error" and "nightly" in row["summary"]
    jobs._record_run_outcome(job, True, None, None, None, "2026-11-21T01:00:00")
    assert hermes_health.active_failures() == []


def test_doctor_lists_still_failing_conditions(capsys):
    from hermes_cli import doctor
    hermes_health.record("plugin_hook_failure", "k", "Hook 'pre_approval_request' raised PermissionError: EPERM")
    monkey_home = hermes_health.ledger_path().parent.parent
    old = doctor.HERMES_HOME
    doctor.HERMES_HOME = monkey_home
    try:
        finding = doctor._check_health_ledger(False)
    finally:
        doctor.HERMES_HOME = old
    out = capsys.readouterr().out
    assert "Still failing" in out and "pre_approval_request" in out
    assert finding.manual_issues
