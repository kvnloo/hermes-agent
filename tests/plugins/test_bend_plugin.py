"""Tests for the downstream Bend verification plugin."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from plugins.bend import register
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


def test_handler_returns_stable_error_code(monkeypatch):
    def fail(**kwargs):
        raise core.BendVerifyError("unsupported_bend", "old Bend")

    monkeypatch.setattr(tools, "verify", fail)
    result = json.loads(tools.handle_bend_verify({"project_dir": "/tmp/example"}))
    assert result == {"error": "old Bend", "code": "unsupported_bend"}
