"""Regression tests for the Discord /model picker.

Uses the shared discord mock from tests/gateway/conftest.py (installed
at collection time via _ensure_discord_mock()). Previously this file
installed its own mock at module-import time and clobbered sys.modules,
breaking other gateway tests in the same process.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.platforms.base import utf16_len
from plugins.platforms.discord.adapter import ModelPickerView


@pytest.mark.asyncio
async def test_model_picker_clears_controls_before_running_switch_callback():
    events: list[object] = []

    async def on_model_selected(chat_id: str, model_id: str, provider_slug: str) -> str:
        events.append(("switch", chat_id, model_id, provider_slug))
        return "Model switched"

    async def edit_message(**kwargs):
        events.append(
            (
                "initial-edit",
                kwargs["embed"].title,
                kwargs["embed"].description,
                kwargs["view"],
            )
        )

    async def edit_original_response(**kwargs):
        events.append((
            "final-edit",
            kwargs["embed"].title,
            kwargs["embed"].description,
            kwargs["view"],
        ))

    view = ModelPickerView(
        providers=[
            {
                "slug": "copilot",
                "name": "GitHub Copilot",
                "models": ["gpt-5.4"],
                "total_models": 1,
                "is_current": True,
            }
        ],
        current_model="gpt-5-mini",
        current_provider="copilot",
        session_key="session-1",
        on_model_selected=on_model_selected,
        allowed_user_ids={"123"},  # matches the interaction user; empty = fail-closed
    )
    view._selected_provider = "copilot"

    interaction = SimpleNamespace(
        user=SimpleNamespace(id=123),
        channel_id=456,
        data={"values": ["gpt-5.4"]},
        response=SimpleNamespace(
            defer=AsyncMock(),
            send_message=AsyncMock(),
            edit_message=AsyncMock(side_effect=edit_message),
        ),
        edit_original_response=AsyncMock(side_effect=edit_original_response),
    )

    await view._on_model_selected(interaction)

    assert events == [
        ("initial-edit", "⚙ Switching Model", "Switching to `gpt-5.4`...", None),
        ("switch", "456", "gpt-5.4", "copilot"),
        ("final-edit", "⚙ Model Switched", "Model switched", None),
    ]
    interaction.response.edit_message.assert_awaited_once()
    interaction.response.defer.assert_not_called()
    interaction.edit_original_response.assert_awaited_once()




@pytest.mark.asyncio
async def test_model_picker_refuses_registered_guard_failure_without_changing_runtime_state(monkeypatch):
    raw_config = b"model:\n  default: old/model\n  provider: openai\n"
    session = {"model_override": {"model": "old/model", "provider": "openai"}}
    state = {"config": raw_config, "session": session}
    before = {"config": raw_config, "session": {"model_override": session["model_override"].copy()}}

    async def on_model_selected(_chat_id: str, model_id: str, provider_slug: str) -> str:
        state["config"] = f"model: {model_id}\nprovider: {provider_slug}\n".encode()
        session["model_override"]["model"] = model_id
        session["model_override"]["provider"] = provider_slug
        return "Model switched"

    def broken_local_metadata(provider, model):
        raise RuntimeError("registered guard metadata failure")

    monkeypatch.setattr("agent.models_dev.get_model_info", broken_local_metadata)
    view = ModelPickerView(
        providers=[{
            "slug": "openai",
            "name": "OpenAI",
            "models": ["gpt-5-pro"],
            "total_models": 1,
            "is_current": True,
        }],
        current_model="old/model",
        current_provider="openai",
        session_key="session-1",
        on_model_selected=on_model_selected,
        allowed_user_ids={"123"},
    )
    view._selected_provider = "openai"
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=123),
        channel_id=456,
        data={"values": ["gpt-5-pro"]},
        response=SimpleNamespace(
            defer=AsyncMock(),
            send_message=AsyncMock(),
            edit_message=AsyncMock(),
        ),
        edit_original_response=AsyncMock(),
    )

    await view._on_model_selected(interaction)

    assert state == before
    assert view.resolved is False
    error_embed = interaction.response.edit_message.await_args.kwargs["embed"]
    assert "registered guard metadata failure" in error_embed.description
    interaction.response.send_message.assert_not_awaited()
    interaction.edit_original_response.assert_not_awaited()
