"""Role-separated Linux Unix-socket transport."""

import json
import os
import socket
import struct
import threading
from pathlib import Path

from .broker import BrokerError, PeerIdentity

MAX_FRAME_SIZE = 65536


def peer_identity(client, _role):
    raw = client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    pid, uid, _gid = struct.unpack("3i", raw)
    fields = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").split()
    return PeerIdentity(uid, pid, int(fields[21]))


def _recv(client):
    size = struct.unpack("!I", _exact(client, 4))[0]
    if size > MAX_FRAME_SIZE:
        raise ValueError("frame too large")
    value = json.loads(_exact(client, size).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("frame must be an object")
    return value


def _send(client, value):
    payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
    client.sendall(struct.pack("!I", len(payload)) + payload)


def _exact(client, size):
    chunks = []
    while size:
        chunk = client.recv(size)
        if not chunk:
            raise ConnectionError("connection closed")
        chunks.append(chunk)
        size -= len(chunk)
    return b"".join(chunks)


def call(path, envelope):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(str(path))
        _send(client, envelope)
        return _recv(client)


class SocketServer:
    def __init__(self, broker, request_path, operator_path, decision_timeout: float = 15, identity=peer_identity):
        self.broker = broker
        self.request_path = Path(request_path)
        self.operator_path = Path(operator_path)
        self.decision_timeout = decision_timeout
        self.identity = identity
        self.running = False
        self.listeners = []

    def start(self):
        self.running = True
        for path, role in ((self.request_path, "requester"), (self.operator_path, "operator")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.unlink(missing_ok=True)
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(path))
            os.chmod(path, 0o600)
            listener.listen(16)
            listener.settimeout(0.1)
            self.listeners.append(listener)
            threading.Thread(target=self._serve, args=(listener, role), daemon=True).start()

    def stop(self):
        self.running = False
        for listener in self.listeners:
            listener.close()
        self.request_path.unlink(missing_ok=True)
        self.operator_path.unlink(missing_ok=True)

    def _serve(self, listener, role):
        while self.running:
            try:
                client, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._handle, args=(client, role), daemon=True).start()

    def _handle(self, client, role):
        with client:
            try:
                peer = self.identity(client, role)
                envelope = _recv(client)
                if set(envelope) != {"credential", "request"}:
                    raise ValueError("invalid envelope")
                credential = envelope["credential"]
                message = envelope["request"]
                if not isinstance(credential, str) or not isinstance(message, dict):
                    raise ValueError("invalid envelope")
                response = self._request(peer, credential, message) if role == "requester" else self._operator(peer, credential, message)
            except (BrokerError, ConnectionError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
                response = {"status": "error", "error": str(exc)}
            _send(client, response)

    def _request(self, peer, credential, message):
        required = {"type", "operation_id", "slots", "reason", "profile", "session"}
        if set(message) != required or message["type"] != "request":
            raise ValueError("typed requests only")
        pending = self.broker.request(
            peer=peer, credential=credential, operation_id=message["operation_id"],
            slots=message["slots"], reason=message["reason"], profile=message["profile"],
            session=message["session"],
        )
        return self.broker.await_result(pending["request_id"], self.decision_timeout)

    def _operator(self, peer, credential, message):
        if message == {"type": "list"}:
            return {"status": "ok", "pending": self.broker.list_pending(peer=peer, credential=credential)}
        if set(message) == {"type", "request_id", "decision"} and message["type"] == "decide":
            return self.broker.decide(message["request_id"], message["decision"], peer=peer, credential=credential)
        raise ValueError("operator endpoint accepts list or decide only")
