"""Capacity broker: model/pool recommendation without live routing by default."""

from __future__ import annotations

from hermes_cli.capacity_broker import recommend


def test_phone_interactive_stays_on_grok_not_groq():
    d = recommend(
        privacy_class="company-private",
        work_kind="interactive",
        load1=8.0,
        nproc=20,
        remaining={"grok_weekly_used_pct": 15, "codex_weekly_used_pct": 10},
    )
    assert d.provider == "xai-oauth"
    assert d.model == "grok-4.6"
    assert "cpu-interactive" in d.pools
    assert "provider-groq" not in d.pools
    assert d.applied is False


def test_public_oss_triage_uses_free_moa():
    d = recommend(
        privacy_class="public-oss",
        work_kind="observe",
        load1=8.0,
        nproc=20,
        remaining={"grok_weekly_used_pct": 15},
    )
    assert d.moa_preset == "triage-tiny"
    assert d.provider == "moa"
    assert "cpu-batch" in d.pools


def test_secrets_never_get_free_or_opencode():
    d = recommend(
        privacy_class="secrets",
        work_kind="coding",
        load1=4.0,
        nproc=20,
        remaining={},
    )
    assert d.provider == "openai-codex"
    assert "opencode" not in (d.provider or "")
    assert d.moa_preset is None
    assert "provider-groq" not in d.pools


def test_pinned_model_is_respected_not_overwritten():
    d = recommend(
        privacy_class="public-oss",
        work_kind="review",
        load1=8.0,
        nproc=20,
        remaining={},
        pinned_model="coding-free",
        pinned_provider="moa",
    )
    assert d.model == "coding-free"
    assert d.provider == "moa"
    assert d.pinned is True
    assert d.applied is False
    assert any("pin" in r.lower() for r in d.reasons)


def test_compute_critical_marks_defer_not_a_new_model():
    d = recommend(
        privacy_class="public-oss",
        work_kind="review",
        load1=30.0,
        nproc=20,
        remaining={},
        pinned_model="coding-free",
        pinned_provider="moa",
    )
    assert d.defer is True
    assert d.model == "coding-free"
    assert any("compute" in r.lower() for r in d.reasons)


def test_grok_exhausted_falls_to_codex_for_private_interactive():
    d = recommend(
        privacy_class="company-private",
        work_kind="interactive",
        load1=4.0,
        nproc=20,
        remaining={"grok_weekly_used_pct": 96, "codex_weekly_used_pct": 10},
    )
    assert d.provider == "openai-codex"
    assert d.model == "gpt-5.6-sol"
    assert any("grok" in r.lower() for r in d.reasons)
