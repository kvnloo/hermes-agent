"""Tests for terminal truncation spill + metadata (deferred retrieval)."""

import json
import os
from pathlib import Path

import pytest

from tools.terminal_tool import terminal_tool


@pytest.fixture
def small_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    from hermes_constants import hermes_home_key
    import tools.tool_output_limits as lim
    monkeypatch.setattr(lim, "_cached_limits", {hermes_home_key(): {
        "max_bytes": 2000, "max_lines": 2000, "max_line_length": 2000,
    }})
    return tmp_path


class TestTruncationSpill:
    @pytest.mark.platforms("linux")
    def test_truncated_output_has_metadata_and_spill(self, small_cap):
        r = json.loads(terminal_tool(
            "python3 -c \"print('marker_head'); [print(f'row_{i}', 'x'*80) for i in range(200)]; print('marker_tail')\"",
            task_id="t-spill-1"))
        assert r["exit_code"] == 0
        assert "OUTPUT TRUNCATED" in r["output"]
        assert r["output_total_chars"] > 2000
        p = Path(r["full_output_path"])
        assert p.exists()
        full = p.read_text()
        assert "marker_head" in full and "marker_tail" in full
        # The spill contains rows that were cut from the visible window.
        assert "row_100 " in full
        assert "read_file" in r["truncation_note"]

    def test_small_output_has_no_metadata(self, small_cap):
        r = json.loads(terminal_tool("echo tiny", task_id="t-spill-2"))
        assert r["exit_code"] == 0
        assert "full_output_path" not in r
        assert "output_total_chars" not in r

    @pytest.mark.platforms("linux")
    def test_spill_is_redacted(self, small_cap):
        r = json.loads(terminal_tool(
            "python3 -c \"print('sk-proj-' + 'a1B2c3D4e5F6g7H8i9J0' * 3); [print('pad', 'y'*90) for i in range(200)]\"",
            task_id="t-spill-3"))
        p = Path(r["full_output_path"])
        full = p.read_text()
        assert "a1B2c3D4e5F6g7H8i9J0a1B2c3D4e5F6g7H8i9J0" not in full

    def test_old_spills_cleaned(self, small_cap, tmp_path):
        spill_dir = tmp_path / ".hermes" / "cache" / "terminal-output"
        spill_dir.mkdir(parents=True, exist_ok=True)
        stale = spill_dir / "out-1-2-dead.log"
        stale.write_text("old")
        os.utime(stale, (1, 1))
        json.loads(terminal_tool(
            "python3 -c \"[print('z'*90) for i in range(200)]\"", task_id="t-spill-4"))
        assert not stale.exists()

    @pytest.mark.platforms("linux")
    def test_failed_command_still_gets_spill(self, small_cap):
        r = json.loads(terminal_tool(
            "python3 -c \"[print('e'*90) for i in range(200)]; import sys; sys.exit(3)\"",
            task_id="t-spill-5"))
        assert r["exit_code"] == 3
        assert Path(r["full_output_path"]).exists()


def test_ssh_spill_path_resolves_to_synced_remote_file(tmp_path, monkeypatch):
    """Regression for #154749: SSH read_file needs a synced, SSH-visible path."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("TERMINAL_ENV", "ssh")

    from types import SimpleNamespace

    from tools.environments.base_output import _finalize_wait_result, _new_output_collector
    from tools.environments.file_sync import FileSyncManager, iter_sync_files
    from tools.terminal_tool_result import _redact_spill_file
    from tools.tool_output_limits import get_max_bytes

    # Exercise the real default capture limit, not a lowered test limit.
    row = "safe terminal output row\n"
    output = "start\n" + row * (get_max_bytes() // len(row) + 2) + "end\n"
    # The SSH backend already synced at startup; a fresh spill must bypass
    # the five-second normal sync throttle before the next read_file call.
    uploaded = {}
    remote_home = tmp_path / "remote-home"
    remote_home.mkdir()

    def upload(staged, remote):
        uploaded[remote] = Path(staged).read_text(encoding="utf-8")
        remote_path = remote_home / Path(remote).relative_to("/home/remote")
        remote_path.parent.mkdir(parents=True, exist_ok=True)
        remote_path.write_text(uploaded[remote], encoding="utf-8")

    sync_manager = FileSyncManager(
        get_files_fn=lambda: iter_sync_files("/home/remote/.hermes"),
        upload_fn=upload,
        delete_fn=lambda _: None,
    )
    sync_manager.sync(force=True)

    collector = _new_output_collector(object(), bounded_capture=True)
    collector.append(output)
    result = _finalize_wait_result(collector, collector.render(), 0)
    host_path = Path(result["full_output_path"])
    def execute(command, timeout=None):
        import subprocess
        result = subprocess.run(
            ["bash", "-c", command], capture_output=True, text=True,
            env={**os.environ, "HOME": str(remote_home)}, timeout=timeout, check=False,
        )
        return {"returncode": result.returncode}

    env = SimpleNamespace(_sync_manager=sync_manager, execute=execute)
    fields = dict(
        _redact_spill_file(str(host_path), result["output_total_chars"], "echo safe", env=env)
    )

    remote_rel = f"cache/terminal-output/{host_path.name}"
    visible = f"~/.hermes/{remote_rel}"
    assert fields["full_output_path"] == visible
    assert visible in fields["truncation_note"]
    assert host_path.read_text(encoding="utf-8") == output
    assert uploaded[f"/home/remote/.hermes/{remote_rel}"] == output
    assert (str(host_path), f"/home/remote/.hermes/{remote_rel}") in iter_sync_files(
        "/home/remote/.hermes"
    )

@pytest.mark.platforms("posix")
def test_ssh_spill_does_not_advertise_a_failed_upload(tmp_path, monkeypatch):
    """A swallowed SCP error must not produce a dead read_file path (#154749)."""
    from types import SimpleNamespace

    from tools.environments.file_sync import FileSyncManager
    from tools.terminal_tool_result import _redact_spill_file
    from tools.tool_output_limits import get_max_bytes

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("TERMINAL_ENV", "ssh")
    host_path = tmp_path / ".hermes" / "cache" / "terminal-output" / "out-failed.log"
    host_path.parent.mkdir(parents=True)
    row = "safe output row\n"
    content = row * (get_max_bytes() // len(row) + 2)
    host_path.write_text(content, encoding="utf-8")
    upload_calls = []

    def fail_upload(staged, remote):
        upload_calls.append((staged, remote))
        raise OSError("SCP upload rejected")

    manager = FileSyncManager(
        get_files_fn=lambda: [
            (str(host_path), "/home/remote/.hermes/cache/terminal-output/out-failed.log"),
        ],
        upload_fn=fail_upload,
        delete_fn=lambda _: None,
    )
    env = SimpleNamespace(
        _sync_manager=manager,
        execute=lambda command, timeout=None: {"returncode": 1},
    )
    fields = dict(_redact_spill_file(str(host_path), len(content), "echo safe", env=env))

    assert upload_calls  # FileSyncManager logs/rolls back the upload error instead of raising.
    assert host_path.is_file()  # Keep the redacted host archive and the terminal head/tail.
    assert "full_output_path" not in fields
    assert "truncation_note" not in fields
