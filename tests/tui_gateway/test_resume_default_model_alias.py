"""A TUI row saved before default-alias routing was fixed must resume on the alias host."""

from hermes_cli import runtime_provider as rp
from tui_gateway import server


def test_pre_fix_tui_default_alias_row_resumes_on_alias_route(monkeypatch):
    # The earlier TUI factory saved the literal config default and the provider that rejected it.
    config = {
        "model": {"default": "myalias", "provider": "openrouter"},
        "model_aliases": {"myalias": {
            "model": "some-vendor/some-model-id",
            "provider": "custom",
            "base_url": "http://127.0.0.1:9999/v1",
            "key_env": "DEMO_API_KEY",
        }},
    }
    for name in ("HERMES_MODEL", "HERMES_INFERENCE_MODEL", "HERMES_TUI_PROVIDER",
                 "HERMES_INFERENCE_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEMO_API_KEY", "sk-alias-host")
    monkeypatch.setattr(server, "_load_cfg", lambda: config)
    monkeypatch.setattr(rp, "load_config", lambda: config)
    monkeypatch.setattr(rp, "_get_model_config", lambda: config["model"])
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: config)

    legacy = {"model": "myalias", "model_config": {
        "model": "myalias", "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1", "api_mode": "chat_completions",
    }}
    overrides = server._stored_session_runtime_overrides(legacy)
    model, runtime = server._resolve_agent_model_runtime(
        overrides.get("model_override"), overrides.get("provider_override"))

    assert (model, runtime["provider"], runtime["base_url"], runtime["api_key"]) == (
        "some-vendor/some-model-id", "custom", "http://127.0.0.1:9999/v1", "sk-alias-host")

    # A row with a different explicitly selected provider is not a stale config-default route.
    explicit = {"model": "myalias", "model_config": {"model": "myalias", "provider": "anthropic"}}
    assert server._stored_session_runtime_overrides(explicit)["provider_override"] == "anthropic"
