"""An OS-policy write denial (a sandbox refusing a write the file's mode allows) is named as such,
persisted past log deduplication, reported by ``hermes doctor``, and diffable before a rollout.

Motivating incident: hosts were moved under a macOS Seatbelt profile that denied
a user data directory. The approval plugin's hooks raised ``[Errno 1] Operation not permitted``
on a user-owned 0644 file; core logged it once and then only at DEBUG, so the broken plugin was
invisible, and agents retried the same denied write hundreds of times.
"""

import errno
import json
import logging
import os
import stat
from types import SimpleNamespace

import pytest

from hermes_cli import write_denials as wd
from hermes_cli.plugins import PluginManager

posix_only = pytest.mark.skipif(not hasattr(os, "getuid"), reason="classification reads POSIX ownership")


def _st(mode, uid, gid=0, flags=0):
    return SimpleNamespace(st_mode=mode, st_uid=uid, st_gid=gid, st_flags=flags)


def _stat_of(table):
    def fake(path):
        try:
            return table[str(path)]
        except KeyError:
            raise FileNotFoundError(errno.ENOENT, "missing", str(path)) from None
    return fake


@pytest.fixture(autouse=True)
def _fresh_memo():
    wd._last_persisted.clear()
    yield
    wd._last_persisted.clear()


@pytest.fixture()
def home(tmp_path, monkeypatch):
    h = tmp_path / "hermes_home"
    h.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(h))
    return h


@posix_only
def test_eperm_on_a_file_our_mode_bits_allow_is_an_os_policy_denial():
    exc = PermissionError(errno.EPERM, "Operation not permitted", "/u/asks/approvals.jsonl")
    table = {"/u/asks/approvals.jsonl": _st(stat.S_IFREG | 0o644, uid=501)}
    assert wd.classify_write_error(exc, stat_fn=_stat_of(table), uid=501, gids={20}) == wd.POLICY_DENIED


@posix_only
def test_a_file_owned_by_someone_else_is_a_plain_permission_denial():
    exc = PermissionError(errno.EACCES, "Permission denied", "/u/other.log")
    table = {"/u/other.log": _st(stat.S_IFREG | 0o644, uid=0, gid=0)}
    assert wd.classify_write_error(exc, stat_fn=_stat_of(table), uid=501, gids={20}) == wd.PERMISSION_DENIED


@posix_only
@pytest.mark.skipif(not getattr(stat, "UF_IMMUTABLE", 0), reason="no BSD file flags")
def test_an_immutable_flag_is_not_blamed_on_a_sandbox():
    exc = PermissionError(errno.EPERM, "Operation not permitted", "/u/locked")
    table = {"/u/locked": _st(stat.S_IFREG | 0o644, uid=501, flags=stat.UF_IMMUTABLE)}
    assert wd.classify_write_error(exc, stat_fn=_stat_of(table), uid=501, gids=set()) == wd.PERMISSION_DENIED


@posix_only
def test_a_file_not_yet_created_is_judged_by_its_parent_dir():
    exc = PermissionError(errno.EPERM, "Operation not permitted", "/u/asks/new.jsonl")
    table = {"/u/asks": _st(stat.S_IFDIR | 0o755, uid=501)}
    assert wd.classify_write_error(exc, stat_fn=_stat_of(table), uid=501, gids=set()) == wd.POLICY_DENIED


@posix_only
def test_chmod_eperm_on_our_own_dir_is_a_policy_denial():
    """bot_live_delivery's chmod(0o700) of a dir we own: POSIX never answers EPERM to the owner."""
    exc = PermissionError(errno.EPERM, "Operation not permitted", "/u/pc/runtime/bot_live_delivery")
    table = {"/u/pc/runtime/bot_live_delivery": _st(stat.S_IFDIR | 0o700, uid=501)}
    assert wd.classify_write_error(exc, stat_fn=_stat_of(table), uid=501, gids=set()) == wd.POLICY_DENIED


def test_non_write_errors_are_not_classified():
    assert wd.classify_write_error(FileNotFoundError(errno.ENOENT, "nope", "/x")) is None
    assert wd.classify_write_error(ValueError("x")) is None
    assert wd.classify_write_error(OSError(errno.EROFS, "Read-only file system", "/x")) == wd.READ_ONLY_FS


@posix_only
def test_a_denial_is_persisted_and_counted_across_processes(home, tmp_path):
    target = tmp_path / "asks" / "approvals.jsonl"
    target.parent.mkdir()
    target.write_text("")
    exc = PermissionError(errno.EPERM, "Operation not permitted", str(target))
    assert wd.record_write_denial(exc, source="hook pre_approval_request", now=1000.0) == wd.POLICY_DENIED
    # Within the throttle window a repeat is classified but not rewritten.
    assert wd.record_write_denial(exc, source="hook pre_approval_request", now=1010.0) == wd.POLICY_DENIED
    wd._last_persisted.clear()  # a new process
    wd.record_write_denial(exc, source="hook pre_approval_request", now=2000.0)
    rows = wd.load_write_denials()
    assert len(rows) == 1
    row = rows[0]
    assert row["path"] == str(target) and row["kind"] == wd.POLICY_DENIED
    assert row["count"] == 2 and row["first_seen"] == 1000.0 and row["last_seen"] == 2000.0
    assert (home / "state" / "write_denials.json").is_file()


def test_recording_never_raises_when_the_store_is_unwritable(home, monkeypatch):
    def boom(*a, **k):
        raise PermissionError(errno.EPERM, "Operation not permitted", str(home / "state"))
    monkeypatch.setattr(wd, "_write_store", boom)
    exc = OSError(errno.EROFS, "Read-only file system", "/x")
    assert wd.record_write_denial(exc, source="t") == wd.READ_ONLY_FS


@posix_only
def test_an_os_denied_hook_write_stays_visible_after_the_log_dedupes_it(home, tmp_path, caplog):
    """Before: one WARNING, then DEBUG forever, and nothing persistent. After: the WARNING names a
    capability blocker and every occurrence lands in the store doctor reads."""
    ledger = tmp_path / "asks" / "approvals.jsonl"
    ledger.parent.mkdir()
    ledger.write_text("")  # our file, mode allows writes: only a policy layer can refuse it

    def on_request(**kwargs):
        raise PermissionError(errno.EPERM, "Operation not permitted", str(ledger))

    manager = PluginManager()
    manager._hooks.setdefault("pre_approval_request", []).append(on_request)
    with caplog.at_level(logging.DEBUG, logger="hermes_cli.plugins"):
        for i in range(4):
            wd._last_persisted.clear()  # each call as if far apart in time
            manager.invoke_hook("pre_approval_request", command=f"rm x{i}", session_id="s")

    warnings = [r.getMessage() for r in caplog.records
                if r.levelno == logging.WARNING and "on_request" in r.getMessage()]
    assert len(warnings) == 1
    assert "capability blocker" in warnings[0] and "hermes doctor" in warnings[0]
    rows = wd.load_write_denials()
    assert [r["path"] for r in rows] == [str(ledger)]
    assert rows[0]["count"] == 4
    assert "pre_approval_request" in rows[0]["source"]


def test_a_non_os_hook_failure_keeps_the_old_message(home, caplog):
    def on_request(tool_data):
        return None

    manager = PluginManager()
    manager._hooks.setdefault("pre_approval_request", []).append(on_request)
    with caplog.at_level(logging.WARNING, logger="hermes_cli.plugins"):
        manager.invoke_hook("pre_approval_request", command="x")
    assert any("identical failures are logged at DEBUG" in r.getMessage() for r in caplog.records)
    assert wd.load_write_denials() == []


@posix_only
def test_doctor_fails_a_still_denied_path_and_forgets_a_repaired_one(home, tmp_path, monkeypatch, capsys):
    from hermes_cli.doctor_state import _check_write_denials

    fixed, walled = tmp_path / "fixed", tmp_path / "walled"
    fixed.mkdir()
    walled.mkdir()
    for p in (fixed, walled):
        wd.record_write_denial(PermissionError(errno.EPERM, "Operation not permitted", str(p)), source="hook h")
    real_probe = wd.probe_write_access
    monkeypatch.setattr(wd, "probe_write_access",
                        lambda p: (False, wd.POLICY_DENIED, "denied") if str(p) == str(walled) else real_probe(p))

    finding = _check_write_denials(True)
    out = capsys.readouterr().out
    assert "Write Denials Seen at Runtime" in out
    assert any(str(walled) in issue and "sandbox profile" in issue for issue in finding.manual_issues)
    assert not any(str(fixed) in issue for issue in finding.manual_issues)
    assert [r["path"] for r in wd.load_write_denials()] == [str(walled)]


def test_doctor_is_silent_with_no_recorded_denials(home, capsys):
    from hermes_cli.doctor_state import _check_write_denials
    finding = _check_write_denials(False)
    assert capsys.readouterr().out == "" and not finding.manual_issues


def test_preflight_reports_what_a_candidate_policy_would_break(tmp_path):
    ok_dir, ledger_dir = tmp_path / "sandbox", tmp_path / "asks"
    ok_dir.mkdir()
    ledger_dir.mkdir()
    seen = {}

    def runner(argv):
        seen["argv"] = argv
        rows = [{"path": str(ok_dir), "ok": True, "kind": None, "detail": ""},
                {"path": str(ledger_dir), "ok": False, "kind": wd.POLICY_DENIED, "detail": "Operation not permitted"}]
        return SimpleNamespace(stdout=json.dumps(rows), returncode=0)

    rows = wd.preflight_write_paths([str(ok_dir), str(ledger_dir)], ["sandbox-exec", "-f", "agents.sb"],
                                    runner=runner)
    assert seen["argv"][:3] == ["sandbox-exec", "-f", "agents.sb"] and "probe" in seen["argv"]
    assert {r["path"]: r["breaks"] for r in rows} == {str(ok_dir): False, str(ledger_dir): True}


def test_preflight_treats_a_wrapper_that_died_as_breaking_everything(tmp_path):
    rows = wd.preflight_write_paths([str(tmp_path)], ["false"],
                                    runner=lambda argv: SimpleNamespace(stdout="", returncode=137))
    assert rows[0]["breaks"] and "exit 137" in rows[0]["wrapped"]["detail"]


def test_probe_module_runs_standalone(tmp_path):
    """The wrapped probe runs the file with ``python -I``: it must not need the Hermes package."""
    import subprocess
    import sys
    proc = subprocess.run([sys.executable, "-I", wd.__file__, "probe", str(tmp_path)],
                          capture_output=True, text=True, timeout=60, cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)[0]["ok"] is True
