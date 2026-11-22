"""``model: hermes-agent`` is the gateway, never a provider model id — also on a named profile.

Regression: a profile named ``tek`` advertises ``tek`` on /v1/models, so only ``tek`` was nulled as
the virtual alias. A client sending the generic ``hermes-agent`` (the documented default, and what
gateway/run_turn.py's proxy sends literally) had it treated as a raw model override: the turn ran
with ``model=hermes-agent``, the provider answered ``404 model: hermes-agent`` and the agent burned
three retries on a deterministic error before the caller re-sent with the real model.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter, _request_agent_overrides


@pytest.fixture
def named_profile_adapter():
    with patch("gateway.platforms.api_server.APIServerAdapter._resolve_model_name", return_value="tek"):
        adapter = APIServerAdapter(PlatformConfig(enabled=True, extra={}))
    assert adapter._model_name == "tek"
    return adapter


@pytest.mark.parametrize("sent", ["hermes-agent", "tek", "openrouter::hermes-agent"])
def test_generic_and_advertised_alias_are_not_provider_models(named_profile_adapter, sent):
    req = named_profile_adapter._session_runtime_request_from_body({"model": sent})
    assert req["requested"]["model"] is None
    assert req["route"] is None or "model" not in req["route"]
    assert req["route_source"] == "global"


def test_openai_and_runs_overrides_drop_the_generic_alias():
    assert "requested_model" not in _request_agent_overrides({"model": "hermes-agent"}, virtual_model="tek")
    assert "requested_model" not in _request_agent_overrides(
        {"model": "hermes-agent", "provider": "anthropic"}, virtual_model="tek")


def test_stored_generic_alias_is_not_replayed_upstream(named_profile_adapter):
    assert named_profile_adapter._stored_session_model({"model": "hermes-agent"}) is None


def test_real_model_requests_still_pass_through(named_profile_adapter):
    req = named_profile_adapter._session_runtime_request_from_body({"model": "claude-opus-5-5"})
    assert req["requested"]["model"] == "claude-opus-5-5" and req["route_source"] == "raw_request"
    assert _request_agent_overrides({"model": "claude-opus-5-5"}, virtual_model="tek")["requested_model"] == \
        "claude-opus-5-5"
