"""A terminal auth failure on the auxiliary auto route benches the provider instead of being replayed.

Regression for a gateway whose main provider lost its login (``Claude Code is installed but has no
usable login``, HTTP 401) with ``fallback_providers: []``: the kanban auto-decomposer called the
auxiliary client once per dispatcher tick and each call re-ran the dead provider, logged
``auth error on auto and all fallbacks exhausted`` and raised — 16 times in 15 minutes — while the
dispatcher reported ``0 workers spawned``. The credential rungs already ran before the fallback
rung, so when every fallback is exhausted on an auth error the provider cannot serve auxiliary work
until the owner re-authenticates: mark it unhealthy (like a 402) so later auxiliary calls skip it.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from agent import auxiliary_client as aux
from agent import auxiliary_error_policy as aux_errors

PROVIDER = "claude-subscription-directsdk-experimental"
BASE = f"process://{PROVIDER}"


class _LoggedOut(RuntimeError):
    """Shape of the provider plugin's ``ClaudeCodeLoggedOut`` (a RuntimeError carrying status 401)."""
    status_code = 401


class _RateLimited(RuntimeError):
    status_code = 429


class _Client:
    api_key = "not-a-real-key"
    base_url = BASE
    _hermes_aux_backend_provider = ""
    _hermes_aux_effective_provider = PROVIDER


@pytest.fixture(autouse=True)
def _clean_health():
    aux._reset_aux_unhealthy_cache()
    yield
    aux._reset_aux_unhealthy_cache()


def _exhaust(err: Exception, task: str = "kanban_decomposer"):
    """Drive the real provider-fallback rung with no configured fallback anywhere."""
    client = _Client()
    route = aux._LadderRoute(client, task, "", False, BASE, "auto", "claude-opus-5-5", None, None, None,
                             "claude-opus-5-5", {"provider": PROVIDER, "model": "claude-opus-5-5"}, None, 180)
    failure = aux_errors.Failure(err, aux_errors.classify_attempt(err, PROVIDER, client), client=client)
    none = (None, None, "")
    with patch.object(aux, "_try_configured_fallback_chain", return_value=none), \
         patch.object(aux, "_try_main_fallback_chain", return_value=none), \
         patch.object(aux, "_try_payment_fallback", return_value=none), \
         patch.object(aux, "_next_fallback_after_quarantine", return_value=none):
        gen = aux._ladder_provider_fallback(failure, route)
        with pytest.raises(StopIteration) as stop:
            next(gen)
    return stop.value.value


def _main_route():
    with patch.object(aux, "resolve_provider_client", return_value=(MagicMock(), "claude-opus-5-5")) as build:
        routed = aux._try_main_provider_route(PROVIDER, "claude-opus-5-5", BASE, None, "")
    return routed, build


def test_auth_exhaustion_benches_the_main_provider_for_later_aux_calls(caplog):
    caplog.set_level(logging.WARNING, logger="agent.auxiliary_client")
    assert _exhaust(_LoggedOut("Claude Code is installed but has no usable login. Run `claude auth login`.")) is None
    assert aux._is_provider_unhealthy(PROVIDER)
    routed, build = _main_route()
    assert routed is None, "the next auxiliary call must not rebuild and re-send to a provider that needs re-auth"
    build.assert_not_called()
    # One actionable line naming the provider and carrying the provider's own login hint.
    marks = [r.getMessage() for r in caplog.records if "marking" in r.getMessage()]
    assert len(marks) == 1 and PROVIDER in marks[0] and "re-auth" in marks[0] and "claude auth login" in marks[0]


def test_repeat_callers_do_not_repeat_the_refusing_to_guess_warning(caplog):
    _exhaust(_LoggedOut("no usable login"))
    caplog.clear()
    caplog.set_level(logging.WARNING, logger="agent.auxiliary_client")
    for _ in range(3):
        assert aux._discovery_chain_allowed(PROVIDER, "kanban_decomposer") is False
    assert not [r for r in caplog.records if "refusing to guess" in r.getMessage()]


def test_transient_failures_do_not_bench_the_provider():
    _exhaust(_RateLimited("Error code: 429 - rate limited"))
    assert not aux._is_provider_unhealthy(PROVIDER)
    routed, build = _main_route()
    assert routed is not None
    build.assert_called_once()
