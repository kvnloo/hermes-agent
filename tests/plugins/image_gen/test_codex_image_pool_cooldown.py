"""Regression for #152300: a chat entitlement cooldown must not disable Codex images.

Complements poyhsiao's #152301 call-site tests with a real credential pool, rather
than a mocked selector that cannot exercise model-scoped cooldown decisions.
"""

from __future__ import annotations

import importlib

import pytest

from agent import auxiliary_client
from agent.credential_pool import CredentialPool, PooledCredential

codex_plugin = importlib.import_module("plugins.image_gen.openai-codex")


@pytest.mark.parametrize(
    ("benched_model", "available"),
    [
        ("gpt-4o", True),
        ("gpt-image-2", False),
    ],
)
def test_codex_image_availability_respects_only_image_model_bench(
    monkeypatch, benched_model, available,
):
    """A chat-only bench spares images, but an image-model bench still blocks them."""
    key = PooledCredential(
        "openai-codex", "paid-account", "paid-account", "api_key", 0, "manual",
        "pooled-codex-token", model_cooldowns={benched_model: 9e9},
    )
    pool = CredentialPool("openai-codex", [key])
    monkeypatch.setattr(
        auxiliary_client, "_load_pool_with_credentials",
        lambda provider, *_args: pool if provider == "openai-codex" else None,
    )
    monkeypatch.setattr(auxiliary_client, "_read_codex_singleton_token", lambda: None)

    assert codex_plugin.OpenAICodexImageGenProvider().is_available() is available
