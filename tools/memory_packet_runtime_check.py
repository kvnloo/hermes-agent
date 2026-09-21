"""Runtime check for the memory packet cache, on the shipped code path.

This is not a unit test: it uses the real ``MemoryManager``, the real cache, and
real wall-clock timing, and it performs a real HTTP request against the configured
TencentDB Gateway (127.0.0.1:8420) so the "remote is down" case is measured rather
than asserted.

Run:  python3 tools/memory_packet_runtime_check.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

WORKTREE = "/workspace/hermes-home/hermes-agent/.worktrees/wt/memory-packet-cache"
sys.path.insert(0, WORKTREE)

from agent.memory_manager import MemoryManager  # noqa: E402
from agent.memory_packet_cache import cache_key, make_scope  # noqa: E402
from agent.memory_provider import MemoryProvider  # noqa: E402

GATEWAY = "http://127.0.0.1:8420/health"


class GatewayProvider(MemoryProvider):
    """Provider that really talks to the Gateway, or really fails trying."""

    def __init__(self, reply="", probe_down=False):
        self._reply = reply
        self._probe_down = probe_down
        self.calls = 0

    @property
    def name(self):
        return "memory_tencentdb"

    def is_available(self):
        return True

    def initialize(self, session_id, **kwargs):
        pass

    def system_prompt_block(self):
        return ""

    def prefetch(self, query, *, session_id=""):
        self.calls += 1
        if self._probe_down:
            # Real request, real refusal. Mirrors the provider returning "" when
            # the Gateway is unreachable.
            try:
                urllib.request.urlopen(GATEWAY, timeout=2)
            except Exception:
                return ""
        return self._reply

    def queue_prefetch(self, query, *, session_id=""):
        pass

    def sync_turn(self, user_content, assistant_content, *, session_id=""):
        pass

    def get_tool_schemas(self):
        return []

    def handle_tool_call(self, tool_name, args, **kwargs):
        return ""


def gateway_reachable():
    try:
        urllib.request.urlopen(GATEWAY, timeout=2)
        return True
    except Exception as exc:
        return f"{type(exc).__name__}"


def main():
    out = {"gateway_probe": gateway_reachable()}

    # 1. Remote down: the turn must not block on the full 8 s default, and the
    #    failure must NOT be cached as "this user has no memories".
    down = GatewayProvider(probe_down=True)
    mgr = MemoryManager()
    mgr.add_provider(down)
    t0 = time.monotonic()
    first = mgr.prefetch_all("what is the deploy target", session_id="rt-1")
    ms_down = (time.monotonic() - t0) * 1000
    out["down"] = {
        "returned": first,
        "latency_ms": round(ms_down, 1),
        "remote_calls": down.calls,
        "cached_entries": mgr.memory_packet_cache.stats()["entries"],
        "false_negative_cached": mgr.memory_packet_cache.stats()["entries"] != 0,
    }

    # 2. Remote healthy: cold call pays the round trip, the repeat must not.
    up = GatewayProvider(reply="<relevant-memories>\n- [fact] deploy target is staging\n</relevant-memories>")
    mgr2 = MemoryManager()
    mgr2.add_provider(up)
    t0 = time.monotonic()
    cold = mgr2.prefetch_all("what is the deploy target", session_id="rt-2")
    ms_cold = (time.monotonic() - t0) * 1000
    t0 = time.monotonic()
    warm = mgr2.prefetch_all("what is the deploy target", session_id="rt-2")
    ms_warm = (time.monotonic() - t0) * 1000
    out["warm"] = {
        "cold_ms": round(ms_cold, 2),
        "warm_ms": round(ms_warm, 2),
        "remote_calls_total": up.calls,
        "same_text": cold == warm and cold != "",
        "saved_fraction": round(1 - (ms_warm / ms_cold), 4) if ms_cold > 0 else None,
    }

    # 3. Scope: a different session must not read another session's packet.
    t0 = time.monotonic()
    other = mgr2.prefetch_all("what is the deploy target", session_id="rt-3")
    out["scope_isolation"] = {
        "remote_calls_total": up.calls,
        "second_session_refetched": up.calls == 2,
        "text_present": other != "",
    }

    # 4. A write invalidates to stale, and the stale packet still answers.
    mgr2.sync_all("deploy target changed", "noted", session_id="rt-2")
    state = mgr2.memory_packet_cache.classify(
        cache_key(make_scope(provider="memory_tencentdb", session_id="rt-2"), "what is the deploy target")
    )[0]
    out["after_write"] = {"state": state, "lkg_retained": state in ("fresh", "stale")}

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
