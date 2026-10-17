from types import SimpleNamespace

from hermes_cli.model_switch import ModelSwitchResult


def _bound(fn, instance):
    return fn.__get__(instance, type(instance))


def test_prompt_toolkit_model_picker_defers_confirmation_off_key_handler(monkeypatch):
    import cli as cli_mod

    result = ModelSwitchResult(
        success=True,
        new_model="openai/gpt-5.5-pro",
        target_provider="nous",
    )
    monkeypatch.setattr(
        "hermes_cli.model_switch.switch_model",
        lambda **_kwargs: result,
    )

    captured = {}

    class _Thread:
        def __init__(self, *, target, args, daemon):
            captured["target"] = target
            captured["args"] = args
            captured["daemon"] = daemon

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(cli_mod.threading, "Thread", _Thread)

    self_ = SimpleNamespace(
        _app=object(),
        _model_picker_state={
            "stage": "model",
            "provider_data": {"slug": "nous"},
            "model_list": ["openai/gpt-5.5-pro"],
            "selected": 0,
            "user_provs": None,
            "custom_provs": None,
        },
        provider="nous",
        model="openai/gpt-5.5",
        base_url="",
        api_key="",
        _restore_modal_input_snapshot=lambda: None,
        _invalidate=lambda **_kwargs: None,
    )
    self_._close_model_picker = _bound(cli_mod.HermesCLI._close_model_picker, self_)
    self_._commit_picker_result = _bound(cli_mod.HermesCLI._commit_picker_result, self_)
    self_._confirm_and_apply_model_switch_result = (
        lambda *_args: captured.setdefault("ran_inline", True)
    )

    # The key handler now resolves persistence via resolve_persist_behavior,
    # which defaults to True (persist-by-default). Simulate that call.
    _bound(cli_mod.HermesCLI._handle_model_picker_selection, self_)(persist_global=True)

    # Picking a model opens the reasoning-effort step (no commit yet); "Keep current effort"
    # (the last effort row) commits with the historical arity.
    from hermes_cli.cli_model_switch_mixin import _picker_reasoning_rows
    assert self_._model_picker_state["stage"] == "reasoning"
    assert "started" not in captured
    self_._model_picker_state["selected"] = len(_picker_reasoning_rows()) - 1
    _bound(cli_mod.HermesCLI._handle_model_picker_selection, self_)(persist_global=True)

    assert self_._model_picker_state is None
    assert captured["started"] is True
    assert captured["daemon"] is True
    # Third arg is the fresh picker custom_providers snapshot (None here).
    assert captured["args"] == (result, True, None)
    assert "ran_inline" not in captured

def test_picker_guard_failure_without_mutating_runtime_or_config(
    monkeypatch, tmp_path,
):
    import cli as cli_mod

    config_path = tmp_path / "config.yaml"
    original_config = "model:\n  default: old-model\n  provider: anthropic\n"
    config_path.write_text(original_config, encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(cli_mod, "_hermes_home", tmp_path)

    def _fail_model_metadata(_provider, _model):
        raise RuntimeError("registered model metadata unavailable")

    monkeypatch.setattr("agent.models_dev.get_model_info", _fail_model_metadata)
    rendered = []
    monkeypatch.setattr(cli_mod, "_cprint", rendered.append)

    agent_calls = []
    agent = SimpleNamespace(
        model="old-model",
        context_compressor=None,
        session_prompt_tokens=0,
    )

    def _switch_model(**kwargs):
        agent_calls.append(kwargs)
        agent.model = kwargs["new_model"]

    agent.switch_model = _switch_model
    self_ = SimpleNamespace(
        model="old-model",
        provider="anthropic",
        requested_provider="anthropic",
        api_key="",
        base_url="",
        agent=agent,
    )
    self_._confirm_expensive_model_switch = _bound(
        cli_mod.HermesCLI._confirm_expensive_model_switch, self_)
    result = ModelSwitchResult(
        success=True, new_model="new-model", target_provider="anthropic", is_global=True,
    )

    _bound(cli_mod.HermesCLI._confirm_and_apply_model_switch_result, self_)(result, True)
    assert self_.model == "old-model"
    assert self_.provider == "anthropic"
    assert agent.model == "old-model"
    assert agent_calls == []
    assert config_path.read_text(encoding="utf-8") == original_config
    assert len(rendered) == 1
    assert all(rendered)
    assert all("cancelled" not in message.lower() for message in rendered)


def _seed_openrouter_price_cache(monkeypatch):
    import time

    import agent.models_dev as models_dev

    cache = {
        "openrouter": {
            "name": "OpenRouter",
            "env": ["OPENROUTER_API_KEY"],
            "api": "https://openrouter.ai/api/v1",
            "models": {
                "openai/gpt-5.5-pro": {"cost": {"input": 50.0, "output": 200.0}},
            },
        },
    }
    monkeypatch.setattr(models_dev, "_models_dev_cache", cache)
    monkeypatch.setattr(models_dev, "_models_dev_cache_time", time.time())
    reads = []

    def _fetch_models_dev(force_refresh=False, *, allow_network=True):
        reads.append(allow_network)
        if allow_network:
            raise AssertionError("selection guard attempted a models.dev refresh")
        return cache

    monkeypatch.setattr(models_dev, "fetch_models_dev", _fetch_models_dev)
    return reads


def test_typed_cli_switch_confirms_from_local_guard_before_switch_seam(monkeypatch):
    import cli as cli_mod

    import hermes_cli.model_switch as model_switch
    from hermes_cli.model_switch import DirectAlias, ModelSwitchResult
    import hermes_cli.cli_model_switch_mixin as switch_mixin

    def _blocked_before_consent(*_args, **_kwargs):
        raise AssertionError("switch validation or capabilities ran before consent")

    monkeypatch.setattr("hermes_cli.models_validate.validate_requested_model", _blocked_before_consent)
    monkeypatch.setattr(model_switch, "get_model_capabilities", _blocked_before_consent)
    monkeypatch.setattr(model_switch, "get_model_info", _blocked_before_consent)

    metadata_reads = _seed_openrouter_price_cache(monkeypatch)
    monkeypatch.setattr(model_switch, "DIRECT_ALIASES", {
        "known-pro": DirectAlias(
            model="openai/gpt-5.5-pro", provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
        ),
    })
    monkeypatch.setattr(model_switch, "_ensure_direct_aliases", lambda: None)
    context = SimpleNamespace(
        user_providers=None, custom_providers=None,
        with_overrides=lambda **_kwargs: context,
    )
    monkeypatch.setattr("hermes_cli.inventory.load_picker_context", lambda: context)

    events = []
    cli = SimpleNamespace(
        model="old-model", provider="anthropic", requested_provider="anthropic",
        api_key="sk-old", base_url="https://api.anthropic.com", agent=None, _app=None,
        _prompt_text_input_modal=lambda **kwargs: (events.append(("prompt", kwargs)) or "once"),
        _normalize_slash_confirm_choice=lambda raw, _choices: raw,
    )
    cli._confirm_expensive_model_switch = _bound(
        cli_mod.HermesCLI._confirm_expensive_model_switch, cli)
    cli._confirm_and_switch_cli_model = _bound(
        cli_mod.HermesCLI._confirm_and_switch_cli_model, cli)

    def _switch_model(**kwargs):
        assert events and events[-1][0] == "prompt"
        events.append(("switch", kwargs))
        return ModelSwitchResult(
            success=True, new_model="openai/gpt-5.5-pro", target_provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
        )

    def _commit(target, result, **_kwargs):
        events.append(("commit", result.new_model))
        target.model, target.provider = result.new_model, result.target_provider

    monkeypatch.setattr("hermes_cli.model_switch.switch_model", _switch_model)
    monkeypatch.setattr(switch_mixin, "_commit_model_switch", _commit)
    monkeypatch.setattr(cli_mod, "_cprint", lambda *_args, **_kwargs: None)

    cli_mod.HermesCLI._handle_model_switch(
        cli, "/model known-pro --session")

    assert metadata_reads and all(read is False for read in metadata_reads)
    assert [event[0] for event in events] == ["prompt", "switch", "commit"]
    assert cli.model == "openai/gpt-5.5-pro"
    assert cli.provider == "openrouter"


def test_typed_cli_switch_decline_and_guard_fault_never_enter_switch_seam(monkeypatch):
    import cli as cli_mod
    import hermes_cli.cli_model_switch_mixin as switch_mixin

    _seed_openrouter_price_cache(monkeypatch)
    context = SimpleNamespace(
        user_providers=None, custom_providers=None,
        with_overrides=lambda **_kwargs: context,
    )
    monkeypatch.setattr("hermes_cli.inventory.load_picker_context", lambda: context)
    monkeypatch.setattr(cli_mod, "_cprint", lambda *_args, **_kwargs: None)
    calls = []

    def _switch_model(**_kwargs):
        calls.append("switch")
        raise AssertionError("declined or faulted selection entered switch pipeline")

    monkeypatch.setattr("hermes_cli.model_switch.switch_model", _switch_model)
    monkeypatch.setattr(
        switch_mixin, "_commit_model_switch",
        lambda *_args, **_kwargs: calls.append("commit"),
    )
    decline = SimpleNamespace(
        model="old-model", provider="openrouter", requested_provider="openrouter",
        api_key="", base_url="https://openrouter.ai/api/v1", agent=None, _app=None,
        _prompt_text_input_modal=lambda **_kwargs: "cancel",
        _normalize_slash_confirm_choice=lambda raw, _choices: raw,
    )
    decline._confirm_expensive_model_switch = _bound(
        cli_mod.HermesCLI._confirm_expensive_model_switch, decline)
    decline._confirm_and_switch_cli_model = _bound(
        cli_mod.HermesCLI._confirm_and_switch_cli_model, decline)

    cli_mod.HermesCLI._handle_model_switch(
        decline, "/model openai/gpt-5.5-pro --provider openrouter --session")
    assert calls == []
    assert decline.model == "old-model"
    assert decline.provider == "openrouter"
    assert decline.requested_provider == "openrouter"
    assert decline.api_key == ""
    assert decline.base_url == "https://openrouter.ai/api/v1"

    def _broken_metadata(_provider, _model, **_kwargs):
        raise RuntimeError("registered model metadata unavailable")

    monkeypatch.setattr("agent.models_dev.get_model_info", _broken_metadata)
    faulted = SimpleNamespace(
        model="old-model", provider="openrouter", requested_provider="openrouter",
        api_key="", base_url="https://openrouter.ai/api/v1", agent=None, _app=None,
        _prompt_text_input_modal=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("guard fault must not request consent")),
        _normalize_slash_confirm_choice=lambda raw, _choices: raw,
    )
    faulted._confirm_expensive_model_switch = _bound(
        cli_mod.HermesCLI._confirm_expensive_model_switch, faulted)
    faulted._confirm_and_switch_cli_model = _bound(
        cli_mod.HermesCLI._confirm_and_switch_cli_model, faulted)
    rendered = []
    monkeypatch.setattr(cli_mod, "_cprint", rendered.append)

    cli_mod.HermesCLI._handle_model_switch(
        faulted, "/model openai/gpt-5.5-pro --provider openrouter --session")
    assert calls == []
    assert faulted.model == "old-model"
    assert faulted.provider == "openrouter"
    assert faulted.requested_provider == "openrouter"
    assert faulted.api_key == ""
    assert faulted.base_url == "https://openrouter.ai/api/v1"
    assert any("registered model metadata unavailable" in line for line in rendered)


def test_typed_cli_switch_refuses_when_local_context_cannot_load(monkeypatch):
    import cli as cli_mod

    import hermes_cli.cli_model_switch_mixin as switch_mixin

    def _unreachable_switch(**_kwargs):
        raise AssertionError("selection with incomplete local context entered switch pipeline")

    monkeypatch.setattr("hermes_cli.inventory.load_picker_context", lambda: (_ for _ in ()).throw(
        RuntimeError("local selection context unavailable")))
    monkeypatch.setattr("hermes_cli.model_switch.switch_model", _unreachable_switch)
    monkeypatch.setattr(
        switch_mixin, "_commit_model_switch",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("failed preflight must not commit")),
    )
    rendered = []
    monkeypatch.setattr(cli_mod, "_cprint", rendered.append)
    cli = SimpleNamespace(
        model="old-model", provider="openrouter", requested_provider="openrouter",
        api_key="", base_url="https://openrouter.ai/api/v1", agent=None, _app=None,
    )

    cli_mod.HermesCLI._handle_model_switch(
        cli, "/model openai/gpt-5.5-pro --provider openrouter --session")

    assert cli.model == "old-model"
    assert cli.provider == "openrouter"
    assert cli.requested_provider == "openrouter"
    assert cli.api_key == ""
    assert cli.base_url == "https://openrouter.ai/api/v1"
    assert any("local selection context unavailable" in line for line in rendered)
