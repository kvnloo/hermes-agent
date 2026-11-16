"""Tests for the downstream Bend verification plugin."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from plugins.bend import register
from plugins.bend import session_kernel as session
from plugins.bend import tools
from plugins.bend import verify_core as core


def _proof(tmp_path, name="PROOF.bend", text="# test proof\n"):
    proof = tmp_path / name
    proof.write_text(text)
    return proof


def _laws(tmp_path, text="import Base\n\nlaw ok:\n  {0n == 0n : Nat}\n"):
    laws = tmp_path / "LAWS.bend"
    laws.write_text(text)
    return laws


def _runner(verdict, *, version="2.0.34", mutate=None, inspect=None):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[-1] == "version":
            return SimpleNamespace(returncode=0, stdout=f"bend {version}\n", stderr="")
        if inspect is not None:
            inspect(command, kwargs)
        if mutate is not None:
            mutate()
        return verdict

    return run, calls


def test_registers_one_bend_verify_tool():
    seen = {}

    class Ctx:
        def register_tool(self, **kwargs):
            seen.update(kwargs)

    register(Ctx())
    assert seen["name"] == "bend_verify"
    assert seen["toolset"] == "bend"
    assert seen["handler"] is tools.handle_bend_verify
    assert seen["check_fn"] is tools.check_bend_available


def test_core_verifies_private_snapshot_and_sanitizes_trust_overrides(tmp_path):
    _proof(tmp_path)
    _laws(tmp_path)
    observed = {}

    def inspect(_command, kwargs):
        snapshot = Path(kwargs["cwd"])
        observed["cwd"] = snapshot
        observed["proof"] = (snapshot / "PROOF.bend").read_text()
        observed["laws"] = (snapshot / "LAWS.bend").read_text()
        observed["env"] = kwargs["env"]

    runner, calls = _runner(
        SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr=""),
        inspect=inspect,
    )
    result = core.verify(
        str(tmp_path),
        which=lambda _: "/usr/local/bin/bend",
        runner=runner,
        source_env={
            "BENDTT": "/tmp/forged-kernel",
            "BEND_HUB": "https://evil.invalid",
            "BEND_LIB": "/tmp/evil-lib",
            "BEND_ORIGIN": "https://evil.invalid",
            "UNRELATED": "keep",
        },
    )

    assert result["success"] is True
    assert result["verdict"] == "pass"
    assert result["cache_mode"] == "isolated"
    assert result["input_file_count"] == 2
    assert observed["cwd"] != tmp_path
    assert observed["proof"] == (tmp_path / "PROOF.bend").read_text()
    assert observed["laws"] == (tmp_path / "LAWS.bend").read_text()
    assert calls[1][0] == ["/usr/local/bin/bend", "PROOF.bend", "--verdict"]
    env = observed["env"]
    assert env["BEND_NO_TELEMETRY"] == "1"
    assert env["UNRELATED"] == "keep"
    assert env["BEND_LIB"] != "/tmp/evil-lib"
    for key in ("BENDTT", "BEND_HUB", "BEND_ORIGIN"):
        assert key not in env


def test_adjacent_laws_is_snapshotted_even_if_proof_does_not_import_it(tmp_path):
    _proof(tmp_path, text="import Base\n")
    _laws(tmp_path)
    seen = {}

    def inspect(_command, kwargs):
        seen["laws"] = (Path(kwargs["cwd"]) / "LAWS.bend").exists()

    runner, _ = _runner(
        SimpleNamespace(returncode=1, stdout="", stderr="SOME PROOFS FAIL\n"),
        inspect=inspect,
    )
    core.verify(str(tmp_path), which=lambda _: "/bin/bend", runner=runner)
    assert seen["laws"] is True


def test_zero_exit_with_forged_marker_substring_is_indeterminate(tmp_path):
    _proof(tmp_path)
    runner, _ = _runner(SimpleNamespace(returncode=0, stdout="NOT ALL PROOFS CHECK\n", stderr=""))
    result = core.verify(str(tmp_path), which=lambda _: "/bin/bend", runner=runner)
    assert result["success"] is False
    assert result["verdict"] == "indeterminate"


def test_nonzero_preserves_failure_evidence(tmp_path):
    _proof(tmp_path)
    runner, _ = _runner(SimpleNamespace(returncode=1, stdout="", stderr="SOME PROOFS FAIL\n"))
    result = core.verify(str(tmp_path), which=lambda _: "/bin/bend", runner=runner)
    assert result["verdict"] == "fail"
    assert result["exit_code"] == 1


def test_rejects_path_escape(tmp_path):
    _proof(tmp_path)
    with pytest.raises(core.BendVerifyError, match="inside project_dir"):
        core.resolve_proof(str(tmp_path), "../PROOF.bend")


def test_rejects_noncanonical_proof_basename(tmp_path):
    _proof(tmp_path, "proof.bend")
    with pytest.raises(core.BendVerifyError, match="named PROOF.bend"):
        core.resolve_proof(str(tmp_path), "proof.bend")


def test_allows_nested_canonical_proof(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    _proof(nested)
    project, proof, relative = core.resolve_proof(str(tmp_path), "nested/PROOF.bend")
    assert project == tmp_path.resolve()
    assert proof == nested / "PROOF.bend"
    assert relative.as_posix() == "nested/PROOF.bend"


def test_requires_current_verdict_semantics(tmp_path):
    _proof(tmp_path)
    runner, _ = _runner(
        SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr=""),
        version="2.0.31",
    )
    with pytest.raises(core.BendVerifyError) as caught:
        core.verify(str(tmp_path), which=lambda _: "/bin/bend", runner=runner)
    assert caught.value.code == "unsupported_bend"


def test_timeout_is_structured(tmp_path):
    _proof(tmp_path)

    def runner(command, **kwargs):
        if command[-1] == "version":
            return SimpleNamespace(returncode=0, stdout="bend 2.0.34\n", stderr="")
        raise core.subprocess.TimeoutExpired(command, 30, output=b"partial", stderr=b"slow")

    result = core.verify(str(tmp_path), which=lambda _: "/bin/bend", runner=runner)
    assert result["verdict"] == "timeout"
    assert result["stdout"] == "partial"
    assert result["stderr"] == "slow"


def test_detects_proof_mutation_during_verification(tmp_path):
    proof = _proof(tmp_path, text="# before\n")
    runner, _ = _runner(
        SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr=""),
        mutate=lambda: proof.write_text("# after\n"),
    )
    result = core.verify(str(tmp_path), which=lambda _: "/bin/bend", runner=runner)
    assert result["success"] is False
    assert result["verdict"] == "unstable"
    assert result["execution_verdict"] == "pass"
    assert result["proof_changed_during_verify"] is True
    assert result["source_changed_during_verify"] is True


def test_detects_laws_mutation_and_never_reports_snapshot_pass_as_current(tmp_path):
    _proof(tmp_path, text="import Base\nimport ./LAWS.bend as Laws\n")
    laws = _laws(tmp_path, text="import Base\n\nlaw ok:\n  {0n == 0n : Nat}\n")
    runner, _ = _runner(
        SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr=""),
        mutate=lambda: laws.write_text("import Base\n\nlaw ok:\n  {0n == 1n : Nat}\n"),
    )
    result = core.verify(str(tmp_path), which=lambda _: "/bin/bend", runner=runner)
    assert result["success"] is False
    assert result["verdict"] == "unstable"
    assert result["proof_changed_during_verify"] is False
    assert result["source_changed_during_verify"] is True


def test_import_closure_manifest_tracks_imported_helper_not_unrelated_file(tmp_path):
    helper = tmp_path / "HELPER.bend"
    helper.write_text("import Base\n")
    _proof(tmp_path, text="import Base\nimport ./HELPER.bend as H\n")
    unrelated = tmp_path / "UNRELATED.bend"
    unrelated.write_text("import Base\n")

    project, proof, _ = core.resolve_proof(str(tmp_path))
    first = core.capture_local_inputs(project, proof)
    assert set(first["files"]) == {"PROOF.bend", "HELPER.bend"}

    unrelated.write_text("# changed\n")
    second = core.capture_local_inputs(project, proof)
    assert second["manifest_sha256"] == first["manifest_sha256"]

    helper.write_text("import Base\n# changed\n")
    third = core.capture_local_inputs(project, proof)
    assert third["manifest_sha256"] != first["manifest_sha256"]


def test_rejects_absolute_local_import_for_snapshot_integrity(tmp_path):
    outside = tmp_path.parent / "outside.bend"
    outside.write_text("import Base\n")
    _proof(tmp_path, text=f"import Base\nimport {outside} as O\n")
    project, proof, _ = core.resolve_proof(str(tmp_path))
    with pytest.raises(core.BendVerifyError) as caught:
        core.capture_local_inputs(project, proof)
    assert caught.value.code == "unsupported_import"


def test_cold_kernel_uses_bootstrap_timeout(tmp_path):
    _proof(tmp_path)
    fake_root = tmp_path / "bend-dist"
    fake_bin = fake_root / "bin" / "bend"
    fake_src = fake_root / "bend2" / "bendtt.lean"
    fake_bin.parent.mkdir(parents=True)
    fake_src.parent.mkdir(parents=True)
    fake_bin.write_text("# fake bend\n")
    fake_src.write_text("-- fake kernel source\n")
    seen = {}

    def runner(command, **kwargs):
        if command[-1] == "version":
            return SimpleNamespace(returncode=0, stdout="bend 2.0.34\n", stderr="")
        seen["timeout"] = kwargs["timeout"]
        return SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr="")

    result = core.verify(
        str(tmp_path),
        which=lambda _: str(fake_bin),
        runner=runner,
        source_env={"HOME": str(tmp_path / "home")},
    )
    assert result["kernel_cache_state"] == "cold"
    assert result["verdict_timeout_seconds"] == core._KERNEL_BOOTSTRAP_TIMEOUT_SECONDS
    assert seen["timeout"] == core._KERNEL_BOOTSTRAP_TIMEOUT_SECONDS


def test_warm_kernel_keeps_proof_timeout(tmp_path):
    _proof(tmp_path)
    fake_root = tmp_path / "bend-dist"
    fake_bin = fake_root / "bin" / "bend"
    fake_src = fake_root / "bend2" / "bendtt.lean"
    fake_bin.parent.mkdir(parents=True)
    fake_src.parent.mkdir(parents=True)
    fake_bin.write_text("# fake bend\n")
    fake_src.write_text("-- fake kernel source\n")

    home = tmp_path / "home"
    key = core.sha256_bytes(fake_src.read_bytes())[:16]
    kernel = home / ".bend" / "bendtt" / key / "bendtt"
    kernel.parent.mkdir(parents=True)
    kernel.write_text("# cached kernel\n")
    seen = {}

    def runner(command, **kwargs):
        if command[-1] == "version":
            return SimpleNamespace(returncode=0, stdout="bend 2.0.34\n", stderr="")
        seen["timeout"] = kwargs["timeout"]
        return SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr="")

    result = core.verify(
        str(tmp_path),
        which=lambda _: str(fake_bin),
        runner=runner,
        source_env={"HOME": str(home)},
    )
    assert result["kernel_cache_state"] == "warm"
    assert result["kernel_sha256_before"] == core.sha256_file(kernel)
    assert result["verdict_timeout_seconds"] == core._TIMEOUT_SECONDS
    assert seen["timeout"] == core._TIMEOUT_SECONDS


def test_pinned_kernel_is_injected_only_after_hash_check(tmp_path):
    _proof(tmp_path)
    kernel = tmp_path / "bendtt"
    kernel.write_text("# pinned kernel\n")
    expected = core.sha256_file(kernel)
    seen = {}

    def runner(command, **kwargs):
        if command[-1] == "version":
            return SimpleNamespace(returncode=0, stdout="bend 2.0.34\n", stderr="")
        seen["bendtt"] = kwargs["env"].get("BENDTT")
        return SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr="")

    result = core.verify(
        str(tmp_path),
        which=lambda _: "/bin/bend",
        runner=runner,
        kernel_override=str(kernel),
        kernel_expected_sha256=expected,
    )
    assert result["success"] is True
    assert result["kernel_cache_state"] == "pinned"
    assert result["kernel_sha256_before"] == expected
    assert seen["bendtt"] == str(kernel.resolve())


def test_pinned_kernel_hash_mismatch_fails_before_verdict(tmp_path):
    _proof(tmp_path)
    kernel = tmp_path / "bendtt"
    kernel.write_text("# mutated kernel\n")

    with pytest.raises(core.BendVerifyError) as caught:
        core.verify(
            str(tmp_path),
            which=lambda _: "/bin/bend",
            runner=lambda *args, **kwargs: SimpleNamespace(
                returncode=0, stdout="bend 2.0.34\n", stderr=""
            ),
            kernel_override=str(kernel),
            kernel_expected_sha256="0" * 64,
        )
    assert caught.value.code == "kernel_integrity"


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX-specific")
def test_run_process_timeout_reaps_process_group(monkeypatch):
    events = []

    class FakeProcess:
        pid = 4242
        returncode = -15

        def __init__(self):
            self.calls = 0

        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise core.subprocess.TimeoutExpired(["bend"], timeout)
            return ("partial-out", "partial-err")

    fake = FakeProcess()

    def fake_popen(*args, **kwargs):
        events.append(("popen", kwargs.get("start_new_session")))
        return fake

    monkeypatch.setattr(core.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        core.os,
        "killpg",
        lambda pid, sig: events.append(("killpg", pid, sig)),
    )

    with pytest.raises(core.subprocess.TimeoutExpired) as caught:
        core.run_process(["bend", "PROOF.bend", "--verdict"], timeout=0.01)

    assert ("popen", True) in events
    assert ("killpg", 4242, core.signal.SIGTERM) in events
    assert caught.value.output == "partial-out"
    assert caught.value.stderr == "partial-err"


def test_run_process_non_posix_uses_subprocess_run(monkeypatch):
    """The Windows path never touches POSIX-only process-group signals."""
    expected = core.subprocess.CompletedProcess(["bend"], 0, "ok", "")
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return expected

    def unexpected_popen(*_args, **_kwargs):
        pytest.fail("non-POSIX must not start a POSIX process group")

    monkeypatch.setattr(core, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core.subprocess, "Popen", unexpected_popen)

    actual = core.run_process(
        ["bend", "PROOF.bend", "--verdict"],
        cwd="fake-workdir",
        env={"BEND_NO_TELEMETRY": "1"},
        timeout=0.01,
    )
    assert actual is expected
    assert calls == [
        (
            ["bend", "PROOF.bend", "--verdict"],
            {
                "cwd": "fake-workdir",
                "env": {"BEND_NO_TELEMETRY": "1"},
                "capture_output": True,
                "text": True,
                "timeout": 0.01,
                "check": False,
            },
        )
    ]


def test_detects_bend_binary_mutation_during_verdict(tmp_path):
    _proof(tmp_path)
    fake_root = tmp_path / "bend-dist"
    fake_bin = fake_root / "bin" / "bend"
    fake_src = fake_root / "bend2" / "bendtt.lean"
    fake_bin.parent.mkdir(parents=True)
    fake_src.parent.mkdir(parents=True)
    fake_bin.write_text("# bend before\n")
    fake_src.write_text("-- fake kernel source\n")

    def runner(command, **kwargs):
        if command[-1] == "version":
            return SimpleNamespace(returncode=0, stdout="bend 2.0.34\n", stderr="")
        fake_bin.write_text("# bend after\n")
        return SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr="")

    result = core.verify(
        str(tmp_path),
        which=lambda _: str(fake_bin),
        runner=runner,
        source_env={"HOME": str(tmp_path / "home")},
    )
    assert result["execution_verdict"] == "pass"
    assert result["verdict"] == "unstable"
    assert result["success"] is False
    assert result["bend_changed_during_verify"] is True
    assert result["bend_sha256_after"] != result["bend_sha256"]


def test_session_kernel_bootstraps_once_then_pins(monkeypatch):
    session._reset_session_kernel_for_tests()
    calls = []

    monkeypatch.setattr(session, "_current_bend", lambda: ("/opt/bend/bin/bend", "bend-sha"))
    monkeypatch.setattr(
        session,
        "kernel_cache_identity",
        lambda bend, env: {
            "state": "warm",
            "path": "/private/session/bendtt",
            "source_sha256": "source-sha",
            "sha256": "kernel-sha",
        },
    )
    monkeypatch.setattr(
        session,
        "file_identity_sha256",
        lambda path: "kernel-sha" if path == "/private/session/bendtt" else "bend-sha",
    )

    def fake_verify(project_dir, proof_file="PROOF.bend", **kwargs):
        calls.append(kwargs)
        return {
            "success": True,
            "verdict": "pass",
            "execution_verdict": "pass",
        }

    monkeypatch.setattr(session, "verify", fake_verify)
    first = session.verify_with_session_kernel("/project")
    second = session.verify_with_session_kernel("/project")

    assert first["kernel_strategy"] == "session-bootstrap"
    assert second["kernel_strategy"] == "session-pinned"
    assert "kernel_override" not in calls[0]
    assert calls[1]["kernel_override"] == "/private/session/bendtt"
    assert calls[1]["kernel_expected_sha256"] == "kernel-sha"
    session._reset_session_kernel_for_tests()


def test_session_kernel_tamper_fails_closed(monkeypatch):
    session._reset_session_kernel_for_tests()
    current_kernel_sha = {"value": "kernel-sha"}

    monkeypatch.setattr(session, "_current_bend", lambda: ("/opt/bend/bin/bend", "bend-sha"))
    monkeypatch.setattr(
        session,
        "kernel_cache_identity",
        lambda bend, env: {
            "state": "warm",
            "path": "/private/session/bendtt",
            "source_sha256": "source-sha",
            "sha256": "kernel-sha",
        },
    )
    monkeypatch.setattr(
        session,
        "file_identity_sha256",
        lambda path: current_kernel_sha["value"]
        if path == "/private/session/bendtt"
        else "bend-sha",
    )
    monkeypatch.setattr(
        session,
        "verify",
        lambda *args, **kwargs: {
            "success": True,
            "verdict": "pass",
            "execution_verdict": "pass",
        },
    )

    session.verify_with_session_kernel("/project")
    current_kernel_sha["value"] = "mutated"
    with pytest.raises(core.BendVerifyError) as caught:
        session.verify_with_session_kernel("/project")
    assert caught.value.code == "kernel_integrity"
    session._reset_session_kernel_for_tests()


def test_session_refuses_bend_binary_swap_after_bootstrap(monkeypatch):
    session._reset_session_kernel_for_tests()
    bend_sha = {"value": "bend-sha"}

    monkeypatch.setattr(
        session,
        "_current_bend",
        lambda: ("/opt/bend/bin/bend", bend_sha["value"]),
    )
    monkeypatch.setattr(
        session,
        "kernel_cache_identity",
        lambda bend, env: {
            "state": "warm",
            "path": "/private/session/bendtt",
            "source_sha256": "source-sha",
            "sha256": "kernel-sha",
        },
    )
    monkeypatch.setattr(
        session,
        "file_identity_sha256",
        lambda path: "kernel-sha" if path == "/private/session/bendtt" else bend_sha["value"],
    )
    monkeypatch.setattr(
        session,
        "verify",
        lambda *args, **kwargs: {
            "success": True,
            "verdict": "pass",
            "execution_verdict": "pass",
        },
    )

    session.verify_with_session_kernel("/project")
    bend_sha["value"] = "replacement-sha"
    with pytest.raises(core.BendVerifyError) as caught:
        session.verify_with_session_kernel("/project")
    assert caught.value.code == "bend_integrity"
    session._reset_session_kernel_for_tests()


@pytest.fixture
def fake_bend_cli(tmp_path, monkeypatch):
    """Local protocol double. Adapter I/O, hashing and kernel execution stay real."""
    root = tmp_path / "bend-dist"
    binary = root / "bin" / "bend"
    source = root / "bend2" / "bendtt.lean"
    binary.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    source.write_text("-- test kernel source\n")
    kernel_script = (
        '#!/bin/sh\nif [ "$1" = valid ]; then\n'
        'echo ALL PROOFS CHECK\nelse\necho SOME PROOFS FAIL >&2\nexit 1\nfi\n'
    )
    binary.write_text(
        f"#!{sys.executable}\n"
        "import hashlib, os, pathlib, subprocess, sys\n"
        "if sys.argv[1:] == ['version']:\n"
        "    print('bend 2.0.34')\n"
        "    sys.exit(0)\n"
        "assert sys.argv[2:] == ['--verdict']\n"
        "assert os.environ['BEND_NO_TELEMETRY'] == '1'\n"
        "assert pathlib.Path(os.environ['BEND_LIB']).is_dir()\n"
        "if 'BENDTT' in os.environ:\n"
        "    kernel = pathlib.Path(os.environ['BENDTT'])\n"
        "else:\n"
        "    source = pathlib.Path(__file__).parents[1] / 'bend2' / 'bendtt.lean'\n"
        "    key = hashlib.sha256(source.read_bytes()).hexdigest()[:16]\n"
        "    kernel = pathlib.Path.home() / '.bend' / 'bendtt' / key / 'bendtt'\n"
        "    if not kernel.exists():\n"
        "        kernel.parent.mkdir(parents=True, exist_ok=True)\n"
        f"        kernel.write_text({kernel_script!r})\n"
        "        kernel.chmod(0o755)\n"
        "proof = pathlib.Path(sys.argv[1]).read_text()\n"
        "case = 'gap' if 'def B(' in proof else 'valid'\n"
        "sys.exit(subprocess.run([str(kernel), case]).returncode)\n"
    )
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(binary.parent) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return binary


@pytest.mark.platforms("posix")
@pytest.mark.parametrize("repeats,attacks", [(1, 1), (2, 2)])
def test_kernel_strategy_rejects_tampering_with_real_subprocesses(
    fake_bend_cli, tmp_path, monkeypatch, repeats, attacks
):
    from evals import bend_adapter_kernel_strategies as strategies

    output = tmp_path / "strategies.json"
    monkeypatch.setattr(sys, "argv", [
        "bend-kernel-strategies", "--repeats", str(repeats),
        "--attacks", str(attacks), "--output", str(output),
    ])
    assert strategies.main() == 0
    payload = json.loads(output.read_text())
    shared = payload["summary"]["shared_cache"]
    pinned = payload["summary"]["session_pinned"]
    assert shared["baseline_gap"] == "fail"
    assert shared["forged_passes"] == attacks
    assert pinned["runs"] == repeats * 2
    assert pinned["mismatch_count"] == 0
    assert pinned["shared_cache_forged_passes"] == 0
    assert pinned["private_mutation_rejections"] == attacks
    assert {row["case"]: row["verdict"] for row in payload["pinned_records"]} == {
        "valid": "pass", "gap": "fail",
    }


@pytest.mark.platforms("posix")
def test_registered_tool_verifies_with_session_kernel_end_to_end(fake_bend_cli, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _proof(project)
    registered = {}
    register(SimpleNamespace(register_tool=lambda **kwargs: registered.update(kwargs)))
    session._reset_session_kernel_for_tests()
    try:
        assert registered["check_fn"]() is True
        first = json.loads(registered["handler"]({"project_dir": str(project)}))
        assert first["success"] is True
        assert first["kernel_strategy"] == "session-bootstrap"
        _proof(project, text="def B(): # rejected by the fake kernel\n")
        second = json.loads(registered["handler"]({"project_dir": str(project)}))
        assert second["success"] is False
        assert second["verdict"] == "fail"
        assert second["kernel_strategy"] == "session-pinned"
        assert second["session_kernel_sha256"] == first["session_kernel_sha256"]
    finally:
        session._reset_session_kernel_for_tests()


def test_handler_returns_stable_error_code(monkeypatch):
    def fail(**kwargs):
        raise core.BendVerifyError("unsupported_bend", "old Bend")

    monkeypatch.setattr(tools, "verify_with_session_kernel", fail)
    result = json.loads(tools.handle_bend_verify({"project_dir": "/tmp/example"}))
    assert result == {"error": "old Bend", "code": "unsupported_bend"}
