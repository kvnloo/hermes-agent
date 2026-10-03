"""Local dependency closure and conservative public proof-result admission."""
from __future__ import annotations

import json

import pytest

from plugins.bend import tools
from plugins.bend import verify_core as core


@pytest.mark.parametrize("statement", [
    "import 0xdeadbeef/Proof as P",
    "import 0xdeadbeef/Proof.bend as P",
    "import package@1.0.0.0/Proof as P",
    "import package@1.0.0.0/Proof.bend as P",
    "import https://example.invalid/Proof.bend as P",
    "import file:///tmp/Proof.bend as P",
    "import 0xdeadbeef/Proof",
    "import package@1.0.0.0/Proof",
    "import ./HELPER.bend",
    "import ./HELPER.txt as H",
    "import ./HELPER.bend as H trailing",
    "import Base as B",
    "import",
])
def test_unsupported_import_is_refused_before_any_cli_call(tmp_path, statement):
    (tmp_path / "PROOF.bend").write_text(f"import Base\n{statement}\n")
    calls = []

    def which(name):
        calls.append(name)
        return "/not-executed/bend"

    def runner(*args, **kwargs):
        calls.append(args)
        pytest.fail("unsupported input must not reach the Bend CLI")

    with pytest.raises(core.BendVerifyError) as caught:
        core.verify(str(tmp_path), which=which, runner=runner)
    assert caught.value.code == "unsupported_import"
    assert calls == []


@pytest.mark.parametrize("dependency", ["HELPER.bend", "LAWS.bend"])
def test_remote_import_in_transitive_or_adjacent_input_is_refused(tmp_path, dependency):
    text = "import Base\n"
    if dependency == "HELPER.bend":
        text += "import ./HELPER.bend as H\n"
    (tmp_path / "PROOF.bend").write_text(text)
    (tmp_path / dependency).write_text("import 0xdeadbeef/Proof as P\n")
    with pytest.raises(core.BendVerifyError) as caught:
        core.capture_local_inputs(tmp_path, tmp_path / "PROOF.bend")
    assert caught.value.code == "unsupported_import"


def test_local_closure_keeps_base_comments_aliases_and_cycles(tmp_path):
    (tmp_path / "PROOF.bend").write_text(
        "# imports\n\nimport Base\nimport ./HELPER.bend as H # local\n"
    )
    (tmp_path / "HELPER.bend").write_text("import ./PROOF.bend as P\n")
    captured = core.capture_local_inputs(tmp_path, tmp_path / "PROOF.bend")
    assert set(captured["files"]) == {"PROOF.bend", "HELPER.bend"}
    assert captured["file_count"] == 2


def test_import_prefix_stops_at_a_non_keyword_identifier():
    assert core._local_imports("import Base\nimportant = 1\n") == []


@pytest.mark.parametrize("version", ["2.0.32", "2.0.33", "2.0.34", "99.0.0"])
def test_handler_never_promotes_raw_pass_by_version_alone(monkeypatch, version):
    original = {
        "success": True,
        "verdict": "pass",
        "execution_verdict": "pass",
        "bend_version": version,
        "bend_sha256": "a" * 64,
        "kernel_sha256_before": "b" * 64,
        "kernel_sha256_after": "b" * 64,
        "input_manifest_sha256": "c" * 64,
    }
    monkeypatch.setattr(tools, "verify_with_session_kernel", lambda **kwargs: original)
    result = json.loads(tools.handle_bend_verify({"project_dir": "/test-only"}))
    assert result["success"] is False
    assert result["verdict"] == "unqualified"
    assert result["code"] == "unqualified_bend_release"
    assert result["qualified"] is False
    assert result["qualification_status"] == "pending_release_qualification"
    assert result["execution_verdict"] == "pass"
    for key in ("bend_version", "bend_sha256", "kernel_sha256_before",
                "kernel_sha256_after", "input_manifest_sha256"):
        assert result[key] == original[key]
    assert original["success"] is True  # Raw experiment evidence was not mutated.
    assert "qualified" not in original


@pytest.mark.parametrize("verdict", ["fail", "timeout", "unstable", "indeterminate"])
def test_handler_preserves_nonpassing_evidence(monkeypatch, verdict):
    original = {
        "success": False,
        "verdict": verdict,
        "execution_verdict": "pass" if verdict == "unstable" else verdict,
        "stderr": "diagnostic evidence",
    }
    monkeypatch.setattr(tools, "verify_with_session_kernel", lambda **kwargs: original)
    result = json.loads(tools.handle_bend_verify({"project_dir": "/test-only"}))
    for key, value in original.items():
        assert result[key] == value
    assert result["qualified"] is False


def test_tool_arguments_and_environment_cannot_override_qualification(monkeypatch):
    seen = []

    def raw_verify(**kwargs):
        seen.append(kwargs)
        return {"success": True, "verdict": "pass", "execution_verdict": "pass",
                "qualified": True, "qualification_status": "approved"}

    monkeypatch.setattr(tools, "verify_with_session_kernel", raw_verify)
    monkeypatch.setenv("BEND_QUALIFIED", "true")
    result = json.loads(tools.handle_bend_verify({
        "project_dir": "/test-only", "qualified": True, "allow_unqualified": True,
    }))
    assert seen == [{"project_dir": "/test-only", "proof_file": "PROOF.bend"}]
    assert result["success"] is False
    assert result["qualified"] is False
    assert result["qualification_status"] == "pending_release_qualification"


def test_tool_import_error_keeps_the_machine_readable_refusal(monkeypatch):
    def refused(**kwargs):
        raise core.BendVerifyError("unsupported_import", "local inputs only")

    monkeypatch.setattr(tools, "verify_with_session_kernel", refused)
    result = json.loads(tools.handle_bend_verify({"project_dir": "/test-only"}))
    assert result == {"error": "local inputs only", "code": "unsupported_import"}
