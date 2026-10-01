"""Loopback-only socket guard for the compaction-hook-salvage factory runs (lifted from
evals/provider_fallback/probe_104260.py). Imported by the isolated test HOME's pytest_live_guard.py
shim, which scripts/run_tests.sh loads as a pytest plugin. Every blocked attempt is appended to
raw/egress_blocked.log next to this tools/ directory."""
import os
import socket
import traceback

_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw", "egress_blocked.log")
_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _check(address):
    if isinstance(address, tuple) and address and address[0] not in _LOOPBACK:
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(repr(address) + "\n")
        if os.environ.get("CHS_GUARD_STACKS") or os.path.exists(_LOG + ".stacks-on"):
            with open(_LOG + ".stacks", "a", encoding="utf-8") as fh:
                fh.write(repr(address) + "\n" + "".join(traceback.format_stack(limit=40)) + "\n----\n")
        raise ConnectionRefusedError("chs loopback guard: non-loopback connect blocked")


def _connect(self, address):
    _check(address)
    return _orig_connect(self, address)


def _connect_ex(self, address):
    _check(address)
    return _orig_connect_ex(self, address)


socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
