"""Gateway mount keeps the dashboard auth refusal's supervisor exit contract (#142281)."""

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_gateway_mount_auth_refusal_is_ex_config_and_unmounts(monkeypatch, capsys):
    """A gateway-mounted dashboard refuses missing auth with EX_CONFIG, not exit 1."""
    from gateway.restart import GATEWAY_FATAL_CONFIG_EXIT_CODE
    from gateway.run_api import GatewayDashboardMount
    from hermes_cli import dashboard_auth, web_server

    # The gateway and standalone dashboard share this app; restore its mutable state.
    for name in (
        "gateway_runner", "session_authority", "withhold_session_token",
        "trusted_public_hosts", "trusted_public_origins", "auth_required",
    ):
        monkeypatch.setattr(
            web_server.app.state, name, getattr(web_server.app.state, name, None), raising=False
        )
    monkeypatch.setattr(web_server.app.state, "gateway_runner", None)
    monkeypatch.delattr(web_server.app.state, "listener_public_url", raising=False)

    # Reproduce the reported loopback bind with an operator-declared public URL
    # but no auth provider in the gateway process.
    monkeypatch.setenv("HERMES_DASHBOARD_PUBLIC_URL", "https://dashboard.example.invalid")
    monkeypatch.delenv("HERMES_DESKTOP", raising=False)
    monkeypatch.delenv("HERMES_DASHBOARD_SESSION_TOKEN", raising=False)
    monkeypatch.setattr(
        web_server, "_dashboard_public_hosts",
        lambda: frozenset({"dashboard.example.invalid"}),
    )
    monkeypatch.setattr(
        web_server, "_dashboard_public_origins",
        lambda: frozenset({"https://dashboard.example.invalid"}),
    )
    monkeypatch.setattr(web_server, "should_require_dashboard_auth", lambda *_: True)
    monkeypatch.setattr(dashboard_auth, "list_providers", lambda: [])

    mount = GatewayDashboardMount(
        SimpleNamespace(session_authority=None),
        SimpleNamespace(bound_host="127.0.0.1", bound_port=9119),
    )
    with pytest.raises(SystemExit) as exc:
        await mount.ensure()

    assert exc.value.code == GATEWAY_FATAL_CONFIG_EXIT_CODE
    assert "Refusing to bind dashboard to 127.0.0.1" in capsys.readouterr().err
    assert not mount.loaded
    assert web_server.app.state.gateway_runner is None
    assert web_server.app.state.session_authority is None
    assert web_server.app.state.withhold_session_token is False
