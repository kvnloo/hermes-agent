"""Canary for the r4 egress guard (factory-only; copied into a worktree as tests/agent/test_zz_chs_guard_canary.py
and run through scripts/run_tests.sh with the isolated HOME whose pytest_live_guard.py shim loads
tools/chs_egress_guard_r4.py). Each case proves one guard layer blocks and logs, that loopback still works,
and that r4 suppresses nothing: a thread named openrouter-prewarm starts and its lookup is logged with its name."""

import os
import socket
import sys
import threading

import pytest


def _guard():
    return sys.modules["chs_egress_guard_r4"]


def test_guard_loaded_from_isolated_home():
    guard = _guard()
    assert guard.GUARD_REVISION == "r4"
    assert guard._LOG.endswith(os.path.join("testhome-sf-compaction-hook-salvage", "chs-egress.log"))
    import pwd

    real_home = pwd.getpwuid(os.getuid()).pw_dir
    assert not os.path.realpath(guard._LOG).startswith(os.path.join(os.path.realpath(real_home), ".hermes"))


def test_non_loopback_connect_is_blocked():
    s = socket.socket()
    try:
        with pytest.raises(ConnectionRefusedError):
            s.connect(("1.1.1.1", 443))
    finally:
        s.close()


def test_non_loopback_dns_is_blocked():
    with pytest.raises(socket.gaierror):
        socket.getaddrinfo("example.com", 443)


def test_loopback_connect_and_dns_still_work():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    c = socket.socket()
    try:
        c.connect(srv.getsockname())
    finally:
        c.close()
        srv.close()
    assert socket.getaddrinfo("localhost", 80)


def test_openrouter_prewarm_thread_starts_and_its_lookup_is_logged():
    seen = []

    def lookup():
        try:
            socket.getaddrinfo("openrouter.ai", 443)
        except socket.gaierror as exc:
            seen.append(exc)

    t = threading.Thread(target=lookup, name="openrouter-prewarm", daemon=True)
    t.start()
    t.join(5)
    assert t.ident is not None and seen, "r4 must start the thread and block its lookup"
    with open(_guard()._LOG, encoding="utf-8") as fh:
        assert "dns\tgetaddrinfo('openrouter.ai')\tthread=openrouter-prewarm\n" in fh.read()
