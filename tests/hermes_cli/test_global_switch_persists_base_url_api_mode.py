"""Regression tests for #25106: CLI `/model <name> --global` never persisted
``model.base_url``/``model.api_mode`` to config.yaml, so a global provider
switch left the PREVIOUS provider's endpoint/wire-protocol on disk. The next
`hermes` launch re-read the stale base_url and routed the new model at the
old host.

This regression drives the typed ``_handle_model_switch`` path against an isolated config file.
It verifies that ``--global`` writes the resolved model route while preserving unrelated model
and platform data.
"""

import hermes_yaml as yaml

from hermes_cli.model_switch import ModelSwitchResult


def _make_result(*, base_url="https://api.minimax.io/v1", api_mode="chat_completions", provider_changed=True):
    return ModelSwitchResult(
        success=True,
        new_model="MiniMax-M3",
        target_provider="custom:minimax",
        provider_changed=provider_changed,
        api_key="sk-minimax",
        base_url=base_url,
        api_mode=api_mode,
        warning_message="",
        provider_label="MiniMax (custom)",
        resolved_via_alias=False,
        capabilities=None,
        model_info=None,
        is_global=True,
    )


class _StubCLI:
    """Minimum attrs/methods `_handle_model_switch` reads or calls on self."""
    def _stage_and_swap_model(self, result, old_model):
        # Staging + in-place swap lives in a helper; run the real one on this stub.
        import cli as _cli_mod
        return _cli_mod.HermesCLI._stage_and_swap_model(self, result, old_model)


    agent = None
    model = "old-model"
    provider = "copilot"
    requested_provider = "copilot"
    api_key = "sk-old"
    base_url = "https://api.githubcopilot.com"
    api_mode = "chat_completions"
    _explicit_api_key = ""
    _explicit_base_url = ""
    conversation_history = []
    _pending_model_switch_note = ""

    def _confirm_expensive_model_switch(self, result, precomputed_warning=None) -> bool:
        return True


    def _open_model_picker(self, *a, **k):
        raise AssertionError("picker should not open when a model name is given")


def _write_config(monkeypatch, tmp_path):
    import hermes_cli.config as config

    config_path = tmp_path / "config.yaml"
    initial = {
        "model": {
            "default": "old-model",
            "provider": "copilot",
            "base_url": "https://api.githubcopilot.com",
            "api_mode": "chat_completions",
            "model_slots": {"preferred": "old-model"},
        },
        "platforms": {"telegram": {"enabled": True}},
    }
    config_path.write_text(yaml.safe_dump(initial), encoding="utf-8")
    monkeypatch.setattr(config, "get_config_path", lambda: config_path)
    return config_path, initial


def test_global_switch_persists_base_url_and_api_mode(monkeypatch, tmp_path):
    """A successful --global switch updates the isolated config without losing sibling data."""
    config_path, _ = _write_config(monkeypatch, tmp_path)
    monkeypatch.setattr("cli._cprint", lambda *a, **k: None)
    monkeypatch.setattr("hermes_cli.model_switch.switch_model", lambda **kw: _make_result())
    monkeypatch.setattr("hermes_cli.model_switch.resolve_display_context_length", lambda *a, **k: None)

    import cli as cli_mod
    cli_mod.HermesCLI._handle_model_switch(_StubCLI(), "/model MiniMax-M3 --global")

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved["model"]["default"] == "MiniMax-M3"
    assert saved["model"]["provider"] == "custom:minimax"
    assert saved["model"]["base_url"] == "https://api.minimax.io/v1"
    assert saved["model"]["api_mode"] == "chat_completions"
    assert saved["model"]["model_slots"] == {"preferred": "old-model"}
    assert saved["platforms"]["telegram"]["enabled"] is True


def test_session_only_switch_does_not_touch_config(monkeypatch, tmp_path):
    """--session leaves the isolated config file unchanged."""
    import cli as cli_mod

    config_path, initial = _write_config(monkeypatch, tmp_path)
    monkeypatch.setattr(cli_mod, "_cprint", lambda *a, **k: None)
    monkeypatch.setattr("hermes_cli.model_switch.switch_model", lambda **kw: _make_result())
    monkeypatch.setattr("hermes_cli.model_switch.resolve_display_context_length", lambda *a, **k: None)
    cli_mod.HermesCLI._handle_model_switch(_StubCLI(), "/model MiniMax-M3 --session")

    assert yaml.safe_load(config_path.read_text(encoding="utf-8")) == initial

