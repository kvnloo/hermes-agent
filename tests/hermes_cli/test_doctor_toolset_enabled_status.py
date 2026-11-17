"""Regression for doctor displaying installed-but-disabled CLI toolsets."""

import sys
import types
from argparse import Namespace

import pytest

from hermes_cli import doctor
from hermes_cli import tools_config


def test_run_doctor_warns_when_available_toolset_is_disabled(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    hermes_home = tmp_path / "hermes-home"
    project_root.mkdir()
    hermes_home.mkdir()

    monkeypatch.setattr(doctor, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(doctor, "HERMES_HOME", hermes_home)
    monkeypatch.setattr(doctor, "_check_gateway_service_linger", lambda _issues: None)
    monkeypatch.setattr(
        doctor,
        "_apply_doctor_tool_availability_overrides",
        lambda available, unavailable: (available, unavailable),
    )
    monkeypatch.setenv("TERMINAL_ENV", "local")
    for key in (
        "OPENROUTER_API_KEY",
        "ANTHROPIC_TOKEN",
        "ANTHROPIC_API_KEY",
        "GLM_API_KEY",
        "ZAI_API_KEY",
        "Z_AI_API_KEY",
        "KIMI_API_KEY",
        "MINIMAX_API_KEY",
        "MINIMAX_CN_API_KEY",
        "AI_GATEWAY_API_KEY",
        "KILOCODE_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    fake_model_tools = types.ModuleType("model_tools")
    fake_model_tools.check_tool_availability = lambda: (["moa", "web"], [])
    fake_model_tools.TOOLSET_REQUIREMENTS = {
        "moa": {"name": "Mixture of Agents"},
        "web": {"name": "Web Search"},
    }
    monkeypatch.setitem(sys.modules, "model_tools", fake_model_tools)

    monkeypatch.setattr(tools_config, "load_config", lambda: {})
    platforms = []

    def enabled_cli_toolsets(_config, platform):
        platforms.append(platform)
        return {"web"}

    monkeypatch.setattr(tools_config, "_get_platform_tools", enabled_cli_toolsets)

    statuses = []

    def record_ok(label, detail=""):
        statuses.append(("ok", label, detail))
        if label == "Web Search":
            # Stop after the target section rather than running later checks.
            raise SystemExit(0)

    def record_warn(label, detail=""):
        statuses.append(("warn", label, detail))

    monkeypatch.setattr(doctor, "check_ok", record_ok)
    monkeypatch.setattr(doctor, "check_warn", record_warn)

    with pytest.raises(SystemExit):
        doctor.run_doctor(Namespace(fix=False))

    assert platforms == ["cli"]
    assert (
        "warn",
        "Mixture of Agents",
        "(requirements met, but disabled — enable with: hermes tools enable moa)",
    ) in statuses
    assert ("ok", "Web Search", "") in statuses
