"""Regression tests for the Anthropic model-picker dropping curated aliases.

Bug — newly-routed curated aliases vanished on a native Anthropic setup
    ``provider_model_ids("anthropic")`` returned the live ``/v1/models`` dump
    verbatim whenever Anthropic credentials were configured. Anthropic's API
    lags behind freshly-routed aliases (e.g. ``claude-fable-5``, which is
    reachable on Anthropic before the models endpoint enumerates it), so the
    curated entry disappeared from the picker. The picker now merges the
    curated ``_PROVIDER_MODELS["anthropic"]`` list with the live catalog —
    curated entries first, live-only models appended, deduped — mirroring the
    OpenAI curated-merge philosophy.
"""

from unittest.mock import patch

from hermes_cli import models as M


def test_anthropic_merge_dedupes_overlap_and_appends_live_only():
    """Models in both lists appear once; live-only models are appended."""
    live = [
        "claude-opus-4-8",          # overlaps curated
        "claude-sonnet-4-6",        # overlaps curated
        "claude-future-9-99",       # live-only, not curated
    ]
    with patch.object(M, "_fetch_anthropic_models", return_value=live):
        result = M.provider_model_ids("anthropic")

    # No duplicates introduced by the merge.
    assert result.count("claude-opus-4-8") == 1
    # Live-only entry is preserved (discovery still works for unknown models).
    assert "claude-future-9-99" in result
    # Curated entries lead, live-only trails.
    curated = list(M._PROVIDER_MODELS["anthropic"])
    assert result[:len(curated)] == curated and result[-1] == "claude-future-9-99"


def test_anthropic_falls_back_to_curated_when_live_unavailable():
    """No creds / live failure -> curated list verbatim (alias still present)."""
    with patch.object(M, "_fetch_anthropic_models", return_value=None):
        result = M.provider_model_ids("anthropic")

    assert result == list(M._PROVIDER_MODELS["anthropic"])


def test_anthropic_picker_keeps_55_aliases_when_live_catalog_lags():
    """Regression for #135448: a stale live listing must not hide native 5.5 models."""
    with patch.object(
        M,
        "_fetch_anthropic_models",
        return_value=["claude-sonnet-5", "claude-haiku-4-5-20251001"],
    ):
        models = M.provider_model_ids("anthropic")

    for newer, older in (
        ("claude-sonnet-5-5", "claude-sonnet-5"),
        ("claude-haiku-5-5", "claude-haiku-4-5-20251001"),
    ):
        assert models.count(newer) == 1
        assert models.index(newer) < models.index(older)
