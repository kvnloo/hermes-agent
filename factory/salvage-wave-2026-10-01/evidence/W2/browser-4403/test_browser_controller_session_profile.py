"""Cloud browser-controller registration resolves the session's canonical profile.

Production session builders (session.create / _init_session / compute host) stamp
``profile_home`` (``None`` for the launch profile) and never a bare ``profile`` name,
so ``browser.controller.register`` must derive ``profile_id`` from the session's
home: the same canonical name ``session.create`` persists as the session row's
``profile_name`` and the key the local-API adapter uses for artifact-store slots.
"""

from __future__ import annotations

import pytest

from gateway.browser_control_broker import get_browser_control_broker
from hermes_constants import get_default_hermes_root
from tui_gateway import server


class _Transport:
    auth_identity = {"user_id": "user-fixture", "provider": "provider-fixture"}

    def write(self, _frame):
        return True


def _serve_launch_profile(monkeypatch, tmp_path, launch: str):
    """Pin the launch profile and map profile requests to homes the way
    ``server._profile_home`` does: ``None`` for the launch home, else the home path."""
    monkeypatch.setattr("gateway.browser_control_broker.browser_control_enabled", lambda: True)
    monkeypatch.setattr(server, "_schedule_agent_build", lambda *a, **k: None)
    monkeypatch.setattr(server, "_schedule_session_cap_enforcement", lambda *a, **k: None)
    monkeypatch.setattr(server, "_completion_cwd", lambda params=None: str(tmp_path))
    monkeypatch.setattr(server, "_current_profile_name", lambda: launch)
    root = get_default_hermes_root()

    def home_for(name: str):
        return root if name == "default" else root / "profiles" / name

    launch_home = home_for(launch)

    def _profile_home(profile):
        name = (profile or "").strip()
        if not name:
            return None
        home = home_for(name)
        home.mkdir(parents=True, exist_ok=True)
        return None if home == launch_home else home

    monkeypatch.setattr(server, "_profile_home", _profile_home)


def _create_and_register(transport, requested_profile):
    params = {"cols": 80}
    if requested_profile is not None:
        params["profile"] = requested_profile
    created = server.dispatch(
        {"jsonrpc": "2.0", "id": 1, "method": "session.create", "params": params}, transport
    )
    session_id = created["result"]["session_id"]
    registration = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "browser.controller.register",
            "params": {
                "protocol_version": 1,
                "session_id": session_id,
                "controller_id": "controller-fixture",
                "browser_profile_id": "browser-profile-fixture",
                "capabilities": ["browser_navigate"],
            },
        },
        transport,
    )
    return session_id, registration


@pytest.mark.parametrize(
    ("launch", "sequence"),
    [
        pytest.param(
            "default", [(None, "default"), ("ops", "ops"), (None, "default")], id="launch-default"
        ),
        pytest.param(
            "work", [(None, "work"), ("default", "default"), ("ops", "ops")], id="launch-named"
        ),
    ],
)
def test_created_session_registers_with_its_canonical_profile(monkeypatch, tmp_path, launch, sequence):
    _serve_launch_profile(monkeypatch, tmp_path, launch)
    transport = _Transport()
    for requested_profile, expected in sequence:
        session_id, registration = _create_and_register(transport, requested_profile)
        try:
            assert "error" not in registration, (requested_profile, registration)
            assert registration["result"]["scope"]["profile_id"] == expected, requested_profile
        finally:
            get_browser_control_broker().reset()
            server._sessions.pop(session_id, None)


def test_cloud_scope_selects_the_local_api_artifact_store_slot(monkeypatch, tmp_path):
    """The local-API adapter attaches artifact stores keyed by profile NAME; a cloud
    scope for the same profile must resolve that slot, not miss it."""
    _serve_launch_profile(monkeypatch, tmp_path, "work")
    broker = get_browser_control_broker()
    stores = {name: object() for name in ("default", "work", "ops")}
    transport = _Transport()
    for requested_profile, expected in ((None, "work"), ("default", "default"), ("ops", "ops")):
        for name, store in stores.items():
            broker.attach_artifact_store(store, profile_id=name)
        session_id, registration = _create_and_register(transport, requested_profile)
        try:
            assert "error" not in registration, (requested_profile, registration)
            payload = registration["result"]["scope"]
            scope = broker.scope_for_session(
                session_id=session_id,
                principal_id=payload["principal_id"],
                transport_family=payload["transport_family"],
            )
            assert scope is not None
            assert broker._artifact_store_for_scope(scope) is stores[expected], requested_profile
        finally:
            for name in stores:
                broker.attach_artifact_store(None, profile_id=name)
            broker.reset()
            server._sessions.pop(session_id, None)
