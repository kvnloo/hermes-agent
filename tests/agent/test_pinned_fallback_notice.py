"""Every turn on an entitlement-pinned fallback names the answering route."""

from types import SimpleNamespace

from agent.agent_runtime_helpers import restore_primary_runtime


def test_entitlement_pinned_fallback_announces_each_turn():
    notices = []
    primary = {"provider": "openai-codex", "model": "gpt-5.4", "base_url": ""}
    agent = SimpleNamespace(
        _fallback_activated=True,
        _primary_runtime=primary,
        _entitlement_rejected_models={(primary["provider"], primary["model"])},
        model="gpt-5-mini",
        provider="copilot",
        _emit_diagnostic_status=notices.append,
    )

    for _ in range(2):
        assert restore_primary_runtime(agent) is False

    assert len(notices) == 2
    assert all("gpt-5-mini via copilot" in notice for notice in notices)
    assert all("gpt-5.4 stays unavailable" in notice for notice in notices)
    assert (agent.model, agent.provider) == ("gpt-5-mini", "copilot")
