"""Canary for the r3 egress guard (factory-only; copied into a worktree as tests/agent/test_zz_chs_guard_canary.py
and run through scripts/run_tests.sh with the isolated HOME whose pytest_live_guard.py shim loads
tools/chs_egress_guard.py). Each case proves one guard layer blocks, and that loopback still works."""

import os
import socket
import sys
import threading

import pytest


def _guard():
    return sys.modules["chs_egress_guard"]


def test_guard_loaded_from_isolated_home():
    guard = _guard()
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


def test_openrouter_prewarm_thread_is_not_started():
    t = threading.Thread(target=lambda: None, name="openrouter-prewarm", daemon=True)
    t.start()
    assert t.ident is None and not t.is_alive()
    other = threading.Thread(target=lambda: None, name="unrelated", daemon=True)
    other.start()
    other.join(5)
    assert other.ident is not None
