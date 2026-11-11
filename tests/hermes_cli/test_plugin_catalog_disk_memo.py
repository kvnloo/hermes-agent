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
    monkeypatch.setattr(pc, "in_tree_catalog_time", lambda: None)

    with memo.guard_json_disk_memo_mutations():
        entries = pc.load_catalog_live()
        removed = pc.live_removed_list()
        assert [e.name for e in entries] == ["active"]
        assert [r.name for r in removed] == ["revoked"]
        assert pc._stale_live_cache(cache) == raw
        assert memo.json_disk_memo_parse_count() == 1


def test_stale_expiry_drops_entries_but_keeps_removed(tmp_path):
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


def test_external_equal_signature_replacement_updates_cached_plugin_kill_list(tmp_path, monkeypatch):
    import subprocess
    import sys

    cache = tmp_path / "plugin-catalog.json"
    old = {"entries": [], "removed": [{"name": "revoked-a"}]}
    new = {"entries": [], "removed": [{"name": "revoked-b"}]}
    old_payload, new_payload = json.dumps(old), json.dumps(new)
    assert len(old_payload) == len(new_payload)
    cache.write_text(old_payload, encoding="utf-8")
    baseline = cache.stat()
    monkeypatch.setattr(pc, "_live_cache_path", lambda: cache)
    monkeypatch.setattr(pc, "load_removed_list", lambda: [])
    assert [r.name for r in pc.cached_removed_entries()] == ["revoked-a"]

    writer = (
        "import os,sys; from pathlib import Path; "
        "p=Path(sys.argv[1]); t=p.with_suffix('.swap'); "
        "t.write_text(sys.argv[2],encoding='utf-8'); "
        "os.utime(t,ns=(int(sys.argv[3]),int(sys.argv[4]))); "
        "os.replace(t,p)"
    )
    subprocess.run(
        [sys.executable, "-c", writer, str(cache), new_payload,
         str(baseline.st_atime_ns), str(baseline.st_mtime_ns)],
        check=True, capture_output=True, text=True, timeout=20,
    )
    assert (cache.stat().st_mtime_ns, cache.stat().st_size) == (
        baseline.st_mtime_ns, baseline.st_size
    )
    assert [r.name for r in pc.cached_removed_entries()] == ["revoked-b"]
    assert [r.name for r in pc.live_removed_list()] == ["revoked-b"]


def test_production_plugin_cache_is_immutable_but_parsed_entries_are_independent(tmp_path, monkeypatch):
    cache = tmp_path / "plugin-catalog.json"
    raw = {"entries": [{"name": "stable", "repo": "https://github.com/a/b",
                        "sha": "a" * 40, "tier": "community",
                        "capabilities": {"provides_tools": ["tool"]}}],
           "removed": [{"name": "revoked"}]}
    cache.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(pc, "_live_cache_path", lambda: cache)
    monkeypatch.setattr(pc, "load_catalog", lambda *args, **kwargs: [])
    monkeypatch.setattr(pc, "in_tree_catalog_time", lambda: None)
    cache_view = pc.fetch_live_catalog()
    with pytest.raises(TypeError, match="read-only"):
        cache_view["removed"].clear()
    with pytest.raises(TypeError, match="read-only"):
        cache_view["entries"][0]["capabilities"]["provides_tools"].append("extra")
    assert [e.name for e in pc.load_catalog_live()] == ["stable"]
    assert [r.name for r in pc.live_removed_list()] == ["revoked"]
    assert pc._stale_live_cache(cache) == raw
