"""Plugin live-catalog no-copy memo: guarded reads, expiry, and invalidation."""

from __future__ import annotations

import json
import os
import time

import pytest

import json_disk_memo as memo
from hermes_cli import plugin_catalog as pc


@pytest.fixture(autouse=True)
def _fresh_memo():
    memo.clear_json_disk_memo()
    yield
    memo.clear_json_disk_memo()


def test_fresh_and_stale_readers_share_object_and_guard_mutations(tmp_path, monkeypatch):
    cache = tmp_path / "plugin-catalog.json"
    raw = {"entries": [{"name": "active"}], "removed": [{"name": "revoked"}]}
    cache.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(pc, "_live_cache_path", lambda: cache)

    with memo.guard_json_disk_memo_mutations():
        fresh = pc.fetch_live_catalog()
        stale = pc._stale_live_cache(cache)
        assert fresh is stale
        assert fresh == raw
        with pytest.raises(TypeError, match="read-only"):
            fresh["entries"][0]["name"] = "mutated"
        with pytest.raises(TypeError, match="read-only"):
            stale["removed"].clear()
        assert pc._stale_live_cache(cache) is stale
        assert memo.json_disk_memo_parse_count() == 1


def test_parsing_catalog_entries_and_removals_does_not_mutate_cache(tmp_path, monkeypatch):
    cache = tmp_path / "plugin-catalog.json"
    entry = {"name": "active", "repo": "https://github.com/owner/repo",
             "sha": "a" * 40, "tier": "community",
             "capabilities": {"provides_tools": ["tool"]}}
    raw = {"entries": [entry], "removed": [{"name": "revoked"}]}
    cache.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(pc, "_live_cache_path", lambda: cache)
    monkeypatch.setattr(pc, "load_catalog", lambda *args, **kwargs: [])

    with memo.guard_json_disk_memo_mutations():
        entries = pc.load_catalog_live()
        removed = pc.live_removed_list()
        assert [e.name for e in entries] == ["active"]
        assert [r.name for r in removed] == ["revoked"]
        assert pc._stale_live_cache(cache) == raw
        assert memo.json_disk_memo_parse_count() == 1

ef test_stale_expiry_drops_entries_but_keeps_removed(tmp_path):
    cache = tmp_path / "plugin-catalog.json"
    raw = {"entries": [{"name": "expired"}], "removed": [{"name": "revoked"}]}
    cache.write_text(json.dumps(raw), encoding="utf-8")
    old_ns = int((time.time() - pc.LIVE_CATALOG_MAX_STALE_SECONDS - 60) * 1_000_000_000)
    os.utime(cache, ns=(old_ns, old_ns))

    assert pc._stale_live_cache(cache) == {"entries": [], "removed": raw["removed"]}


def test_explicit_invalidation_handles_same_signature_recreation(tmp_path):
    cache = tmp_path / "cache" / "plugin-catalog.json"
    cache.parent.mkdir()
    old = {"entries": [{"name": "one"}], "removed": []}
    new = {"entries": [{"name": "two"}], "removed": []}
    old_json, new_json = json.dumps(old), json.dumps(new)
    assert len(old_json) == len(new_json)
    fixed_ns = time.time_ns() - 2_000_000_000

    cache.write_text(old_json, encoding="utf-8")
    os.utime(cache, ns=(fixed_ns, fixed_ns))
    assert pc._stale_live_cache(cache) == old

    pc.invalidate_live_cache_for_home(tmp_path)
    assert not cache.exists()
    cache.write_text(new_json, encoding="utf-8")
    os.utime(cache, ns=(fixed_ns, fixed_ns))

    assert pc._stale_live_cache(cache) == new


def test_malformed_stale_cache_stays_fallback_and_recovers(tmp_path):
    cache = tmp_path / "plugin-catalog.json"
    cache.write_text('{"entries":', encoding="utf-8")
    assert pc._stale_live_cache(cache) is None

    corrected = {"entries": [], "removed": [{"name": "revoked"}]}
    cache.write_text(json.dumps(corrected), encoding="utf-8")
    assert pc._stale_live_cache(cache) == corrected
