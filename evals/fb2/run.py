"""Run with PYTHONPATH pointing to an extracted pin, not this checkout."""
import inspect
import json
import os
import sys
from contextlib import nullcontext

from probe import probe
from tools import memory_tool as mt
from tools.memory_tool_store import ENTRY_DELIMITER, MemoryStore


def run(variant, two):
    store = MemoryStore()
    doc_kw = ({"doc": "alpha"} if "doc" in inspect.signature(mt.memory_tool).parameters
              else {"target": "doc:alpha"})

    def call(root, action, content):
        os.environ["HERMES_HOME"] = str(root)
        mt.get_memory_dir = lambda: root
        result = json.loads(mt.memory_tool(action=action, content=content, store=store, **doc_kw))
        if "target" in doc_kw and hasattr(store, "_doc") and not result.get("success"):
            print("chain action rejected at dispatch:", result, "; using the store seam")
            return (store.add("doc:alpha", content) if action == "add"
                    else store.read("doc:alpha"))
        if action == "read" and not result.get("success"):
            # On read-less pins the doc target is rejected before action dispatch.
            capability = json.loads(mt.memory_tool(action="read", target="memory", store=store))
            print("anchor read capability:", capability)
            if "Unknown action 'read'" in capability.get("error", ""):
                print("chain read rejected:", result, "; recovering from chain file")
                return capability
        return result

    if variant in {"no-lock", "both"}:
        store._file_lock = lambda path: nullcontext()
    if variant in {"cache-write", "both"}:
        read = store._read_raw_checked

        def read_and_cache(path):
            raw, ok = read(path)
            if ok:
                store._set_entries("doc:alpha", list(dict.fromkeys(store._parse_entries(raw))))
            return raw, ok

        # Add the cache assignment only during recovery, inside read's lock scope
        # when the lock remains. Leave append, parsing and sanitization unchanged.
        original = store.read

        def cached_read(target):
            store._read_raw_checked = read_and_cache
            try:
                return original(target)
            finally:
                del store._read_raw_checked

        store.read = cached_read

    accepted = probe(call, ENTRY_DELIMITER, two)
    print("valid add sequence:", accepted)


if __name__ == "__main__":
    variant, arm = sys.argv[1:]
    assert variant in {"stock", "no-lock", "cache-write", "both"}
    assert arm in {"one", "two"}
    run(variant, arm == "two")
