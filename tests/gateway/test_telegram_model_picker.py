"""Tests for Telegram model picker thread fallback."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from gateway.config import PlatformConfig
from plugins.platforms.telegram.adapter import TelegramAdapter


def _make_adapter():
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="test-token"))
    adapter._bot = AsyncMock()
    adapter._app = MagicMock()
    return adapter


class TestTelegramModelPicker:
    @pytest.mark.asyncio
    async def test_send_model_picker_escapes_dynamic_provider_label(self):
        adapter = _make_adapter()
        sent = {}

        async def mock_send_message(**kwargs):
            sent.update(kwargs)
            return SimpleNamespace(message_id=101)

        adapter._bot.send_message = AsyncMock(side_effect=mock_send_message)

        result = await adapter.send_model_picker(
            chat_id="12345",
            providers=[
                {"slug": "provider_one", "name": "Provider One", "total_models": 1, "is_current": True}
            ],
            current_model="model_1",
            current_provider="provider_one",
            session_key="s",
            on_model_selected=AsyncMock(),
            metadata={"thread_id": "99999"},
        )

        assert result.success is True
        assert "MARKDOWN_V2" in repr(sent["parse_mode"])
        assert "provider\\_one" in sent["text"]
        assert "`model_1`" in sent["text"]

    @pytest.mark.asyncio
    async def test_back_button_escapes_dynamic_provider_label(self):
        adapter = _make_adapter()
        adapter._model_picker_state["12345"] = {
            "providers": [{"slug": "provider_one", "name": "Provider One", "total_models": 1, "is_current": True}],
            "current_model": "model_1",
            "current_provider": "provider_one",
            "session_key": "s",
            "on_model_selected": AsyncMock(),
            "msg_id": 42,
        }

        query = AsyncMock()
        query.data = "mb"
        query.message = MagicMock()
        query.message.chat_id = 12345
        query.from_user = MagicMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        await adapter._handle_model_picker_callback(query, "mb", "12345")

        edit_kwargs = query.edit_message_text.call_args[1]
        assert "MARKDOWN_V2" in repr(edit_kwargs["parse_mode"])
        assert "provider\\_one" in edit_kwargs["text"]
        assert "`model_1`" in edit_kwargs["text"]


def _gateway_wired_runner_adapter():
    """Real gateway/adapter wiring; callback authorization remains on its production path."""
    from gateway.config import GatewayConfig, Platform
    from gateway.pairing import PairingStore
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig()
    runner.config.platforms = {Platform.TELEGRAM: PlatformConfig(enabled=True, extra={})}
    runner.pairing_store = PairingStore(profile="default")
    runner.pairing_stores = {"default": runner.pairing_store}
    runner._primary_profile_name = "default"
    runner._voice_mode = {}
    runner._session_model_overrides = {}
    runner._running_agents = {}
    adapter = _make_adapter()
    runner.adapters = {Platform.TELEGRAM: adapter}
    adapter.set_authorization_check(runner._make_adapter_auth_check(Platform.TELEGRAM))
    return runner, adapter


def _gateway_wired_adapter():
    return _gateway_wired_runner_adapter()[1]

@pytest.mark.asyncio
@pytest.mark.parametrize("tapper_id, switches", [("222", False), ("111", True)])
async def test_group_model_picker_switch_follows_callback_allowlist(monkeypatch, tapper_id, switches):
    """Only an allowlisted tapper can switch the model from a group /model picker."""
    for key in ("GATEWAY_ALLOW_ALL_USERS", "GATEWAY_ALLOWED_USERS", "TELEGRAM_ALLOW_ALL_USERS",
                "TELEGRAM_GROUP_ALLOWED_USERS", "TELEGRAM_GROUP_ALLOWED_CHATS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "111")
    import hermes_cli.model_selection_guards as guards
    monkeypatch.setattr(guards, "combined_selection_warning", lambda *a, **k: None)

    adapter = _gateway_wired_adapter()
    on_model_selected = AsyncMock(return_value="Switched to `other-model`")
    adapter._model_picker_state["-100777"] = {
        "providers": [{"slug": "openai", "name": "OpenAI", "total_models": 1}],
        "current_model": "owner-model",
        "current_provider": "openai",
        "session_key": "s",
        "on_model_selected": on_model_selected,
        "selected_provider": "openai",
        "model_list": ["other-model"],
        "msg_id": 42,
    }
    query = SimpleNamespace(
        data="mm:0",
        message=SimpleNamespace(
            chat_id=-100777, chat=SimpleNamespace(type="supergroup"), message_thread_id=None
        ),
        from_user=SimpleNamespace(id=int(tapper_id), first_name="Tapper"),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )

    await adapter._handle_callback_query(SimpleNamespace(callback_query=query), MagicMock())

    assert on_model_selected.await_count == (1 if switches else 0)
    assert ("-100777" in adapter._model_picker_state) is not switches


@pytest.mark.asyncio
async def test_registered_guard_failure_keeps_real_picker_and_gateway_route(tmp_path, monkeypatch):
    """A guard fault reports a recoverable error and preserves the existing gateway session route."""
    from gateway.config import Platform
    from gateway.platforms.event import MessageEvent, MessageType
    from gateway.session import SessionSource
    from hermes_cli.model_switch import ModelSwitchResult

    for key in (
        "GATEWAY_ALLOW_ALL_USERS", "GATEWAY_ALLOWED_USERS", "TELEGRAM_ALLOW_ALL_USERS",
        "TELEGRAM_GROUP_ALLOWED_USERS", "TELEGRAM_GROUP_ALLOWED_CHATS",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "111")

    home = tmp_path / ".hermes"
    home.mkdir()
    config_path = home / "config.yaml"
    config_path.write_text(
        "model:\n  default: old-model\n  provider: openrouter\nproviders: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr("gateway.run._hermes_home", home)
    monkeypatch.setattr("hermes_constants.get_hermes_home", lambda: home)
    monkeypatch.setattr("hermes_cli.config.get_hermes_home", lambda: home)
    monkeypatch.setattr(
        "hermes_cli.model_switch_providers.list_picker_providers",
        lambda **_kwargs: [{
            "slug": "anthropic", "name": "Anthropic", "models": ["guard-fault-model"],
            "total_models": 1, "is_current": False,
        }],
    )
    monkeypatch.setattr(
        "hermes_cli.model_switch.switch_model",
        lambda **kwargs: ModelSwitchResult(
            success=True, new_model=kwargs["raw_input"],
            target_provider=kwargs["explicit_provider"], provider_label="Anthropic",
        ),
    )
    monkeypatch.setattr(
        "hermes_cli.context_switch_guard.enrich_model_switch_warnings_for_gateway",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr("gateway.code_skew.detect_code_skew", lambda: None)
    failures = []

    def _broken_metadata(provider, model):
        failures.append((provider, model))
        raise RuntimeError("registered guard metadata failure")

    monkeypatch.setattr("agent.models_dev.get_model_info", _broken_metadata)

    runner, adapter = _gateway_wired_runner_adapter()
    runner._session_db = None
    runner._record_switch_metrics = lambda *_args, **_kwargs: None
    runner._evict_cached_agent = lambda *_args, **_kwargs: None
    runner._model_switch_confirmation = AsyncMock(return_value="switched")
    adapter._bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=42))
    source = SessionSource(platform=Platform.TELEGRAM, chat_id="111", chat_type="dm")
    event = MessageEvent(text="/model", message_type=MessageType.TEXT, source=source)
    old_override = {"model": "old-model", "provider": "openrouter"}
    session_key = runner._session_key_for_source(source)
    runner._session_model_overrides[session_key] = old_override.copy()
    before_overrides = {session_key: old_override.copy()}

    assert await runner._handle_model_command(event) is None
    state = adapter._model_picker_state["111"]
    query = SimpleNamespace(
        data="mp:anthropic",
        message=SimpleNamespace(chat_id=111, chat=SimpleNamespace(type="private"), message_thread_id=None),
        from_user=SimpleNamespace(id=111, first_name="Owner"),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    await adapter._handle_callback_query(SimpleNamespace(callback_query=query), MagicMock())
    query.answer.reset_mock()
    query.edit_message_text.reset_mock()
    query.data = "mm:0"
    before = config_path.read_bytes()

    await adapter._handle_callback_query(SimpleNamespace(callback_query=query), MagicMock())

    alert = query.answer.await_args.kwargs
    assert alert["show_alert"] is True
    assert "no change was made" in alert["text"].lower()
    assert "please try again" in alert["text"].lower()
    assert query.edit_message_text.await_count == 0
    assert failures == [("anthropic", "guard-fault-model")]
    assert adapter._model_picker_state["111"] is state
    assert state["current_model"] == "old-model"
    assert runner._session_model_overrides == before_overrides
    assert config_path.read_bytes() == before
