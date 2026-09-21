"""Tests for the scoped memory packet cache.

Each test names the behaviour it pins. The provider-level failure cases
(timeout, malformed response, contradictory memories) are exercised through
``MemoryManager`` so the guarantee is tested where it is actually relied on,
not only on the cache in isolation.
"""

import threading
import time

import pytest

from agent.memory_manager import MemoryManager
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
from agent.memory_provider import MemoryProvider


class FakeProvider(MemoryProvider):
    """Provider whose recall behaviour each test dictates."""

    def __init__(self, name="fakeext", *, reply="", delay=0.0, raises=None, available=True):
        self._name = name
        self._reply = reply
        self._delay = delay
        self._raises = raises
        self._available = available
        self.calls = 0
        self.cache_scope_value = None

    @property
    def name(self):
        return self._name

    def is_available(self):
        return self._available

    def initialize(self, session_id, **kwargs):
        pass

    def system_prompt_block(self):
        return ""

    def prefetch(self, query, *, session_id=""):
        self.calls += 1
        if self._delay:
            time.sleep(self._delay)
        if self._raises is not None:
            raise self._raises
        return self._reply

    def queue_prefetch(self, query, *, session_id=""):
        pass

    def sync_turn(self, user_content, assistant_content, *, session_id=""):
        pass

    def get_tool_schemas(self):
        return []

    def handle_tool_call(self, tool_name, args, **kwargs):
        return ""

    def cache_scope(self):
        return self.cache_scope_value


def _manager(provider, **kwargs):
    mgr = MemoryManager(**kwargs)
    mgr.add_provider(provider)
    return mgr


# ---------------------------------------------------------------------------
# Keying and scope isolation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Freshness states
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Invalidation: changed / removed / contradictory facts
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Refresh coalescing
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Provider-level failures, through MemoryManager
# ---------------------------------------------------------------------------


def test_manager_serves_a_fresh_packet_without_calling_the_provider_again():
    provider = FakeProvider(reply="<relevant-memories>likes tea</relevant-memories>")
    mgr = _manager(provider)
    first = mgr.prefetch_all("what do I drink", session_id="s1")
    assert "likes tea" in first
    assert provider.calls == 1

    second = mgr.prefetch_all("what do I drink", session_id="s1")
    assert "likes tea" in second
    assert provider.calls == 1, "a fresh packet must not trigger a second remote call"


def test_manager_does_not_reuse_a_packet_across_sessions_by_default():
    provider = FakeProvider(reply="scoped memory")
    mgr = _manager(provider)
    mgr.prefetch_all("what do I drink", session_id="s1")
    mgr.prefetch_all("what do I drink", session_id="s2")
    assert provider.calls == 2, "session boundary must not leak a packet"


def test_timeout_degrades_to_empty_without_caching_a_false_negative():
    provider = FakeProvider(reply="slow memory", delay=5.0)
    mgr = _manager(provider, external_prefetch_timeout=0.2)
    started = time.monotonic()
    text = mgr.prefetch_all("needs memory", session_id="s1")
    elapsed = time.monotonic() - started
    assert text == "", "a timed-out recall must not inject anything"
    assert elapsed < 2.0, f"turn blocked for {elapsed:.2f}s despite a 0.2s bound"
    assert mgr.memory_packet_cache.stats()["entries"] == 0, (
        "a timeout is indistinguishable from 'no memories'; caching it would "
        "turn an outage into a permanent false negative"
    )


def test_malformed_response_is_not_cached_and_does_not_break_the_turn():
    provider = FakeProvider(raises=ValueError("malformed envelope from gateway"))
    mgr = _manager(provider)
    assert mgr.prefetch_all("needs memory", session_id="s1") == ""
    assert mgr.memory_packet_cache.stats()["entries"] == 0


def test_empty_query_never_reaches_the_provider():
    provider = FakeProvider(reply="unused")
    mgr = _manager(provider)
    assert mgr.prefetch_all("", session_id="s1") == ""
    assert provider.calls == 0
    assert mgr.memory_packet_cache.stats()["entries"] == 0


def test_trivial_prompt_gate_lives_upstream_of_the_manager():
    """Pin the layering: the cheap-query gate is the caller's, not the manager's.

    ``turn_context`` applies ``is_trivial_prompt`` before calling ``prefetch_all``,
    so the packet cache sits *below* that gate and must not re-implement it. If
    this ever inverts, recall has silently become unconditional for one-word turns.
    """
    from agent.memory_provider import is_trivial_prompt

    assert is_trivial_prompt("hi") is True
    assert is_trivial_prompt("/help") is True
    assert is_trivial_prompt("what did we decide about the deploy target") is False

    # The manager deliberately does not gate, which is why the cache lives inside it.
    provider = FakeProvider(reply="memory")
    mgr = _manager(provider)
    assert mgr.prefetch_all("hi", session_id="s1") == "memory"
    assert provider.calls == 1


def test_stale_packet_is_injected_now_and_refresh_replaces_it_behind_the_turn():
    provider = FakeProvider(reply="v1 memory")
    mgr = _manager(provider)
    assert "v1 memory" in mgr.prefetch_all("q", session_id="s1")
    assert provider.calls == 1

    mgr.invalidate_memory_packets("s1")
    provider._reply = "v2 memory"

    served = mgr.prefetch_all("q", session_id="s1")
    assert "v1 memory" in served, "the stale packet must still answer this turn"

    for _ in range(200):
        if provider.calls >= 2:
            break
        time.sleep(0.01)
    assert provider.calls == 2, "a stale hit must schedule a replacement"
    for _ in range(200):
        if "v2 memory" in mgr.prefetch_all("q", session_id="s1"):
            break
        time.sleep(0.01)
    assert "v2 memory" in mgr.prefetch_all("q", session_id="s1")


def test_a_successful_sync_invalidates_the_scope_it_wrote_to():
    provider = FakeProvider(reply="before write")
    mgr = _manager(provider)
    mgr.prefetch_all("q", session_id="s1")
    assert mgr.memory_packet_cache.stats()["entries"] == 1
    mgr.sync_all("user said", "assistant said", session_id="s1")
    assert mgr.memory_packet_cache.lookup(
        cache_key(make_scope(provider="fakeext", session_id="s1"), "q")
    ).state == STALE


def test_provider_declared_scope_widens_reuse_safely_across_sessions():
    provider = FakeProvider(reply="tenant memory")
    provider.cache_scope_value = "tenant:t1"
    mgr = _manager(provider)
    mgr.prefetch_all("q", session_id="s1")
    mgr.prefetch_all("q", session_id="s2")
    assert provider.calls == 1, "an explicit tenant scope may be shared"
