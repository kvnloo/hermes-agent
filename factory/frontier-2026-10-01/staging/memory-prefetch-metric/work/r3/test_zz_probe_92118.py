"""Temporary probe (never committed): a #92118-style structured prefetch result after a naive merge."""

from tests.hermes_cli.test_relay_shared_metrics_runtime import direct_runtime  # noqa: F401
from tests.hermes_cli.test_shared_metrics_loop import _PrefetchProvider, _rows, home  # noqa: F401


def test_structured_prefetch_result_after_naive_merge(home):  # noqa: F811
    from agent.memory_manager import MemoryManager
    from agent.memory_provider import MemoryPrefetchResult

    manager = MemoryManager(external_prefetch_timeout=5.0)
    manager._providers = [_PrefetchProvider("honcho", lambda: MemoryPrefetchResult(context="- prefers tabs"))]
    context = manager.prefetch_all("what do I prefer?")
    rows = [(d["provider"], d["outcome"]) for d, _ in _rows(home, "hermes.memory.prefetch.count")]
    open("<scratch>/probe_out.txt", "a").write(f"PROBE context={context!r} rows={rows}\n")
    assert context == "- prefers tabs"
