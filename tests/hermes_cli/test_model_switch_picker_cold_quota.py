"""The classic /model picker must commit a healthy route before the first turn.

Regression for NousResearch/hermes-agent#154391; reported and fixed in upstream
PR #154392 by yusuf-madkour. Unlike the lower-level staging test, this exercises
the picker's summary and session-persistence path.
"""

from hermes_cli import runtime_provider
from tests.hermes_cli.test_cli_gateway_model_scope import _submits
from tests.hermes_cli.test_model_switch_cold_init import _cold_cli, _pick, _quota


def test_picker_commits_selected_first_turn_despite_codex_launch_cooldown(monkeypatch):
    cli_mod, cli, conn = _cold_cli(monkeypatch)
    printed = []
    monkeypatch.setattr(cli_mod, "_cprint", lambda message, *args, **kwargs: printed.append(str(message)))
    monkeypatch.setattr(
        "hermes_cli.model_switch.resolve_display_context_length",
        lambda *args, **kwargs: None,
    )
    original_resolve = runtime_provider.resolve_runtime_provider
    attempted = []

    def resolve_unless_launch_quota_exhausted(**kwargs):
        attempted.append(kwargs["requested"])
        if kwargs["requested"] == "openai-codex":
            raise _quota("openai-codex")
        return original_resolve(**kwargs)

    monkeypatch.setattr(
        runtime_provider, "resolve_runtime_provider", resolve_unless_launch_quota_exhausted
    )

    cli_mod.HermesCLI._apply_model_switch_result(cli, _pick(), persist_global=False)

    assert attempted == ["deepseek"], "picker initialized the exhausted launch provider"
    assert (cli.model, cli.provider) == ("deepseek-flash", "deepseek")
    assert (cli.agent.model, cli.agent.provider) == ("deepseek-flash", "deepseek")
    assert conn.state("s").info["model"] == "deepseek-flash"
    assert any("deepseek-flash" in line for line in printed), "missing switch summary"
    assert cli._pending_model_switch_note

    assert cli.chat("first turn after picker") == "ok"
    [submitted] = _submits(conn)
    assert "model_override" not in submitted, "picker must commit the session, not a one-turn override"
