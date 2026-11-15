"""Alibaba Token Plan: a successful key-scoped /v1/models listing is the account's whole catalog.

Entitlements differ per plan and key tier, so the curated floor carries ids a given account
can't call (``qwen3.8-max-0902`` 404s on every turn, #119481). The picker, its disk-cached
read path and first-run setup must all offer only what the live listing returned; a failed
probe still serves the curated floor. Uses the real bundled profiles, not a mock.
"""

from unittest.mock import patch

import pytest

from hermes_cli.models import provider_model_ids
from hermes_cli.models_catalog_static import _ALIBABA_TOKEN_PLAN_MODELS

LIVE = ["qwen3.8-max", "qwen3.6-flash", "deepseek-v4-flash-0731"]
RETIRED = "qwen3.8-max-0902"


def _profile(slug):
    from providers import get_provider_profile

    profile = get_provider_profile(slug)
    assert profile is not None and profile.name == slug
    return profile


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("ALIBABA_TOKEN_PLAN_API_KEY", "sk-sp-test")
    monkeypatch.setenv("ALIBABA_TOKEN_PLAN_CN_API_KEY", "sk-sp-test")


@pytest.mark.parametrize("slug", ["alibaba-token-plan", "alibaba-token-plan-cn"])
def test_successful_listing_drops_curated_only_ids(slug):
    assert RETIRED in _ALIBABA_TOKEN_PLAN_MODELS
    with patch.object(type(_profile(slug)), "fetch_models", lambda self, **kw: list(LIVE)):
        rows = provider_model_ids(slug)
    assert rows == LIVE


def test_failed_probe_still_serves_curated_floor():
    def boom(self, **kw):
        raise OSError("offline")

    with patch.object(type(_profile("alibaba-token-plan")), "fetch_models", boom):
        rows = provider_model_ids("alibaba-token-plan")
    assert RETIRED in rows and len(rows) == len(_ALIBABA_TOKEN_PLAN_MODELS)


def test_picker_disk_cache_round_trip_keeps_live_rows_only():
    from hermes_cli.model_switch_providers import _live_or_curated_ids
    from hermes_cli.models import _PROVIDER_MODELS, clear_provider_models_cache

    clear_provider_models_cache()
    with patch.object(type(_profile("alibaba-token-plan")), "fetch_models", lambda self, **kw: list(LIVE)):
        first = _live_or_curated_ids("alibaba-token-plan", _PROVIDER_MODELS)
    # Second open is served from $HERMES_HOME/provider_models_cache.json without a fetch.
    second = _live_or_curated_ids("alibaba-token-plan", _PROVIDER_MODELS, non_blocking=True)
    assert RETIRED not in first and RETIRED not in second
    assert set(second) == set(LIVE)


def test_first_run_setup_offers_live_rows_not_the_curated_shortcut():
    from types import SimpleNamespace

    from hermes_cli.model_setup_flows import _api_key_provider_model_list

    pconfig = SimpleNamespace(name="Alibaba Cloud (Token Plan)")
    with (
        patch.object(type(_profile("alibaba-token-plan")), "fetch_models", lambda self, **kw: list(LIVE)),
        patch("hermes_cli.model_setup_flows._models_dev_merged", return_value=[]),
        patch("hermes_cli.model_setup_flows._report_live_models"),
        patch("hermes_cli.model_setup_flows._show_curated"),
    ):
        rows = _api_key_provider_model_list(
            "alibaba-token-plan", pconfig, "sk-sp-test", "ALIBABA_TOKEN_PLAN_API_KEY",
            "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1")
    assert RETIRED not in rows
    assert rows == LIVE
