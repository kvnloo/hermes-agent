"""Multiplex gateway log routing (#82936, salvage of #84954).

``setup_logging(mode="gateway")`` binds agent.log/errors.log/gateway.log to
the launch home. Under ``multiplex_profiles`` every secondary profile's
records — emitted inside ``_profile_runtime_scope`` — used to fan out into
the DEFAULT profile's files. The gateway now enables the #99440 profile
routers at startup so each record lands in its owner's ``logs/``.
"""

import logging
import types
from pathlib import Path

import pytest

import hermes_logging
from gateway import run


@pytest.fixture
def clean_logging():
    hermes_logging._reset_queued_handlers()
    hermes_logging._logging_initialized = False
    yield
    hermes_logging._reset_queued_handlers()
    hermes_logging._logging_initialized = False


def _emit_under(home: Path, name: str, level: int, msg: str) -> None:
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override

    token = set_hermes_home_override(home)
    try:
        logging.getLogger(name).log(level, msg)
    finally:
        reset_hermes_home_override(token)


def _contains(home: Path, filename: str, needle: str) -> bool:
    path = home / "logs" / filename
    return path.exists() and needle in path.read_text()


def test_multiplex_gateway_routes_profile_records_to_their_own_logs(
    tmp_path, monkeypatch, clean_logging
):
    default_home = tmp_path / "default"
    beta_home = tmp_path / "default" / "profiles" / "beta"
    beta_home.mkdir(parents=True)
    homes = [("default", default_home), ("beta", beta_home)]
    monkeypatch.setattr(run, "_multiplex_profile_homes", lambda _cfg: homes)

    hermes_logging.setup_logging(hermes_home=default_home, mode="gateway")

    # Single-profile gateway: wiring is inert and handlers stay static.
    assert run._enable_multiplex_log_routing(types.SimpleNamespace(multiplex_profiles=False)) is False
    assert run._enable_multiplex_log_routing(types.SimpleNamespace(multiplex_profiles=True)) is True

    _emit_under(beta_home, "gateway.run", logging.WARNING, "BETA-GATEWAY-WARN")
    _emit_under(default_home, "gateway.run", logging.INFO, "DEFAULT-GATEWAY-INFO")
    hermes_logging.flush_log_queue()

    for filename in ("agent.log", "errors.log", "gateway.log"):
        assert _contains(beta_home, filename, "BETA-GATEWAY-WARN"), filename
        assert not _contains(default_home, filename, "BETA-GATEWAY-WARN"), filename
    assert _contains(default_home, "gateway.log", "DEFAULT-GATEWAY-INFO")
    assert not _contains(beta_home, "gateway.log", "DEFAULT-GATEWAY-INFO")


def test_router_constructor_failure_keeps_gateway_file_sink(
    tmp_path, monkeypatch, clean_logging, capsys
):
    """Regression for #141958: a mid-swap failure must not orphan queued records."""
    default_home = tmp_path / "default"
    beta_home = tmp_path / "beta"
    beta_home.mkdir()
    monkeypatch.setattr(
        run, "_multiplex_profile_homes",
        lambda _cfg: [("default", default_home), ("beta", beta_home)],
    )
    hermes_logging.setup_logging(hermes_home=default_home, mode="gateway")
    original_handlers = list(hermes_logging._queued_file_handlers)
    real_router = hermes_logging._ProfileRoutingFileHandler
    constructed = []

    class RefuseSecondRouter(real_router):
        def __init__(self, handler, homes):
            if constructed:
                raise RuntimeError("second router refused")
            constructed.append(True)
            super().__init__(handler, homes)

    monkeypatch.setattr(hermes_logging, "_ProfileRoutingFileHandler", RefuseSecondRouter)
    assert run._enable_multiplex_log_routing(types.SimpleNamespace(multiplex_profiles=True)) is False
    assert hermes_logging._queued_file_handlers == original_handlers
    assert hermes_logging._queue_listener is not None
    logging.getLogger("gateway.run").warning("AFTER-CONSTRUCTOR-REFUSAL")
    hermes_logging.flush_log_queue()
    for filename in ("agent.log", "gateway.log", "errors.log"):
        assert _contains(default_home, filename, "AFTER-CONSTRUCTOR-REFUSAL")
    assert "per-profile log routing is off" in capsys.readouterr().err


def test_listener_restart_failure_restores_launch_profile_sink(
    tmp_path, monkeypatch, clean_logging
):
    """Regression for #141958: listener startup failure must restore the old listener."""
    default_home = tmp_path / "default"
    beta_home = tmp_path / "beta"
    beta_home.mkdir()
    monkeypatch.setattr(
        run, "_multiplex_profile_homes",
        lambda _cfg: [("default", default_home), ("beta", beta_home)],
    )
    hermes_logging.setup_logging(hermes_home=default_home, mode="gateway")
    original_handlers = list(hermes_logging._queued_file_handlers)
    original_listener = hermes_logging._queue_listener

    def refuse_replacement_listener():
        raise RuntimeError("replacement listener refused")

    monkeypatch.setattr(hermes_logging, "_start_queue_listener_locked", refuse_replacement_listener)
    assert run._enable_multiplex_log_routing(types.SimpleNamespace(multiplex_profiles=True)) is False
    assert hermes_logging._queued_file_handlers == original_handlers
    assert hermes_logging._queue_listener is original_listener
    logging.getLogger("gateway.run").warning("AFTER-LISTENER-REFUSAL")
    hermes_logging.flush_log_queue()
    for filename in ("agent.log", "gateway.log", "errors.log"):
        assert _contains(default_home, filename, "AFTER-LISTENER-REFUSAL")
