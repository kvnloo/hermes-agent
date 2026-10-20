"""TUI/Tern launches must not start the classic CLI banner's background prefetch.

The parent ``hermes`` process only hands off to the TUI (Ink or the Tern ui-tsp frontend); the
gateway it spawns computes its own update/banner data. The banner prefetch threads (git state,
full ``git status --porcelain``, release tag, skills index YAML scan) are pure overhead there, and
on slow filesystems (Android/proot) they delay the frontend spawn by seconds via subprocesses and
GIL contention.
"""

import pytest

import hermes_cli.banner as banner
import hermes_cli.main as cli_entry


@pytest.fixture
def recorded(monkeypatch):
    calls = []
    monkeypatch.setattr(banner, "prefetch_banner_data", lambda: calls.append("banner"))
    monkeypatch.setattr(banner, "prefetch_update_check", lambda: calls.append("update"))
    monkeypatch.setattr(cli_entry, "_termux_should_prefetch_update_check", lambda: True)
    monkeypatch.setattr(cli_entry, "_sync_bundled_skills_for_startup", lambda: calls.append("skills"))
    return calls


def _settle_threads():
    import threading

    for thread in threading.enumerate():
        if thread.name == "bundled-skills-sync":
            thread.join(timeout=5)


def test_classic_cli_prefetches_banner_data(recorded):
    cli_entry._start_chat_background_prefetch()
    _settle_threads()

    assert "banner" in recorded and "update" in recorded
    assert "skills" in recorded


def test_tui_launch_skips_banner_prefetch_but_keeps_skills_sync(recorded):
    cli_entry._start_chat_background_prefetch(banner=False)
    _settle_threads()

    assert "banner" not in recorded and "update" not in recorded
    assert "skills" in recorded


def test_cmd_chat_skips_banner_prefetch_when_launching_the_tui(monkeypatch):
    seen = {}

    class Launched(Exception):
        pass

    def fake_launch(*_a, **_k):
        raise Launched

    monkeypatch.setattr(cli_entry, "_resolve_use_tui", lambda _args: True)
    monkeypatch.setattr(cli_entry, "_resolve_chat_session_args", lambda *_a, **_k: None)
    monkeypatch.setattr(cli_entry, "_has_any_provider_configured", lambda: True)
    monkeypatch.setattr(cli_entry, "_start_chat_background_prefetch", lambda **kw: seen.update(kw))
    monkeypatch.setattr(cli_entry, "_pin_kanban_board_env", lambda: None)
    monkeypatch.setattr(cli_entry, "_confirm_startup_expensive_model_override", lambda _a: None)
    monkeypatch.setattr(cli_entry, "_warn_retired_xai_models", lambda: None)
    monkeypatch.setattr(cli_entry, "_launch_tui", fake_launch)
    monkeypatch.setattr("hermes_cli.free_tier_bootstrap.run_bootstrap", lambda **_k: None)
    monkeypatch.setattr("hermes_cli.observability.shared_metrics_consent.offer_consent_before_chat", lambda _a: None)

    from hermes_cli._parser import build_top_level_parser

    parser, _, _ = build_top_level_parser()
    args = parser.parse_args(["chat"])
    with pytest.raises(Launched):
        cli_entry.cmd_chat(args)

    assert seen == {"banner": False}
