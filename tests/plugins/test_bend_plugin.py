"""Tests for the downstream Bend verification plugin."""

from __future__ import annotations

import json
from types import SimpleNamespace

from plugins.bend import register
from plugins.bend import tools


def _proof(tmp_path):
    proof = tmp_path / "PROOF.bend"
    proof.write_text("# test proof\n")
    return proof


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


def test_bend_verify_uses_proven_kernel(monkeypatch, tmp_path):
    _proof(tmp_path)
    captured = {}

    monkeypatch.setattr(tools.shutil, "which", lambda name: "/usr/local/bin/bend")

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="ALL PROOFS CHECK\n", stderr="")

    monkeypatch.setattr(tools.subprocess, "run", fake_run)

    result = json.loads(tools.handle_bend_verify({"project_dir": str(tmp_path)}))

    assert result["success"] is True
    assert result["verdict"] == "pass"
    assert captured["command"] == ["/usr/local/bin/bend", "PROOF.bend", "--verdict"]
    assert captured["cwd"] == str(tmp_path.resolve())
    assert captured["env"]["BEND_NO_TELEMETRY"] == "1"
    assert captured["timeout"] == 30
    assert captured["check"] is False


def test_bend_verify_preserves_failure_evidence(monkeypatch, tmp_path):
    _proof(tmp_path)
    monkeypatch.setattr(tools.shutil, "which", lambda name: "/usr/local/bin/bend")
    monkeypatch.setattr(
        tools.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="SOME PROOFS FAIL\n",
        ),
    )

    result = json.loads(tools.handle_bend_verify({"project_dir": str(tmp_path)}))

    assert result["success"] is False
    assert result["verdict"] == "fail"
    assert result["exit_code"] == 1
    assert "SOME PROOFS FAIL" in result["stderr"]


def test_bend_verify_rejects_path_escape(tmp_path):
    _proof(tmp_path)

    result = json.loads(
        tools.handle_bend_verify(
            {"project_dir": str(tmp_path), "proof_file": "../PROOF.bend"}
        )
    )

    assert "error" in result
    assert "inside project_dir" in result["error"]
