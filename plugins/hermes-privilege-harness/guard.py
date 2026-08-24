"""Unprivileged typed requester for the external privilege broker."""

from __future__ import annotations

import json
import os
import socket
import struct


REQUEST_SOCK = os.environ.get("VIP_REQUEST_SOCK", "/var/run/hermes-vip/request.sock")
MAX_FRAME_SIZE = 64 * 1024


def build_request(operation_id: str, slots: dict, reason: str,
                  profile: str, session: str) -> dict:
    if not isinstance(operation_id, str) or not operation_id:
        raise ValueError("operation_id is required")
    if not isinstance(slots, dict) or not all(
        isinstance(name, str) and isinstance(value, (str, int, bool))
        for name, value in slots.items()
    ):
        raise ValueError("slots must contain typed scalar values")
    if not all(isinstance(value, str) for value in (reason, profile, session)):
        raise ValueError("reason and correlation fields must be strings")
    return {
        "type": "request",
        "operation_id": operation_id,
        "slots": slots,
        "reason": reason,
        "profile": profile,
        "session": session,
    }


def request(operation_id: str, slots: dict, reason: str = "",
            profile: str = "", session: str = "") -> str:
    payload = build_request(operation_id, slots, reason, profile, session)
    credential = os.environ.get("HERMES_PRIVILEGE_REQUESTER_TOKEN", "")
    if not credential:
        return json.dumps({"status": "error", "error": "requester credential is not configured"})
    envelope = {"credential": credential, "request": payload}
    encoded = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_FRAME_SIZE:
        return json.dumps({"status": "error", "error": "request is too large"})
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(10)
            client.connect(REQUEST_SOCK)
            client.sendall(struct.pack("!I", len(encoded)) + encoded)
            raw_size = _recv_exact(client, 4)
            size = struct.unpack("!I", raw_size)[0]
            if size > MAX_FRAME_SIZE:
                raise ValueError("broker response is too large")
            response = json.loads(_recv_exact(client, size).decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return json.dumps({"status": "error", "error": f"privilege broker unavailable: {exc}"})
    return json.dumps(response)


def check(tool_name: str, args: dict):
    if tool_name != "privilege_request":
        return None
    operation_id = args.get("operation_id", "") if isinstance(args, dict) else ""
    return {
        "action": "approve",
        "message": f"Submit privilege operation request: {operation_id[:80]}",
    }


def _recv_exact(client: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining:
        chunk = client.recv(remaining)
        if not chunk:
            raise ValueError("broker closed the connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
