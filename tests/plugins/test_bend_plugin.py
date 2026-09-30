"""Tests for the downstream Bend verification plugin."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from plugins.bend import register
from plugins.bend import tools
from plugins.bend import verify_core as core


def _proof(tmp_path, name="PROOF.bend", text="# test proof\n"):
    proof = tmp_path / name
    proof.write_text(text)
    return proof


def _runner(verdict, *, version="2.0.34", mutate=None):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[-1] == "version":
            return SimpleNamespace(returncode=0, stdout=f"bend {version}\n", stderr="")
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


def test_core_uses_proven_kernel_and_sanitizes_trust_overrides(tmp_path):
    _proof(tmp_path)
    runner, calls = _runner(SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr=""))
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
    assert result["bend_version"] == "2.0.34"
    assert calls[1][0] == ["/usr/local/bin/bend", "PROOF.bend", "--verdict"]
    env = calls[1][1]["env"]
    assert env["BEND_NO_TELEMETRY"] == "1"
    assert env["UNRELATED"] == "keep"
    for key in core._BEND_ENV_DENY:
        assert key not in env


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
    assert result["success"] is False
    assert result["verdict"] == "fail"
    assert result["exit_code"] == 1
    assert "SOME PROOFS FAIL" in result["stderr"]


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
    assert proof == (nested / "PROOF.bend").resolve()
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
    assert ">= 2.0.32" in str(caught.value)


def test_timeout_is_structured(tmp_path):
    _proof(tmp_path)

    def runner(command, **kwargs):
        if command[-1] == "version":
            return SimpleNamespace(returncode=0, stdout="bend 2.0.34\n", stderr="")
        raise core.subprocess.TimeoutExpired(command, 30, output=b"partial", stderr=b"slow")

    result = core.verify(str(tmp_path), which=lambda _: "/bin/bend", runner=runner)
    assert result["verdict"] == "timeout"
    assert result["success"] is False
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
    assert result["proof_changed_during_verify"] is True


def test_handler_returns_stable_error_code(monkeypatch):
    def fail(**kwargs):
        raise core.BendVerifyError("unsupported_bend", "old Bend")

    monkeypatch.setattr(tools, "verify", fail)
    result = json.loads(tools.handle_bend_verify({"project_dir": "/tmp/example"}))
    assert result == {"error": "old Bend", "code": "unsupported_bend"}
