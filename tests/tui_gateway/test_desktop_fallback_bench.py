"""Desktop fallback admission uses the shared retry horizon.

Regression for NousResearch/hermes-agent#119195, reported by nita-45.
"""

import time

from hermes_cli.auth import AuthError
from tui_gateway import server


def test_desktop_fallback_uses_default_retry_horizon(monkeypatch):
    """Skip a 660s quota bench, but keep a 540s throttle without changing the 600s default."""
    state = {"reset_delay": 540}
    requested = []

    class BenchedCodexPool:
        provider = "openai-codex"

        def has_credentials(self):
            return True

        def has_available(self, model=None):
            return False

        def next_available_at(self, model=None):
            return time.time() + state["reset_delay"]

    def resolve(**kwargs):
        provider = kwargs.get("requested")
        requested.append(provider)
        if provider == "anthropic":
            raise AuthError("Anthropic subscription session quota exhausted")
        if provider == "openai-codex":
            return {
                "provider": provider,
                "api_key": "codex-token",
                "credential_pool": BenchedCodexPool(),
            }
        if provider == "openrouter":
            return {"provider": provider, "api_key": "openrouter-token"}
        raise AssertionError(f"unexpected fallback: {provider}")

    monkeypatch.setattr("hermes_cli.runtime_provider.resolve_runtime_provider", resolve)
    monkeypatch.setattr(
        server,
        "_load_fallback_model",
        lambda: [
            {"provider": "openai-codex", "model": "gpt-5.6-sol"},
            {"provider": "openrouter", "model": "deepseek/deepseek-v4-pro"},
        ],
    )

    for reset_delay, expected_provider, expected_model in (
        (540, "openai-codex", "gpt-5.6-sol"),
        (660, "openrouter", "deepseek/deepseek-v4-pro"),
    ):
        state["reset_delay"] = reset_delay
        requested.clear()

        resolution = server._resolve_runtime_with_fallback({"requested": "anthropic"})

        assert resolution.used_fallback is True
        assert resolution.runtime["provider"] == expected_provider
        assert resolution.selected_model == expected_model
        assert requested == (
            ["anthropic", "openai-codex", "openrouter"]
            if expected_provider == "openrouter"
            else ["anthropic", "openai-codex"]
        )
