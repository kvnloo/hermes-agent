"""Pure cache tests reused from DSH agent commit 3e762e9d8f2f.

Manager integration from that branch is intentionally not ported into this study.
"""

import threading


import time


import pytest


from agent.memory_packet_cache import (
    FRESH,
    MISS,
    POLICY_VERSION,
    STALE,
    MemoryPacketCache,
    cache_key,
    make_scope,
    normalize_query,
)


def test_scope_none_and_empty_string_do_not_collide():
    a = make_scope(provider="p", tenant=None, session_id="s")
    b = make_scope(provider="p", tenant="", session_id="s")
    assert a != b


def test_scope_separator_in_value_cannot_forge_another_scope():
    a = make_scope(provider="p", tenant="x|y", session_id="s")
    b = make_scope(provider="p", tenant="x", session_id="y|s")
    assert a != b


def test_normalize_query_collapses_whitespace_and_case_only():
    assert normalize_query("  Hello   World ") == "hello world"
    # Wording differences are preserved: merging them would serve wrong memories.
    assert normalize_query("hello world") != normalize_query("world hello")


def test_cache_key_carries_policy_version():
    scope = make_scope(provider="p", tenant="t", session_id="s")
    assert cache_key(scope, "q", policy_version="v1") != cache_key(scope, "q", policy_version="v2")


def test_scope_isolation_between_tenants_sessions_and_workspaces():
    cache = MemoryPacketCache()
    scopes = [
        make_scope(provider="p", tenant="t1", session_id="s"),
        make_scope(provider="p", tenant="t2", session_id="s"),
        make_scope(provider="p", tenant="t1", session_id="s2"),
        make_scope(provider="p", tenant="t1", session_id="s", workspace="w1"),
        make_scope(provider="q", tenant="t1", session_id="s"),
    ]
    keys = [cache_key(s, "same query") for s in scopes]
    assert len(set(keys)) == len(scopes)

    cache.put(keys[0], scope=scopes[0], provider="p", text="tenant-one secret")
    for other in keys[1:]:
        assert cache.lookup(other).state == MISS
    assert cache.lookup(keys[0]).text == "tenant-one secret"


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _cache():
    clock = Clock()
    return MemoryPacketCache(fresh_ttl_s=30.0, stale_ttl_s=300.0, clock=clock), clock


def test_cold_cache_is_a_miss():
    cache, _ = _cache()
    result = cache.lookup("absent")
    assert result.state == MISS
    assert result.text == ""
    assert result.packet is None
    assert not result.served_from_cache


def test_fresh_packet_is_served_without_remote_work():
    cache, clock = _cache()
    cache.put("k", scope="s", provider="p", text="remembered")
    result = cache.lookup("k")
    assert result.state == FRESH
    assert result.text == "remembered"
    assert result.served_from_cache
    assert not result.stale_but_allowed
    assert result.age_s == 0.0
    assert result.describe()["memory_tokens_injected"] > 0


def test_stale_packet_is_served_and_flagged_as_stale_but_allowed():
    cache, clock = _cache()
    cache.put("k", scope="s", provider="p", text="older answer")
    clock.advance(31.0)
    result = cache.lookup("k")
    assert result.state == STALE
    assert result.text == "older answer"
    assert result.stale_but_allowed
    assert result.age_s == pytest.approx(31.0)


def test_packet_expires_past_the_stale_window():
    cache, clock = _cache()
    cache.put("k", scope="s", provider="p", text="ancient")
    clock.advance(301.0)
    result = cache.lookup("k")
    assert result.state == MISS
    assert result.text == ""


def test_empty_text_is_never_stored():
    cache, _ = _cache()
    assert cache.put("k", scope="s", provider="p", text="") is None
    assert cache.put("k2", scope="s", provider="p", text="   \n ") is None
    assert len(cache) == 0


def test_replacement_is_atomic_and_keeps_last_known_good_until_swapped():
    cache, _ = _cache()
    cache.put("k", scope="s", provider="p", text="v1")
    assert cache.lookup("k").text == "v1"
    cache.put("k", scope="s", provider="p", text="v2")
    assert cache.lookup("k").text == "v2"
    assert cache.lookup("k").state == FRESH


def test_invalidate_marks_stale_and_keeps_lkg_rather_than_deleting():
    cache, _ = _cache()
    cache.put("k", scope="s", provider="p", text="old fact")
    assert cache.invalidate("s") == 1
    result = cache.lookup("k")
    assert result.state == STALE, "LKG must remain servable after a write"
    assert result.text == "old fact"


def test_invalidate_only_touches_its_own_scope():
    cache, _ = _cache()
    cache.put("a", scope="s1", provider="p", text="one")
    cache.put("b", scope="s2", provider="p", text="two")
    assert cache.invalidate("s1") == 1
    assert cache.lookup("a").state == STALE
    assert cache.lookup("b").state == FRESH


def test_changed_fact_supersedes_lkg_after_validated_refresh():
    cache, _ = _cache()
    cache.put("k", scope="s", provider="p", text="colour is red")
    cache.invalidate("s")
    assert cache.lookup("k").text == "colour is red"  # stale LKG served once
    cache.put("k", scope="s", provider="p", text="colour is blue")
    result = cache.lookup("k")
    assert result.state == FRESH
    assert result.text == "colour is blue"


def test_removed_fact_stops_being_served_once_the_grace_window_lapses():
    """A retraction yields no replacement, so the stale window must bound it."""
    cache, clock = _cache()
    cache.put("k", scope="s", provider="p", text="project uses sqlite")
    cache.invalidate("s")
    assert cache.lookup("k").state == STALE
    clock.advance(301.0)
    assert cache.lookup("k").state == MISS


def test_invalidation_is_idempotent():
    cache, _ = _cache()
    cache.put("k", scope="s", provider="p", text="x")
    assert cache.invalidate("s") == 1
    assert cache.invalidate("s") == 0


def test_contradictory_memories_keep_only_the_latest_validated_packet():
    cache, _ = _cache()
    cache.put("k", scope="s", provider="p", text="the deploy target is staging")
    cache.put("k", scope="s", provider="p", text="the deploy target is production")
    assert cache.lookup("k").text == "the deploy target is production"
    assert len(cache) == 1


def test_concurrent_identical_refreshes_are_coalesced():
    cache, _ = _cache()
    started = threading.Event()
    release = threading.Event()
    runs = []

    def work():
        runs.append(1)
        started.set()
        release.wait(5)

    assert cache.start_refresh("k", work) is True
    assert started.wait(5)
    # Every additional caller while the first is in flight must coalesce.
    assert [cache.start_refresh("k", work) for _ in range(8)] == [False] * 8
    release.set()
    for _ in range(100):
        if cache.stats()["inflight_refreshes"] == 0:
            break
        time.sleep(0.01)
    assert len(runs) == 1
    # Once settled a new refresh is allowed again.
    assert cache.start_refresh("k", lambda: None) is True


def test_refresh_work_exception_does_not_wedge_the_key():
    cache, _ = _cache()

    def boom():
        raise RuntimeError("backend exploded")

    assert cache.start_refresh("k", boom) is True
    for _ in range(100):
        if cache.stats()["inflight_refreshes"] == 0:
            break
        time.sleep(0.01)
    assert cache.stats()["inflight_refreshes"] == 0


def test_eviction_is_bounded_and_drops_oldest_first():
    cache = MemoryPacketCache(max_entries=3)
    for i in range(5):
        cache.put(f"k{i}", scope="s", provider="p", text=f"t{i}")
    assert len(cache) == 3
    assert cache.lookup("k0").state == MISS
    assert cache.lookup("k4").state == FRESH


def test_rejects_nonsensical_ttls():
    with pytest.raises(ValueError):
        MemoryPacketCache(fresh_ttl_s=-1)
    with pytest.raises(ValueError):
        MemoryPacketCache(fresh_ttl_s=10, stale_ttl_s=5)
    with pytest.raises(ValueError):
        MemoryPacketCache(max_entries=0)
