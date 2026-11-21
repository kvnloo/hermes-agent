"""Guest ledger connections must inherit the configured database.synchronous.

apply_durability_barriers() is the guest-connection entry point (secondary
state.db users that must NOT touch journal mode). The configured
``database.synchronous`` level normally rides on apply_database_pragmas()
during the owner's journal-mode setup — a path guests deliberately skip — so
the guest entry point applies it directly.
"""

import sqlite3

import pytest

import hermes_state
from hermes_state_repair import apply_durability_barriers


def _config(monkeypatch, database_section):
    import hermes_cli.config as config_mod

    cfg = {"database": database_section}
    monkeypatch.setattr(config_mod, "load_config_readonly", lambda *a, **k: cfg)
    return cfg


def test_guest_barriers_apply_configured_synchronous(monkeypatch, tmp_path):
    _config(monkeypatch, {"synchronous": "FULL"})
    conn = sqlite3.connect(tmp_path / "state.db")
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=1")
        apply_durability_barriers(conn)
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2
        # And the journal mode was NOT touched — that is the whole contract.
        assert (
            str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            == "delete"
        )
    finally:
        conn.close()


def test_guest_barriers_leave_synchronous_alone_when_unset(monkeypatch, tmp_path):
    _config(monkeypatch, {})
    conn = sqlite3.connect(tmp_path / "state.db")
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=1")
        apply_durability_barriers(conn)
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1
    finally:
        conn.close()


def test_guest_barriers_survive_config_failure(monkeypatch, tmp_path):
    import hermes_cli.config as config_mod

    def _boom(*a, **k):
        raise RuntimeError("config unavailable")

    monkeypatch.setattr(config_mod, "load_config_readonly", _boom)
    conn = sqlite3.connect(tmp_path / "state.db")
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        # Must not raise; best-effort like every other pragma path.
        apply_durability_barriers(conn)
    finally:
        conn.close()


def test_guest_barriers_cache_config_per_home_and_file_revision(monkeypatch, tmp_path):
    """DbExecutor-style opens must not expand every config ref on every connection."""
    from concurrent.futures import ThreadPoolExecutor
    import hermes_cli.config as config_mod

    config_a = tmp_path / "profile-a" / "config.yaml"
    config_b = tmp_path / "profile-b" / "config.yaml"
    for path, value in ((config_a, "FULL"), (config_b, "FULL")):
        path.parent.mkdir()
        path.write_text(f"database:\n  synchronous: {value}\n")

    active_path = [config_a]
    loads = []

    def load_config():
        loads.append(active_path[0])
        value = active_path[0].read_text().split("synchronous:", 1)[1].strip()
        return {"database": {"synchronous": value}}

    monkeypatch.setattr(config_mod, "get_config_path", lambda: active_path[0])
    monkeypatch.setattr(config_mod, "load_config_readonly", load_config)

    def open_guest():
        conn = sqlite3.connect(tmp_path / "state.db")
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=0")
            apply_durability_barriers(conn)
            return conn.execute("PRAGMA synchronous").fetchone()[0]
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=1) as worker:
        assert [worker.submit(open_guest).result() for _ in range(20)] == [2] * 20
        assert loads == [config_a]  # Red on main: 20 reads instead of one.

        config_a.write_text("database:\n  synchronous: EXTRA\n")  # New size invalidates the signature.
        assert worker.submit(open_guest).result() == 3
        assert loads == [config_a, config_a]

        active_path[0] = config_b  # Same version value, different profile home.
        assert worker.submit(open_guest).result() == 2
        assert loads == [config_a, config_a, config_b]

        active_path[0] = config_a
        assert worker.submit(open_guest).result() == 3
        assert loads == [config_a, config_a, config_b]


def test_guest_barriers_cache_unset_synchronous_and_detect_new_config(monkeypatch, tmp_path):
    import hermes_cli.config as config_mod

    config_path = tmp_path / "new-profile" / "config.yaml"
    loads = []

    def load_config():
        loads.append(config_path)
        return {"database": {"synchronous": "EXTRA"}} if config_path.exists() else {"database": {}}

    monkeypatch.setattr(config_mod, "get_config_path", lambda: config_path)
    monkeypatch.setattr(config_mod, "load_config_readonly", load_config)

    for _ in range(20):
        conn = sqlite3.connect(tmp_path / "state.db")
        try:
            apply_durability_barriers(conn)
        finally:
            conn.close()
    assert loads == [config_path]  # No config file or database key: still one load.

    config_path.parent.mkdir()
    config_path.write_text("database:\n  synchronous: EXTRA\n")
    conn = sqlite3.connect(tmp_path / "state.db")
    try:
        apply_durability_barriers(conn)
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 3
    finally:
        conn.close()
    assert loads == [config_path, config_path]

