"""Egress guard v2 for the compaction-hook-salvage factory runs (supersedes chs_loopback_guard.py).

Loaded as a pytest plugin through the isolated test HOME's pytest_live_guard.py shim (scripts/run_tests.sh
adds it when $HOME/.hermes/pytest_live_guard.py exists), or imported by chs_guard_wrap.py.

* socket.connect / connect_ex to any non-loopback address is refused and logged as ``connect``.
* socket.getaddrinfo / gethostbyname / gethostbyname_ex / gethostbyaddr for any non-loopback name is
  refused (socket.gaierror) and logged as ``dns``. v1 guarded connect() only, so DNS lookups still left
  the process.
* The ``openrouter-prewarm`` daemon thread (agent/agent_init.py: a process-level once-guarded metadata
  GET that AIAgent starts whenever base_url is OpenRouter's) is not started and is logged as
  ``prewarm_suppressed``. It is unrelated to compaction and was the only source of the v1 blocked connects.

Under FACTORY S16 every ``connect`` or ``dns`` line fails its cell as INFRA. ``prewarm_suppressed`` lines
are a prevention, not a blocked attempt, and are counted separately.

The log path is fixed at import (before any test fixture can repoint HOME): $HOME/chs-egress.log, i.e. the
isolated test HOME's root. It is deliberately not under $HOME/.hermes, which tests/home_io_guard.py refuses
as the "real" hermes home. If $HOME/chs-egress.stacks-on exists, a stack per line goes to chs-egress.stacks.
"""

import os
import socket
import threading
import traceback

_LOG = os.path.join(os.path.expanduser("~"), "chs-egress.log")
_STACKS = os.path.exists(_LOG.replace(".log", ".stacks-on"))
_LOOPBACK_ADDRS = {"127.0.0.1", "::1", "localhost", "0.0.0.0", "::"}


def _log(kind, detail):
    # Never swallow: a log write that fails must surface rather than hide a blocked attempt.
    with open(_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{kind}\t{detail}\n")
    if _STACKS:
        with open(_LOG.replace(".log", ".stacks"), "a", encoding="utf-8") as fh:
            fh.write(f"{kind}\t{detail}\n" + "".join(traceback.format_stack(limit=30)) + "----\n")


def _is_loopback_host(host):
    if host is None or host == "" or host in _LOOPBACK_ADDRS:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    return isinstance(host, str) and (host.startswith("127.") or host.endswith(".localhost"))


_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _check_addr(address):
    if isinstance(address, tuple) and address and not _is_loopback_host(address[0]):
        _log("connect", repr(address[:2]))
        raise ConnectionRefusedError("chs egress guard: non-loopback connect blocked")


def _connect(self, address):
    _check_addr(address)
    return _orig_connect(self, address)


def _connect_ex(self, address):
    _check_addr(address)
    return _orig_connect_ex(self, address)


socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex


def _dns_guard(fn_name):
    original = getattr(socket, fn_name)

    def guarded(host, *args, **kwargs):
        if not _is_loopback_host(host):
            _log("dns", f"{fn_name}({host!r})")
            raise socket.gaierror(socket.EAI_NONAME, "chs egress guard: non-loopback DNS lookup blocked")
        return original(host, *args, **kwargs)

    guarded.__name__ = original.__name__
    setattr(socket, fn_name, guarded)


for _fn in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
    _dns_guard(_fn)

_orig_thread_start = threading.Thread.start


def _thread_start(self):
    if self.name == "openrouter-prewarm":
        _log("prewarm_suppressed", "agent_init openrouter-prewarm thread not started")
        return None
    return _orig_thread_start(self)


threading.Thread.start = _thread_start
