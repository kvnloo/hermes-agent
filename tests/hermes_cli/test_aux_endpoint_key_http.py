"""Dashboard auxiliary endpoint key refuses managed .env writes visibly (#131016)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from hermes_cli.config import get_config_path
from hermes_cli.web_models import ModelAssignment
from hermes_cli.web_routers.models import set_model_assignment

SECRET = "sk-aux-MARKER-SECRET"


def test_auxiliary_dashboard_managed_env_refusal_returns_actionable_400(monkeypatch):
    from hermes_cli import config

    get_config_path().write_text("model:\n  provider: openrouter\n  default: x/y\n")
    monkeypatch.setattr(config, "env_write_refusal",
                        lambda key, action: f"Cannot {action} {key}: managed")

    assignment = ModelAssignment(
        scope="auxiliary", task="vision", provider="custom", model="",
        base_url="http://127.0.0.1:11434/v1", api_key=SECRET,
    )
    with pytest.raises(HTTPException) as refusal:
        asyncio.run(set_model_assignment(assignment))

    assert refusal.value.status_code == 400
    assert "HERMES_CUSTOM_AUX_VISION_" in refusal.value.detail
    assert "managed" in refusal.value.detail
    assert SECRET not in get_config_path().read_text()
