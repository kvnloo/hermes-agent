"""Regression for #18990 and #89848: Moonshot CN vision uses model capabilities.

The provider's /v1/chat/completions endpoint accepts images (#23657, #89848),
so auto routing must try an image-capable CN model, but still skip text-only models.
The catalog and transport are hermetic: no credentials or network calls.
"""

from __future__ import annotations

from unittest.mock import Mock

import agent.auxiliary_client as aux
import agent.models_dev as models_dev


def test_cn_main_provider_vision_follows_real_model_catalog(monkeypatch):
    """Exercise the real catalog gate; mock only endpoint resolution."""
    catalog = {
        "kimi-for-coding": {"models": {
            "kimi-k3": {"modalities": {"input": ["text", "image"]}},
            "legacy-text-only": {"modalities": {"input": ["text"]}},
        }},
    }
    monkeypatch.setattr(models_dev, "fetch_models_dev", lambda **_: catalog)
    monkeypatch.setattr(
        "hermes_cli.config.load_config_readonly",
        lambda: {"model": {"provider": "kimi-coding-cn", "default": "kimi-k3"}},
    )
    monkeypatch.setattr(aux, "_resolve_provider_vision_default", lambda _: None)

    client = object()
    resolver = Mock(side_effect=lambda provider, model, **_: (client, model))
    monkeypatch.setattr(aux, "resolve_provider_client", resolver)

    resolved_client, resolved_model = aux._vision_main_provider_client(
        "kimi-coding-cn", "kimi-k3", {}, None, None
    )
    assert resolved_client is client
    assert resolved_model == "kimi-k3"
    assert resolver.call_args.args[:2] == ("kimi-coding-cn", "kimi-k3")
    assert resolver.call_args.kwargs["is_vision"] is True

    resolver.reset_mock()
    resolved_client, resolved_model = aux._vision_main_provider_client(
        "kimi-coding-cn", "legacy-text-only", {}, None, None
    )
    assert (resolved_client, resolved_model) == (None, None)
    resolver.assert_not_called()
