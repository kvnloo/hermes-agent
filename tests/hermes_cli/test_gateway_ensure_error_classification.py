"""Regression for NousResearch/hermes-agent#150424: bad input is not a broken launch."""
from types import SimpleNamespace
import json

import pytest


def test_ensure_distinguishes_invalid_timeout_from_launch_value_error(tmp_path, monkeypatch, capsys):
    import hermes_constants
    from hermes_cli import gateway_runtime, gateway_runtime_cli

    monkeypatch.setattr(hermes_constants, "get_hermes_home", lambda: tmp_path)

    # Invalid caller input must never reach the runtime.
    def unexpected_launch(_home, *, timeout):
        raise AssertionError("invalid timeout reached the gateway")

    monkeypatch.setattr(gateway_runtime, "ensure_gateway_runtime", unexpected_launch)
    with pytest.raises(SystemExit) as invalid:
        gateway_runtime_cli.cmd_gateway_ensure(SimpleNamespace(timeout="nan"))
    assert invalid.value.code == 2
    assert json.loads(capsys.readouterr().out)["reason_code"] == "invalid_invocation"

    # Valid input can fail inside launchd/plist handling. That is not a CLI error.
    for error_type in (ValueError, TypeError):
        def broken_launch(home, *, timeout):
            assert home == tmp_path and timeout == 5
            raise error_type("plist serialization failed")

        monkeypatch.setattr(gateway_runtime, "ensure_gateway_runtime", broken_launch)
        with pytest.raises(SystemExit) as failed:
            gateway_runtime_cli.cmd_gateway_ensure(SimpleNamespace(timeout="5"))
        output = capsys.readouterr()
        assert failed.value.code == 7
        assert json.loads(output.out) == {
            "state": "inaccessible", "reason_code": "launch_failed", "endpoint": None,
        }
        assert f"{error_type.__name__}: plist serialization failed" in output.err
