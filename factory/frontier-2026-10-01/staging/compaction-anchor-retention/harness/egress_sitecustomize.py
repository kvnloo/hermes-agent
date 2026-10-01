# Egress counter for sandboxed guard runs: records every non-loopback DNS lookup and connect attempt.
import os
import socket

_LOG = os.environ.get("EGRESS_LOG")
_LOOP = {None, "127.0.0.1", "::1", "localhost"}
_orig_connect = socket.socket.connect
_orig_gai = socket.getaddrinfo


def _rec(kind, target):
    if _LOG:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(f"{os.getpid()} {kind} {target}\n")


def _connect(self, address):
    if isinstance(address, tuple) and address[0] not in _LOOP:
        _rec("connect", address[:2])
    return _orig_connect(self, address)


def _getaddrinfo(host, *a, **k):
    h = host.decode() if isinstance(host, bytes) else host
    if h not in _LOOP:
        _rec("getaddrinfo", h)
    return _orig_gai(host, *a, **k)


socket.socket.connect = _connect
socket.getaddrinfo = _getaddrinfo
