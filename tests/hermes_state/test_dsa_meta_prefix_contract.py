"""Legacy LIKE prefix contract and indexed-seek differential tests for state_meta."""

import json
import random

import pytest

from hermes_state import SessionDB
from hermes_state_common import escape_like


@pytest.fixture
def db(tmp_path):
    state = SessionDB(db_path=tmp_path / "state.db")
    yield state
    state.close()


def _legacy_scan(db: SessionDB, prefix: str) -> list[tuple[str, str]]:
    """Original LIKE predicate on a table scan, including its rowid ordering."""
    if not prefix:
        return []
    rows = db._read_all(
        "SELECT key, value FROM state_meta NOT INDEXED WHERE key LIKE ? ESCAPE '\\'",
        (escape_like(prefix) + "%",),
    )
    return [(row[0], row[1]) for row in rows]


def test_legacy_contract_literals_case_and_order(db):
    escaped_path = json.dumps({"path": r"C:\dir\file.txt", "emoji": "🧪"}, ensure_ascii=True)
    pairs = [
        ("other:first", "outside"),
        ("loop:z", "first"),
        ("LOOP:Alpha", "ascii-case"),
        ("loop:a", "lower"),
        ("LoOp:%", "percent"),
        ("loop:_", "underscore"),
        ("loop:\\", "backslash"),
        ("loop:" + escaped_path, "json-path"),
        ("loop:🧪", "non-bmp"),
        ("loop:\U0010ffff", "max-unicode"),
        ("loop:\U0010ffff-tail", "max-unicode-tail"),
        ("another:loop:mark", "outside"),
    ]
    for key, value in pairs:
        db.set_meta(key, value)
    db.set_meta("LoOp:%", "updated")  # UPSERT must not move an existing row.

    expected = [
        (key, "updated" if key == "LoOp:%" else value)
        for key, value in pairs
        if key[:5].lower() == "loop:"
    ]
    assert db.list_meta_prefix("") == []
    assert db.list_meta_prefix("loop:") == expected
    assert db.list_meta_prefix("LOOP:") == expected
    assert db.list_meta_prefix("loop:%") == [("LoOp:%", "updated")]
    assert db.list_meta_prefix("loop:_") == [("loop:_", "underscore")]
    assert db.list_meta_prefix("loop:\\") == [("loop:\\", "backslash")]
    assert db.list_meta_prefix("loop:" + escaped_path) == [("loop:" + escaped_path, "json-path")]
    assert db.list_meta_prefix("loop:\U0010ffff") == [
        ("loop:\U0010ffff", "max-unicode"),
        ("loop:\U0010ffff-tail", "max-unicode-tail"),
    ]
    assert db.list_meta_prefix("not-present:") == []


def test_generated_old_vs_indexed_same_rows_and_order(db):
    rng = random.Random(1107)
    roots = ("loop:", "LOOP:", "Loop:", "other:", "meta:", "")
    chars = ("a", "A", "z", "Z", "%", "_", "\\", "/", "🧪", "é", "\U0010ffff", "{", "}", '"')
    keys = []
    for i in range(380):
        key = rng.choice(roots) + "".join(rng.choice(chars) for _ in range(rng.randrange(7)))
        keys.append(key)
        value = json.dumps({"n": i, "path": r"C:\cache\path", "emoji": "🧪"}, ensure_ascii=i % 2 == 0)
        db.set_meta(key, value)
        if i % 13 == 0:
            db.set_meta(key, value + "-upsert")

    escaped_path = json.dumps({"path": r"C:\dir\file.txt"}, ensure_ascii=True)
    probes = {
        "", "loop:", "LOOP:", "lOoP:", "loop:%", "loop:_", "loop:\\",
        "loop:\U0010ffff", "loop:🧪", "loop:é", "loop:" + escaped_path,
        "other:", "missing:", "Z", "\U0010ffff",
    }
    probes.update(key[:rng.randrange(len(key) + 1)] for key in keys[:130])
    for prefix in sorted(probes):
        assert db.list_meta_prefix(prefix) == _legacy_scan(db, prefix), repr(prefix)


def test_explain_uses_nocase_search_for_real_list_query(db, monkeypatch):
    for i in range(40):
        db.set_meta(f"other:{i:04d}", str(i))
    db.set_meta("LOOP:seek", "value")
    captured = []
    original = db._read_all

    def recording_read(sql, params=()):
        captured.append((sql, params))
        return original(sql, params)

    monkeypatch.setattr(db, "_read_all", recording_read)
    assert db.list_meta_prefix("loop:se") == [("LOOP:seek", "value")]
    sql, params = captured[-1]
    assert "INDEXED BY idx_state_meta_key_nocase" in sql
    plan = db._conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    assert any(
        "SEARCH state_meta USING INDEX idx_state_meta_key_nocase" in row[3]
        for row in plan
    ), [row[3] for row in plan]


def test_uppercase_loop_key_remains_visible_to_fail_closed_guard(db):
    from hermes_cli.loops import store_has_active_loop

    db.set_meta("LOOP:orphan", "{invalid-json")
    assert store_has_active_loop(db) is True


def test_readonly_legacy_database_without_companion_index(tmp_path):
    path = tmp_path / "legacy.db"
    writable = SessionDB(db_path=path)
    try:
        writable.set_meta("LOOP:old", "still-visible")
        with writable._lock:
            writable._conn.execute("DROP INDEX idx_state_meta_key_nocase")
            writable._conn.commit()
    finally:
        writable.close()

    readonly = SessionDB(db_path=path, read_only=True)
    try:
        assert readonly.list_meta_prefix("loop:") == [("LOOP:old", "still-visible")]
    finally:
        readonly.close()


def test_ascii_z_successor_and_nul_fallback(db):
    """Z must advance past NOCASE 'z', not to '[' (which sorts before z)."""
    pairs = (
        ('LOOP:a"ZZAa', "upper-z"),
        ('loop:A"z%tail', "mixed-case-percent"),
        ('LOOP:a"[tail', "bracket-is-not-z"),
        ("LOOP:éZtail", "unicode-z"),
        ("loop:é[tail", "unicode-bracket"),
        ("LOOP:%Zrest", "literal-percent"),
        ("loop:_Zrest", "literal-underscore"),
        (r"LOOP:\Zrest", "literal-backslash"),
        ("LOOP:\x00tail", "embedded-nul"),
    )
    for key, value in pairs:
        db.set_meta(key, value)

    assert db.list_meta_prefix('LOOP:a"Z') == [
        ('LOOP:a"ZZAa', "upper-z"),
        ('loop:A"z%tail', "mixed-case-percent"),
    ]
    for prefix in (
        'LOOP:a"Z', 'LOOP:a"[', "loop:z", "loop:{", "LOOP:éZ",
        "loop:é[", "loop:%Z", "loop:_Z", r"LOOP:\Z", "LOOP:\x00tail",
    ):
        assert db.list_meta_prefix(prefix) == _legacy_scan(db, prefix), repr(prefix)
