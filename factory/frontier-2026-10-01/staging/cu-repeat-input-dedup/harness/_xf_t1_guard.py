"""xf T1 guard (pytest plugin, never committed): loopback-only sockets + seam observation.

Lifted from evals/provider_fallback/probe_104260.py:11-39 (loopback-only connect guard).
Adds a passive sys.setprofile observer that counts calls to the dedup seam (no patching).
Writes $HOME/xf_guard/<pid>.json at session end.
"""
import json
import os
import socket
import sys
import threading
from pathlib import Path

_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_blocked = []
_loopback_connects = [0]
_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _check(address):
    if isinstance(address, tuple):
        if address[0] not in _LOOPBACK:
            _blocked.append(str(address))
            raise OSError("xf T1 guard: non-loopback connect blocked")
        _loopback_connects[0] += 1


def _connect(self, address):
    _check(address)
    return _orig_connect(self, address)


def _connect_ex(self, address):
    _check(address)
    return _orig_connect_ex(self, address)


socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex

_TARGETS = {
    ("tool_dispatch_helpers.py", "deduplicate_tool_calls"),
    ("tool_dispatch_helpers.py", "_is_order_significant"),
    ("tool_dispatch_helpers.py", "_peel_bridge_call"),
    ("run_agent.py", "_deduplicate_tool_calls"),
    ("turn_tool_round.py", "run_tool_round"),
    ("tool.py", "handle_computer_use"),
}
_hits = {}


def _prof(frame, event, arg):
    if event == "call":
        co = frame.f_code
        k = (os.path.basename(co.co_filename), co.co_name)
        if k in _TARGETS:
            _hits["%s::%s" % k] = _hits.get("%s::%s" % k, 0) + 1


sys.setprofile(_prof)
threading.setprofile(_prof)

_CRED_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH")
_env_at_start = sorted(k for k in os.environ if any(h in k.upper() for h in _CRED_HINTS))


def pytest_sessionfinish(session, exitstatus):
    out = Path(os.environ.get("HOME", "/nonexistent")) / "xf_guard"
    out.mkdir(parents=True, exist_ok=True)
    (out / ("%d.json" % os.getpid())).write_text(json.dumps({
        "args": [str(a) for a in session.config.args],
        "exitstatus": int(exitstatus),
        "egress_blocked": _blocked,
        "loopback_connects": _loopback_connects[0],
        "seam_hits": _hits,
        "credential_like_env_at_start": _env_at_start,
        "hermes_home_at_end": os.environ.get("HERMES_HOME"),
    }, indent=1), encoding="utf-8")
