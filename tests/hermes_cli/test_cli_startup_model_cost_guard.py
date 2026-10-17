import builtins
import sys
import types
from argparse import Namespace


import pytest


class _NonInteractiveStdin:
    def isatty(self):
        return False


def _chat_args(**overrides):
    base = {
        "continue_last": None,
        "model": None,
        "provider": None,
        "resume": None,
        "no_restore_cwd": False,
        "toolsets": None,
        "skills": None,
        "tui": False,
        "tui_dev": False,
        "cli": True,
        "verbose": None,
        "quiet": True,
        "query": "hello",
        "image": None,
        "worktree": False,
        "checkpoints": False,
        "pass_session_id": False,
        "max_turns": None,
        "ignore_rules": False,
        "ignore_user_config": False,
        "safe_mode": False,
        "compact": False,
        "source": None,
        "yolo": False,
        "accept_hooks": False,
    }
    base.update(overrides)
    return Namespace(**base)


@pytest.fixture
def main_mod(monkeypatch):
    import hermes_cli.main as mod

    monkeypatch.setattr(mod, "_has_any_provider_configured", lambda: True)
    monkeypatch.setattr(mod, "_sync_bundled_skills_for_startup", lambda: None)
    monkeypatch.setattr(mod, "_pin_kanban_board_env", lambda: None)
    monkeypatch.setattr(mod, "_resolve_session_by_name_or_id", lambda val: val)
    monkeypatch.setattr(mod, "_oneshot_cleanup_done", False)
    return mod


@pytest.fixture
def fake_cli(monkeypatch):
    captured = {}

    def fake_cli_main(**kwargs):
        captured.update(kwargs)

    monkeypatch.setitem(sys.modules, "cli", types.SimpleNamespace(main=fake_cli_main))
    return captured


@pytest.fixture
def codex_config(monkeypatch):
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {
            "model": {
                "provider": "openai-codex",
                "default": "gpt-5.5",
                "base_url": "https://chatgpt.com/backend-api/codex",
            }
        },
    )


def _set_startup_config(
    monkeypatch, *, provider="custom", default="safe-model", base_url="", ack=None
):
    model = {"provider": provider, "default": default}
    if base_url:
        model["base_url"] = base_url
    config = {"model": model}
    if ack is not None:
        config["security"] = {
            "allow_data_training_tiers_noninteractive": ack,
        }
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: config)


def test_cmd_chat_rejects_noninteractive_gpt55_pro_startup_override(
    main_mod, fake_cli, codex_config, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(_chat_args(model="openai/gpt-5.5-pro"))

    assert excinfo.value.code == 1
    assert not fake_cli
    err = capsys.readouterr().err
    assert "EXPENSIVE MODEL WARNING" in err
    assert "non-interactive" in err


def test_cmd_chat_rejects_noninteractive_gpt55_pro_even_with_yolo(
    main_mod, fake_cli, codex_config, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(_chat_args(model="openai/gpt-5.5-pro", yolo=True))

    assert excinfo.value.code == 1
    assert not fake_cli
    assert "EXPENSIVE MODEL WARNING" in capsys.readouterr().err


def test_cmd_chat_allows_acknowledged_data_training_tier_noninteractively(
    main_mod, fake_cli, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())
    _set_startup_config(monkeypatch, ack=True)

    main_mod.cmd_chat(
        _chat_args(model="muse-spark-1.2-contributor", provider="custom")
    )

    assert fake_cli["model"] == "muse-spark-1.2-contributor"
    err = capsys.readouterr().err
    assert "TRAINS ON YOUR DATA" in err
    assert "security.allow_data_training_tiers_noninteractive" in err


def test_cmd_chat_rejects_unacknowledged_data_training_tier_with_opt_in_hint(
    main_mod, fake_cli, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())
    _set_startup_config(monkeypatch)

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(
            _chat_args(model="muse-spark-1.2-contributor", provider="custom")
        )

    assert excinfo.value.code == 1
    assert not fake_cli
    err = capsys.readouterr().err
    assert "TRAINS ON YOUR DATA" in err
    assert "security.allow_data_training_tiers_noninteractive" in err


def test_data_training_acknowledgement_does_not_bypass_cost_guard(
    main_mod, fake_cli, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())
    _set_startup_config(
        monkeypatch,
        provider="openai-codex",
        default="gpt-5.5",
        base_url="https://chatgpt.com/backend-api/codex",
        ack=True,
    )

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(_chat_args(model="openai/gpt-5.5-pro"))

    assert excinfo.value.code == 1
    assert not fake_cli
    assert "EXPENSIVE MODEL WARNING" in capsys.readouterr().err


def test_data_training_acknowledgement_requires_literal_true(
    main_mod, fake_cli, monkeypatch
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())
    _set_startup_config(monkeypatch, ack="true")

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(
            _chat_args(model="muse-spark-1.2-contributor", provider="custom")
        )

    assert excinfo.value.code == 1
    assert not fake_cli


def test_data_training_acknowledgement_does_not_skip_interactive_confirmation(
    main_mod, fake_cli, monkeypatch, capsys
):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    _set_startup_config(monkeypatch, ack=True)

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(
            _chat_args(model="muse-spark-1.2-contributor", provider="custom")
        )

    assert excinfo.value.code == 1
    assert not fake_cli
    assert "Model override cancelled" in capsys.readouterr().err


def test_cmd_chat_allows_interactive_gpt55_pro_when_confirmed(
    main_mod, fake_cli, codex_config, monkeypatch
):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "yes")

    main_mod.cmd_chat(_chat_args(model="openai/gpt-5.5-pro"))

    assert fake_cli["model"] == "openai/gpt-5.5-pro"


def test_cmd_chat_cancels_interactive_gpt55_pro_when_not_confirmed(
    main_mod, fake_cli, codex_config, monkeypatch, capsys
):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(_chat_args(model="openai/gpt-5.5-pro"))

    assert excinfo.value.code == 1
    assert not fake_cli
    assert "Model override cancelled" in capsys.readouterr().err


def test_cmd_chat_cancels_interactive_gpt55_pro_on_eof(
    main_mod, fake_cli, codex_config, monkeypatch, capsys
):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    def raise_eof(_prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(_chat_args(model="openai/gpt-5.5-pro"))

    assert excinfo.value.code == 1
    assert not fake_cli
    assert "Model override cancelled" in capsys.readouterr().err


def test_cmd_chat_rejects_noninteractive_provider_only_override_when_default_is_expensive(
    main_mod, fake_cli, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {"model": {"provider": "openai-codex", "default": "openai/gpt-5.5-pro"}},
    )

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(_chat_args(model=None, provider="nous"))

    assert excinfo.value.code == 1
    assert not fake_cli
    assert "EXPENSIVE MODEL WARNING" in capsys.readouterr().err


def test_cmd_chat_allows_noninteractive_safe_codex_startup_override(
    main_mod, fake_cli, monkeypatch
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {"model": {"provider": "openai-codex", "default": "gpt-5.5"}},
    )

    main_mod.cmd_chat(_chat_args(model="gpt-5.5", provider="openai-codex"))

    assert fake_cli["model"] == "gpt-5.5"
    assert fake_cli["provider"] == "openai-codex"


def test_top_level_oneshot_rejects_noninteractive_gpt55_pro_startup_override(
    main_mod, codex_config, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())
    monkeypatch.setattr(sys, "argv", ["hermes", "-z", "hello", "-m", "openai/gpt-5.5-pro"])
    monkeypatch.setattr(main_mod, "_prepare_agent_startup", lambda _args: None)

    called = False

    def fake_run_and_exit_oneshot(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(main_mod, "_run_and_exit_oneshot", fake_run_and_exit_oneshot)

    with pytest.raises(SystemExit) as excinfo:
        main_mod.main()

    assert excinfo.value.code == 1
    assert called is False
    err = capsys.readouterr().err
    assert "EXPENSIVE MODEL WARNING" in err
    assert "non-interactive" in err

def test_cmd_chat_refuses_startup_when_registered_guard_fails(
    main_mod, fake_cli, monkeypatch, capsys,
):
    monkeypatch.setattr(sys, "stdin", _NonInteractiveStdin())
    _set_startup_config(monkeypatch, provider="anthropic", default="old-model")

    def _fail_model_metadata(_provider, _model):
        raise RuntimeError("registered model metadata unavailable")

    monkeypatch.setattr("agent.models_dev.get_model_info", _fail_model_metadata)

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(_chat_args(model="new-model"))

    assert excinfo.value.code == 1
    assert not fake_cli
    assert "safety checks failed" in capsys.readouterr().err.lower()


def _isolate_cmd_chat_startup(monkeypatch, main_mod):
    monkeypatch.setattr(main_mod, "_resolve_use_tui", lambda _args: False)
    monkeypatch.setattr(main_mod, "_resolve_chat_session_args", lambda *_args: None)
    monkeypatch.setattr(main_mod, "_warn_retired_xai_models", lambda: None)
    monkeypatch.setattr(main_mod, "_start_chat_background_prefetch", lambda: None)
    monkeypatch.setitem(
        sys.modules,
        "hermes_cli.stream_json",
        types.SimpleNamespace(stream_json_requested=lambda _args: False),
    )
    monkeypatch.setitem(
        sys.modules,
        "hermes_cli.free_tier_bootstrap",
        types.SimpleNamespace(run_bootstrap=lambda **_kwargs: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "hermes_cli.observability.shared_metrics_consent",
        types.SimpleNamespace(offer_consent_before_chat=lambda _args: None),
    )
    started_processes = []
    monkeypatch.setitem(
        sys.modules,
        "hermes_cli.observability.shared_metrics_process",
        types.SimpleNamespace(begin_process=started_processes.append),
    )
    return started_processes


@pytest.mark.parametrize(
    "failed_module",
    ["hermes_cli.config", "hermes_cli.model_selection_guards"],
)
def test_cmd_chat_refuses_explicit_override_when_guard_helper_import_fails(
    main_mod, fake_cli, monkeypatch, capsys, failed_module
):
    started_processes = _isolate_cmd_chat_startup(monkeypatch, main_mod)
    monkeypatch.setattr(
        main_mod, "_guard_noninteractive_user_config", lambda _args: None
    )
    config_loads = []
    guard_checks = []
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: config_loads.append(True) or {},
    )
    monkeypatch.setattr(
        "hermes_cli.model_selection_guards.selection_warnings",
        lambda *args, **kwargs: guard_checks.append((args, kwargs)) or [],
    )

    failed_imports = []
    original_import = builtins.__import__

    def fail_guard_helper_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == failed_module:
            failed_imports.append(name)
            raise ImportError("guard helper unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_guard_helper_import)
    args = _chat_args(model="explicit-model", provider="explicit-provider")

    with pytest.raises(SystemExit) as excinfo:
        main_mod.cmd_chat(args)

    assert excinfo.value.code == 1
    assert failed_imports == [failed_module]
    assert args.model == "explicit-model"
    assert args.provider == "explicit-provider"
    assert config_loads == []
    assert guard_checks == []
    assert started_processes == []
    assert not fake_cli
    err = capsys.readouterr().err
    assert "Model-selection safety checks failed" in err
    assert "Refusing startup because the selected model could not be checked." in err


def test_cmd_chat_keeps_implicit_startup_when_guard_imports_are_unavailable(
    main_mod, fake_cli, monkeypatch, capsys
):
    started_processes = _isolate_cmd_chat_startup(monkeypatch, main_mod)
    blocked_imports = []
    original_import = builtins.__import__

    def fail_guard_helper_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "hermes_cli.model_selection_guards":
            blocked_imports.append(name)
            raise ImportError("guard helper unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_guard_helper_import)
    args = _chat_args()

    main_mod.cmd_chat(args)

    assert blocked_imports == []
    assert started_processes == ["cli"]
    assert fake_cli["query"] == "hello"
    assert "model" not in fake_cli
    assert "provider" not in fake_cli
    assert "Model-selection safety checks failed" not in capsys.readouterr().err
