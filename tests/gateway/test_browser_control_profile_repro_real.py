"""Regression coverage for the cloud ``browser.controller.register`` profile_id bug.

The ``browser.controller.register`` handler on the authenticated ``/api/ws``
gateway previously derived its ``profile_id`` from ``session.get("profile")`` —
a key that **no** production live-session builder ever stamps. The three
constructors that populate ``_sessions`` (``session.create``,
``server._init_session``, ``server._deferred_session_record``) stamp
``profile_home`` (a filesystem path) and never a bare ``profile`` name, so the
handler deterministically rejected every real registration with
``4403 "controller_id, browser_profile_id, and server session profile are required"``.

These tests build sessions through the **real** ``_init_session`` builder (not
the hand-rolled ``_sessions`` fixtures in ``test_browser_control_cloud.py``)
and lock in the fix's contract:

* registration against a production-built session succeeds (no 4403) with the
  profile **name** (``Path(profile_home).name``) as ``profile_id`` — NOT the
  filesystem path — matching the local-API adapter and the shared, name-keyed
  artifact-store slots the local-API upload route populates;
* a launch-profile session (``profile_home=None``) falls back to ``"default"``;
* a stale ``"profile"`` key on the record is ignored — ``profile_home`` is the
  single source of truth.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from gateway.browser_control_broker import get_browser_control_broker
from tui_gateway import server


def _neutralize_init_session_wiring(monkeypatch):
    """Stub the post-construction side effects of ``_init_session``.

    Only the session-**dict construction** at the top of ``_init_session`` (the
    part that stamps ``profile_home`` and omits ``profile``) is allowed to run;
    every downstream effect (DB I/O, notification poller, approval wiring,
    session.info emit, mcp refresh, cwd registration) is neutralized, mirroring
    the ``test_init_session_fires_reset_hook`` /
    ``test_named_profile_session_db`` patterns.
    """
    monkeypatch.setattr(server, "_open_profile_session_db", lambda _home: None)
    monkeypatch.setattr(server, "_register_session_cwd", lambda _s: None)
    monkeypatch.setattr(server, "_wire_callbacks", lambda _sid: None)
    monkeypatch.setattr(
        server, "_start_notification_poller", lambda _sid, _s: threading.Event()
    )
    monkeypatch.setattr(server, "_notify_session_boundary", lambda *a, **kw: None)
    monkeypatch.setattr(server, "_emit", lambda *a, **kw: None)
    monkeypatch.setattr(server, "_session_info", lambda _agent, _s=None: {})
    monkeypatch.setattr(server, "_schedule_mcp_late_refresh", lambda _sid, _agent: None)
    monkeypatch.setattr(server, "_load_show_reasoning", lambda: False)
    monkeypatch.setattr(server, "_load_tool_progress_mode", lambda: "off")
    monkeypatch.setattr(server, "_load_memory_notifications", lambda: "off")


class _Transport:
    """Minimal WS transport: carries a server-minted identity and records writes."""

    def __init__(self, *, user_id="user-repro", provider="provider-repro"):
        self.auth_identity = {"user_id": user_id, "provider": provider}
        self.frames = []

    def write(self, frame):
        self.frames.append(frame)
        return True


def _enable_browser_control(monkeypatch):
    monkeypatch.setattr(
        "gateway.browser_control_broker.browser_control_enabled", lambda: True
    )


def _register_frame(session_id, *, controller_id="controller-repro", capabilities=None):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "browser.controller.register",
        "params": {
            "protocol_version": 1,
            "session_id": session_id,
            "controller_id": controller_id,
            "browser_profile_id": "browser-profile-repro",
            "capabilities": capabilities if capabilities is not None else ["browser_navigate"],
        },
    }


def test_register_succeeds_against_real_init_session(monkeypatch, tmp_path):
    """Build a session via the real ``_init_session`` (which stamps
    ``profile_home`` and omits ``profile``), then dispatch a real
    ``browser.controller.register`` frame through ``server.dispatch``.

    Before the fix the handler returned 4403 because ``session.get("profile")``
    was None. After the fix it derives ``profile_id`` from
    ``Path(profile_home).name`` and succeeds.
    """
    _enable_browser_control(monkeypatch)
    _neutralize_init_session_wiring(monkeypatch)
    broker = get_browser_control_broker()
    broker.reset()
    sid = "sid-repro-real"
    profile_home = str(tmp_path / "profiles" / "coder")
    transport = _Transport()
    token = server.bind_transport(transport)
    server._init_session(
        sid,
        "session-key-repro",
        None,
        [],
        cols=80,
        profile_home=profile_home,
    )
    try:
        assert "profile" not in server._sessions[sid]
        response = server.dispatch(_register_frame(sid), transport)
        assert "result" in response, response
        scope = response["result"]["scope"]
        assert scope["controller_id"] == "controller-repro"
        assert scope["transport_family"] == "cloud-ticket-ws"
        # profile_id is the profile NAME (Path(profile_home).name == "coder"),
        # not the filesystem path and not "".
        assert scope["profile_id"] == "coder"
        assert scope["profile_id"] != profile_home
    finally:
        server.reset_transport(token)
        server._sessions.pop(sid, None)
        broker.reset()


def test_register_falls_back_to_default_when_profile_home_absent(monkeypatch):
    """A launch-profile session (``profile_home=None``) derives ``profile_id``
    as "default", matching the local-API adapter's ``profile or "default"``."""
    _enable_browser_control(monkeypatch)
    _neutralize_init_session_wiring(monkeypatch)
    broker = get_browser_control_broker()
    broker.reset()
    sid = "sid-launch-profile"
    transport = _Transport()
    token = server.bind_transport(transport)
    server._init_session(sid, "session-key-launch", None, [], cols=80)
    try:
        assert server._sessions[sid].get("profile_home") is None
        response = server.dispatch(_register_frame(sid), transport)
        assert "result" in response, response
        assert response["result"]["scope"]["profile_id"] == "default"
    finally:
        server.reset_transport(token)
        server._sessions.pop(sid, None)
        broker.reset()


def test_cloud_profile_id_hits_local_api_artifact_store_slot(monkeypatch, tmp_path):
    """The cloud scope's ``profile_id`` must be the profile NAME because the
    shared broker's ``_artifact_stores`` map is populated only by the local-API
    adapter, keyed by profile NAME (``attach_artifact_store(store,
    profile_id="coder")``). A path-valued cloud ``profile_id`` would miss the
    slot and silently break every cloud artifact upload/download.

    Locks in the "name, not path" choice: a cloud scope and a local-API store
    registered under the same profile name resolve to the same store, while a
    path-valued ``profile_id`` misses.
    """
    _enable_browser_control(monkeypatch)
    _neutralize_init_session_wiring(monkeypatch)
    broker = get_browser_control_broker()
    broker.reset()
    sid = "sid-parity"
    profile_home = str(tmp_path / "profiles" / "coder")
    transport = _Transport()
    token = server.bind_transport(transport)
    server._init_session(sid, "session-key-parity", None, [], cols=80, profile_home=profile_home)
    try:
        response = server.dispatch(_register_frame(sid), transport)
        scope_payload = response["result"]["scope"]
        assert scope_payload["profile_id"] == "coder"

        scope = broker.scope_for_session(
            session_id=sid,
            principal_id=scope_payload["principal_id"],
            transport_family="cloud-ticket-ws",
        )
        assert scope is not None
        assert scope.profile_id == "coder"

        # The local-API adapter attaches its store under the profile NAME.
        local_api_store = SimpleNamespace(name="local-api-store-for-coder")
        broker.attach_artifact_store(local_api_store, profile_id="coder")
        # The cloud scope resolves to that NAME-keyed store, not the None slot.
        assert broker._artifact_store_for_scope(scope) is local_api_store

        # A path-valued profile_id would miss and fall through to the None slot,
        # which in production is empty — silently breaking artifact actions.
        from gateway.browser_control_broker import ControllerScope

        would_be_path = ControllerScope(
            principal_id=scope.principal_id,
            profile_id=profile_home,  # the WRONG (path) value
            session_id=scope.session_id,
            controller_id=scope.controller_id,
            browser_profile_id=scope.browser_profile_id,
            transport_family=scope.transport_family,
            capabilities=scope.capabilities,
        )
        assert profile_home not in broker._artifact_stores
        assert broker._artifact_store_for_scope(would_be_path) is None
    finally:
        server.reset_transport(token)
        server._sessions.pop(sid, None)
        broker.reset()


def test_register_derives_profile_id_from_profile_home_even_if_profile_key_present(
    monkeypatch, tmp_path
):
    """After the fix ``profile_id`` comes from ``profile_home``. A stale
    ``"profile"`` key (if any caller still stamped one) must NOT take
    precedence — ``profile_home`` is the single source of truth, matching the
    production builders."""
    _enable_browser_control(monkeypatch)
    broker = get_browser_control_broker()
    broker.reset()
    sid = "sid-stale-key"
    profile_home = str(tmp_path / "profiles" / "real-name")
    transport = _Transport()
    server._sessions[sid] = {
        "transport": transport,
        "session_key": "session-key-stale",
        "profile_home": profile_home,
        "profile": "stale-different-name",  # must be ignored by the fix
    }
    try:
        response = server.dispatch(_register_frame(sid), transport)
        assert "result" in response, response
        # Derived from profile_home, not the stale "profile" key.
        assert response["result"]["scope"]["profile_id"] == "real-name"
    finally:
        server._sessions.pop(sid, None)
        broker.reset()
