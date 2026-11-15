"""``/model`` with no ``model.provider`` names the provider the resolver actually routes through (#136801).

``_ModelSwitchContext.read_config`` leaves ``current_provider`` on its ``openrouter`` placeholder when
config.yaml has no ``model.provider``. The listing used to show that placeholder, so a dry API-key
provider billing every turn ("Insufficient Balance") hid behind a route the gateway was not using.
Real config, real env key, real ``resolve_provider``: nothing patched but the home and the env.
"""

import asyncio
import os

import pytest


def _listing_first_line(home, config: str) -> str:
    from gateway.slash_commands_model import GatewayModelCommandsMixin, _ModelSwitchContext

    (home / "config.yaml").write_text(config, encoding="utf-8")

    class Host(GatewayModelCommandsMixin):
        def _delivery_adapter_for(self, source):
            return None  # no picker adapter: /model falls through to the text listing

    ctx = _ModelSwitchContext(session_key="s", source=None, config_path=home / "config.yaml", persist_global=False)
    ctx.read_config()
    reply = asyncio.run(Host()._model_listing_reply(None, ctx, None))
    return (reply or "").splitlines()[0]


@pytest.fixture
def deepseek_only_home(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    for key in [k for k in os.environ if k.endswith("_API_KEY")]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-real")
    return home


@pytest.mark.parametrize("provider_line", ["", "  provider: auto\n", "  provider: ''\n"])
def test_unset_provider_lists_the_route_the_resolver_picks(deepseek_only_home, provider_line):
    line = _listing_first_line(deepseek_only_home, f"model:\n{provider_line}  default: deepseek-v4-flash\n")
    assert line.lower() == "current: `deepseek-v4-flash` on deepseek", line


def test_env_requested_provider_is_named_over_auto_detect(deepseek_only_home, monkeypatch):
    """``HERMES_INFERENCE_PROVIDER`` picks the turn's provider even when another key would auto-detect."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-real")
    monkeypatch.setenv("HERMES_INFERENCE_PROVIDER", "deepseek")
    line = _listing_first_line(deepseek_only_home, "model:\n  default: deepseek-v4-flash\n")
    assert line.lower() == "current: `deepseek-v4-flash` on deepseek", line


def test_configured_provider_is_listed_as_configured(deepseek_only_home):
    line = _listing_first_line(deepseek_only_home, "model:\n  provider: anthropic\n  default: claude-x\n")
    assert line.lower() == "current: `claude-x` on anthropic", line


@pytest.mark.asyncio
async def test_listing_rehydrates_persisted_session_override_after_restart(tmp_path, monkeypatch):
    """First /model after restart must show the saved session route, not the config route."""
    from types import SimpleNamespace

    import gateway.run as gateway_run
    from gateway.config import GatewayConfig, Platform
    from gateway.platforms.event import MessageEvent, MessageType
    from gateway.run import GatewayRunner
    from gateway.session import SessionSource, SessionStore, build_session_key

    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text(
        "model:\n  default: config-model\n  provider: anthropic\n", encoding="utf-8")
    monkeypatch.setattr(gateway_run, "_hermes_home", home)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-real")

    source = SessionSource(platform=Platform.TELEGRAM, chat_id="chat", user_id="user", chat_type="dm")
    store = SessionStore(tmp_path / "sessions", GatewayConfig())
    key = store.get_or_create_session(source).session_key
    store.set_model_override(key, {"model": "deepseek-v4-flash", "provider": "deepseek"})

    # Gateway restart: persistence remains, but the in-memory override has not been hydrated.
    runner = object.__new__(GatewayRunner)
    runner.config = SimpleNamespace(multiplex_profiles=False)
    runner.session_store = store
    runner._session_model_overrides = {}
    runner._normalize_source_for_session_key = lambda src: src
    runner._session_key_for_source = lambda src: build_session_key(src)
    runner._serving_channel_config = lambda src: None
    runner._delivery_adapter_for = lambda src: None

    event = MessageEvent(text="/model", message_type=MessageType.TEXT, source=source)
    reply = await runner._handle_model_command(event)
    assert (reply or "").splitlines()[0].lower() == "current: `deepseek-v4-flash` on deepseek"
