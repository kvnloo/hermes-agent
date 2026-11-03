"""Loopback cooperative-session handshake used by ``hermes --tui --resume``.

The route is intentionally not on ``PUBLIC_API_PATHS``: a gated public dashboard
must still require a session. Loopback token middleware lets this one path
through so a second local TUI can bootstrap before it has the dashboard token.

The lease id never travels: the requester proves it read the registry with
``client_proof`` and this owner answers with ``attach_proof``, both keyed on the
lease id (wire contract in ``hermes_cli.shared_session_attach``).
"""
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from hermes_cli.session_attach_runtime import advertised_shared_runtime_origin, peer_is_loopback

router = APIRouter()


def _lease_proof(lease_id: str, label: str, session_id: str, nonce: str) -> str:
    return hmac.new(str(lease_id).encode(), f"{label}:{session_id}:{nonce}".encode(),
                    hashlib.sha256).hexdigest()


@router.get("/api/session-attach")
def session_attach(request: Request, session_id: str, nonce: str, profile_home: str, client_proof: str):
    """Return the live gateway WebSocket URL only to a requester holding the owner lease's key."""
    client_host = request.client.host if request.client else ""
    if not peer_is_loopback(client_host):
        raise HTTPException(status_code=403, detail="Cooperative attachment is loopback-only")
    origin = advertised_shared_runtime_origin()
    if not origin:
        raise HTTPException(status_code=403, detail="Session owner does not support cooperative attachment")
    try:
        home = Path(profile_home).expanduser().resolve(strict=False)
        from hermes_cli.active_sessions import active_session_registry_snapshot

        owners = [entry for entry in active_session_registry_snapshot(home, strict=True)
                  if entry.get("session_id") == session_id]
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Active-session ownership is unavailable") from exc
    owner = owners[0] if len(owners) == 1 else {}
    lease_id = owner.get("lease_id")
    if (not lease_id or (owner.get("metadata") or {}).get("shared_runtime_url") != origin
            or not hmac.compare_digest(
                client_proof.encode("utf-8", "replace"),
                _lease_proof(lease_id, "hermes-session-attach-request", session_id, nonce).encode("ascii"))):
        raise HTTPException(status_code=403, detail="Session owner does not support cooperative attachment")
    from hermes_cli.web_server_chat import _build_gateway_ws_url

    websocket_url = _build_gateway_ws_url()
    if not websocket_url:
        raise HTTPException(status_code=503, detail="Shared runtime is not ready")
    return {
        "session_id": session_id,
        "nonce": nonce,
        "profile_home": str(home),
        "attach_proof": _lease_proof(lease_id, "hermes-session-attach", session_id, nonce),
        "websocket_url": websocket_url,
    }
