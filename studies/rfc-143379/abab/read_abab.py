#!/usr/bin/env python3
"""A/B/A/B on actual Hermes MemoryStore.read and _mutate, pinned to one commit.

A = native read (current PR #141876 publishes a snapshot to the live cache).
B = candidate stateless read (same native disk reader/parser, no cache publish).
Each period starts in a fresh synthetic HERMES_HOME. No model/compressor invoked.
The observed effect is deterministic reader/writer interleaving, NOT LLM recall.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Event, Thread, current_thread

from score import PERIODS, POLICIES, evaluate

BASELINE = "Synthetic source decision: route=v1, origin=study"
ADDITION = "Synthetic correction: route=v2, origin=user-reviewed"
TIMEOUT = 12


def exact_head(checkout: Path, expected: str) -> str:
    if len(expected) != 40 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError("Expected head must be a complete lowercase SHA")
    head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if head != expected:
        raise RuntimeError(f"Wrong runtime checkout: expected {expected}, got {head}")
    for rel in ("tools/memory_tool.py", "tools/memory_tool_store.py"):
        disk = (checkout / rel).read_bytes()
        committed = subprocess.check_output(["git", "-C", str(checkout), "show", f"HEAD:{rel}"])
        if disk != committed:
            raise RuntimeError(f"Dirty production module: {rel}")
    return head


def episode(mt, sandbox: Path, period: str, policy: str, head: str, fixture_sha: str) -> dict:
    profile = sandbox / period
    profile.mkdir()
    os.environ["HERMES_HOME"] = str(profile)
    store = mt.MemoryStore(memory_char_limit=200000, user_char_limit=200000)
    path = store._path_for("memory")
    if not path.resolve().is_relative_to(profile.resolve()):
        raise RuntimeError("Refusing any non-synthetic user profile")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(BASELINE, encoding="utf-8")
    store.load_from_disk()
    frozen = dict(store._system_prompt_snapshot)
    if policy == "stateless":
        from tools.memory_tool_store import _read_failed_error

        def candidate_read(target: str) -> dict:
            target_path = store._path_for(target)
            raw, ok = store._read_raw_checked(target_path)
            if not ok:
                return _read_failed_error(target_path)
            entries = list(dict.fromkeys(store._parse_entries(raw)))
            return {"success": True, "target": target, "entries": entries,
                    "usage": store._usage_pct(target, len(mt.ENTRY_DELIMITER.join(entries)))}

        store.read = candidate_read  # isolated intervention, never applied to source tree

    before = Event()
    release = Event()
    writer_done = Event()
    result_read: list[dict] = []
    result_write: list[dict] = []
    errors: list[str] = []
    original_disk_read = store._read_raw_checked
    readername = "abab-reader"

    def pause_after_disk_read(target_path):
        observation = original_disk_read(target_path)  # native disk I/O
        if current_thread().name == readername and target_path == path:
            before.set()
            if not release.wait(TIMEOUT):
                raise TimeoutError("reader release watchdog")
        return observation

    store._read_raw_checked = pause_after_disk_read

    def reader():
        try:
            result_read.append(store.read("memory"))
        except Exception as exc:
            errors.append(f"reader:{type(exc).__name__}:{exc}")
            before.set()

    def writer():
        try:
            result_write.append(store.add("memory", ADDITION))
        except Exception as exc:
            errors.append(f"writer:{type(exc).__name__}:{exc}")
        finally:
            writer_done.set()

    rt = Thread(name=readername, target=reader, daemon=True)
    wt = Thread(name="abab-writer", target=writer, daemon=True)
    rt.start()
    try:
        if not before.wait(TIMEOUT):
            raise TimeoutError("read never reached real disk boundary")
        wt.start()
        before_release = writer_done.wait(TIMEOUT / 4)
    finally:
        release.set()
        rt.join(TIMEOUT)
        if wt.ident is not None:
            wt.join(TIMEOUT)
        store._read_raw_checked = original_disk_read
    if rt.is_alive() or wt.is_alive():
        raise RuntimeError("live thread after watchdog; no evidence of correctness")

    disk = store._parse_entries(path.read_text(encoding="utf-8"))
    cache = list(store._entries_for("memory"))
    returned = result_read[0] if result_read else {}
    response_entries = returned.get("entries") or []
    return {
        "period": period, "policy": policy, "profile": str(profile),
        "head": head, "fixture_sha256": fixture_sha,
        "errors": errors,
        "reader_observed_pre_write_snapshot": before.is_set()
            and returned.get("entries") == [BASELINE],
        "writer_committed_before_reader_release": before_release,
        "read_success": returned.get("success") is True,
        "write_success": bool(result_write and result_write[0].get("success")),
        "disk_survived": disk == [BASELINE, ADDITION],
        "cache_fresh_after_join": cache == disk,
        "prompt_frozen": store._system_prompt_snapshot == frozen,
        "usage_matches_read_snapshot": returned.get("usage") ==
            store._usage_pct("memory", len(mt.ENTRY_DELIMITER.join(response_entries))),
        "disk_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "response_entries": response_entries, "cache_entries": cache,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkout", type=Path, required=True)
    ap.add_argument("--expected-head", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    checkout = args.checkout.resolve()
    expected = args.expected_head
    report = {
        "head": expected, "real_modules": False, "real_model": False,
        "real_compressor": False, "runs": [], "blocker": None,
        "intervention": "native cache-publishing read vs instrumented stateless read",
        "upstream_changes": False, "reference": "NousResearch/hermes-agent#141876",
    }
    try:
        head = exact_head(checkout, expected)
        with tempfile.TemporaryDirectory(prefix="rfc143379-abab-") as tmp:
            sandbox = Path(tmp).resolve()
            for name in ("HOME", "HERMES_HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME"):
                os.environ[name] = str(sandbox / name.lower())
                Path(os.environ[name]).mkdir(exist_ok=True)
            for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "NOUS_API_KEY"):
                os.environ.pop(name, None)
            def deny_network(event, arguments):
                if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo"):
                    raise RuntimeError(f"Unexpected network access: {event}")
            sys.addaudithook(deny_network)
            sys.path.insert(0, str(checkout))
            os.chdir(checkout)
            mt = importlib.import_module("tools.memory_tool")
            if not Path(mt.__file__).resolve().is_relative_to(checkout):
                raise RuntimeError("Production modules imported from another checkout")
            if not callable(getattr(mt.MemoryStore, "read", None)):
                raise RuntimeError("The pinned head does not implement MemoryStore.read")
            report["real_modules"] = True
            report["read_source_sha256"] = hashlib.sha256(
                inspect.getsource(mt.MemoryStore.read).encode("utf-8")).hexdigest()
            report["fixture_sha256"] = hashlib.sha256(
                (BASELINE + "\n" + ADDITION).encode("utf-8")).hexdigest()
            for period, policy in zip(PERIODS, POLICIES):
                report["runs"].append(
                    episode(mt, sandbox, period, policy, head, report["fixture_sha256"]))
    except Exception as exc:
        report["blocker"] = f"{type(exc).__name__}: {exc}"
    report["evaluation"] = evaluate(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"head": report["head"], "evaluation": report["evaluation"],
                      "blocker": report["blocker"]}))
    return 0 if report["evaluation"]["status"] in ("PASS_MECHANISM", "NO_GAP") else 2


if __name__ == "__main__":
    raise SystemExit(main())
