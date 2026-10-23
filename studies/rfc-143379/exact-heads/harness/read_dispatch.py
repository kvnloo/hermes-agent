#!/usr/bin/env python3
"""Downstream-only reproducer; no provider, pytest, or live-profile access.

Usage: python read_dispatch.py --checkout FULL_CHECKOUT --output receipt.json
Run separately in each exact-head checkout. RED acceptance findings do not cause
an unsuccessful exit; import/environment blockers do (exit 2). This file has NOT
been executed by its author. Source is never edited. The additional patched
control wraps the checkout's real read/_mutate/dispatch functions; it does not
supply a missing read implementation. See read_dispatch.patch for the equivalent
proposed #141876 source changes (not applied by this script).
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import traceback
from unittest.mock import patch

HEADS = {
    "af16e3ab16eed2492552c325ad1777533a8b7004": "PR #141876",
    "fab9b01c915a3118cc8daa6cc1b18c15b3f982d0": "main control",
    "5b31ccb7d56ad614da63588ef876584b9f95dd3f": "PR #139606",
}
WAIT = 15  # Deadlock watchdog only; never used as evidence of lock exclusion.
NEIGHBOR_TESTS = [
    {"path": "tests/tools/test_memory_tool.py", "neighbors": [
        "TestMemoryToolDispatcher", "TestMemoryBatch", "TestUnreadableFileDoesNotWipeMemory",
        "TestMemoryStoreSnapshot", "TestMemoryFileLockPermissions", "TestBomToleranceInMemoryFiles"],
     "add_cases": [
        "standalone read refreshes cache, reports usage, leaves bytes and prompt snapshot unchanged",
        "batch action enum agrees with actual apply_batch; read is standalone-only",
        "action=read plus operations is explicitly refused, never silently ignores operations",
        "invalid UTF-8 and injected PermissionError preserve existing cache and disk on read",
        "event-controlled read snapshot / writer commit / cache publication interleaving",
        "shared _mutation_lock excludes writer until read publishes; file lock remains real",
        "concurrent writers survive on disk; cache freshness is a distinct assertion"]},
    {"path": "tests/tools/test_memory_tool_schema.py", "neighbors": [
        "test_memory_schema_has_no_forbidden_top_level_combinators"],
     "add_cases": ["read advertised in single action enum, absent from mutating batch enum"]},
    {"path": "tests/tools/test_memory_target_contract.py", "add_cases": [
        "read still observes disabled/invalid target contract at dispatcher boundary"]},
]


class MeasurementBlocked(RuntimeError):
    """Stop further scenarios when an owned concurrency worker cannot be joined."""


def exception_data(exc):
    return {"type": type(exc).__name__, "message": str(exc),
            "traceback": traceback.format_exc()}


def measured(checks, **values):
    return {"acceptance": "GREEN" if all(checks.values()) else "RED", "checks": checks, **values}


def checked_wait(event, name):
    if not event.wait(WAIT):
        raise TimeoutError(f"watchdog waiting for {name}; not a concurrency result")


def fingerprint(fn):
    if fn is None:
        return {"present": False}
    fn = inspect.unwrap(fn)
    text = inspect.getsource(fn)
    return {"present": True, "module": fn.__module__, "qualname": fn.__qualname__,
            "file": inspect.getsourcefile(fn), "line": inspect.getsourcelines(fn)[1],
            "source_sha256": hashlib.sha256(text.encode()).hexdigest(), "source": text}


@contextlib.contextmanager
def patched_shared_lock_and_dispatch(mt):
    """PATCHED CONTROL, not upstream behavior. Native algorithms are delegated.

    A per-store actual threading.RLock named _mutation_lock surrounds the whole
    native read/_mutate call. Read additionally takes the original _file_lock;
    _mutate already takes that original lock internally. No nested file-lock
    acquisition occurs. Also disallow ambiguous read+operations and remove read
    from the batch enum. Missing upstream read is a blocker, never reimplemented.
    """
    cls = mt.MemoryStore
    if not callable(getattr(cls, "read", None)):
        raise RuntimeError("PATCHED CONTROL unavailable: checkout has no MemoryStore.read; no replica supplied")
    init, mutate, read, dispatch = cls.__init__, cls._mutate, cls.read, mt._memory_tool
    signature = inspect.signature(dispatch)

    @functools.wraps(init)
    def locked_init(self, *args, **kwargs):
        init(self, *args, **kwargs)
        if hasattr(self, "_mutation_lock"):
            raise RuntimeError("Control refuses to overwrite an existing upstream _mutation_lock")
        self._mutation_lock = threading.RLock()

    @functools.wraps(mutate)
    def locked_mutate(self, *args, **kwargs):
        with self._mutation_lock:
            return mutate(self, *args, **kwargs)

    @functools.wraps(read)
    def locked_read(self, target):
        with self._mutation_lock, self._file_lock(self._path_for(target)):
            return read(self, target)

    @functools.wraps(dispatch)
    def read_dispatch(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        if bound.arguments.get("action") == "read" and bound.arguments.get("operations") is not None:
            return mt._invalid("'read' is standalone-only; omit 'operations' and make writes in a separate call.")
        return dispatch(*args, **kwargs)

    enum = mt.MEMORY_SCHEMA["parameters"]["properties"]["operations"]["items"]["properties"]["action"]["enum"]
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(cls, "__init__", locked_init))
        stack.enter_context(patch.object(cls, "_mutate", locked_mutate))
        stack.enter_context(patch.object(cls, "read", locked_read))
        stack.enter_context(patch.object(mt, "_memory_tool", read_dispatch))
        original_enum = list(enum)
        enum[:] = [action for action in enum if action != "read"]
        try:
            yield {"mode": "PATCHED_INSTRUMENTED_CONTROL", "native_read_and_mutate_delegated": True,
                   "lock": "per-store threading.RLock _mutation_lock plus actual upstream _file_lock",
                   "read_dispatch": "standalone-only; action=read plus operations rejected",
                   "source_patch": "read_dispatch.patch", "source_patch_applied": False}
        finally:
            enum[:] = original_enum


class Harness:
    def __init__(self, mt, root, head, mode):
        self.mt, self.root, self.head, self.mode = mt, root, head, mode
        self.scenarios = []

    @contextlib.contextmanager
    def fixture(self, name, entries=None):
        home = self.root / self.mode / name
        home.mkdir(parents=True)
        (home / "config.yaml").write_text(
            "memory:\n  memory_enabled: true\n  user_profile_enabled: true\n  write_approval: false\n",
            encoding="utf-8")
        with patch.dict(os.environ, {"HERMES_HOME": str(home)}):
            store = self.mt.MemoryStore(memory_char_limit=50000, user_char_limit=50000)
            path = store._path_for("memory")
            if not path.resolve().is_relative_to(self.root.resolve()):
                raise RuntimeError(f"Refusing non-synthetic memory path: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.mt.ENTRY_DELIMITER.join(entries or ["Synthetic baseline fact."]), encoding="utf-8")
            store.load_from_disk()
            yield store, path

    def call(self, store, **kwargs):
        # Public production entry point, including its native validation/gates/metrics.
        result = json.loads(self.mt.memory_tool(store=store, target=kwargs.pop("target", "memory"), **kwargs))
        if not isinstance(result, dict):
            raise TypeError(f"memory_tool returned {type(result).__name__}, not a JSON object")
        return result

    def record(self, name, fn):
        try:
            result = fn()
        except MeasurementBlocked:
            raise
        except Exception as exc:
            result = {"acceptance": "RED", "finding": "production/runtime error; not replaced with a replica",
                      "error": exception_data(exc)}
        self.scenarios.append({"scenario": name, "head": self.head, "mode": self.mode, **result})

    def require_read(self):
        if not callable(getattr(self.mt.MemoryStore, "read", None)):
            raise RuntimeError("Actual MemoryStore.read is absent on this head; dispatch race cannot run")

    def simple_read(self, target):
        with self.fixture("simple-" + target) as (store, memory_path):
            path = store._path_for(target)
            snapshot = dict(store._system_prompt_snapshot)
            path.write_bytes(b"\xef\xbb\xbf  Synthetic alpha. \n\xc2\xa7\nSynthetic beta.\n\xc2\xa7\nSynthetic alpha.\n")
            before, mtime = path.read_bytes(), path.stat().st_mtime_ns
            result = self.call(store, action="read", target=target)
            expected = ["Synthetic alpha.", "Synthetic beta."]
            return measured({"read_success": result.get("success") is True,
                             "deduped_disk_entries": result.get("entries") == expected,
                             "cache_refreshed": store._entries_for(target) == expected,
                             "usage_correct": result.get("usage") == store._usage_pct(target, len(self.mt.ENTRY_DELIMITER.join(expected))),
                             "target_correct": result.get("target") == target,
                             "disk_bytes_unchanged": path.read_bytes() == before,
                             "disk_mtime_unchanged": path.stat().st_mtime_ns == mtime,
                             "prompt_snapshot_frozen": store._system_prompt_snapshot == snapshot}, result=result)

    def absent_file(self):
        with self.fixture("absent-file") as (store, path):
            path.unlink()
            result = self.call(store, action="read")
            return measured({"missing_file_is_empty_success": result.get("success") is True and result.get("entries") == [],
                             "cache_empty": store._entries_for("memory") == [],
                             "read_does_not_create_memory_file": not path.exists()}, result=result)

    def batch_read(self, mixed):
        with self.fixture("batch-mixed" if mixed else "batch-read") as (store, path):
            props = self.mt.MEMORY_SCHEMA["parameters"]["properties"]
            single_enum = list(props["action"]["enum"])
            batch_enum = list(props["operations"]["items"]["properties"]["action"]["enum"])
            operations = ([{"action": "add", "content": "Synthetic batch candidate."}] if mixed else []) + [{"action": "read"}]
            before, cache = path.read_bytes(), list(store._entries_for("memory"))
            result = self.call(store, operations=operations)
            supported = result.get("success") is True
            return measured({"schema_matches_runtime": ("read" in batch_enum) == supported,
                             "standalone_read_only_contract": "read" not in batch_enum and not supported,
                             "no_partial_commit": path.read_bytes() == before,
                             "cache_preserved_on_rejection": store._entries_for("memory") == cache},
                            single_action_enum=single_enum, batch_action_enum=batch_enum,
                            batch_read_schema_advertised="read" in batch_enum, batch_read_runtime_success=supported,
                            operations=operations, result=result)

    def ambiguous_dispatch(self, operations):
        suffix = "empty" if not operations else "write"
        with self.fixture("read-with-operations-" + suffix) as (store, path):
            before = path.read_bytes()
            result = self.call(store, action="read", operations=operations)
            return measured({"ambiguous_request_rejected": result.get("success") is False,
                             "no_ignored_write_or_disk_change": path.read_bytes() == before},
                            request={"action": "read", "operations": operations}, result=result)

    def failed_read(self, permission_error):
        self.require_read()
        with self.fixture("failed-permission" if permission_error else "failed-utf8") as (store, path):
            cache = store._entries_for("memory")
            expected_cache = list(cache)
            snapshot = dict(store._system_prompt_snapshot)
            if not permission_error:
                path.write_bytes(b"Synthetic unreadable file.\xff\xfe")
            before, mtime = path.read_bytes(), path.stat().st_mtime_ns
            real_read, real_set, real_write = store._read_raw_checked, store._set_entries, store._write_file
            raw_reads, cache_sets, writes = [], [], []

            def observe_read(p):
                answer = real_read(p)
                raw_reads.append({"path": str(p), "read_ok": answer[1]})
                return answer

            def observe_set(target, entries):
                cache_sets.append(list(entries))
                return real_set(target, entries)

            def observe_write(p, entries):
                writes.append(list(entries))
                return real_write(p, entries)

            original_path_read = Path.read_text

            def deny_target(p, *args, **kwargs):
                if p == path:
                    raise PermissionError("Synthetic read failure at actual Path.read_text boundary")
                return original_path_read(p, *args, **kwargs)

            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(store, "_read_raw_checked", observe_read))
                stack.enter_context(patch.object(store, "_set_entries", observe_set))
                stack.enter_context(patch.object(store, "_write_file", observe_write))
                if permission_error:
                    stack.enter_context(patch.object(Path, "read_text", deny_target))
                result = self.call(store, action="read")
            return measured({"read_failed": result.get("success") is False,
                             "actual_checked_read_reports_failure": any(not row["read_ok"] for row in raw_reads),
                             "cache_value_preserved": store._entries_for("memory") == expected_cache,
                             "cache_identity_preserved": store._entries_for("memory") is cache,
                             "no_cache_publish": not cache_sets,
                             "no_native_write": not writes,
                             "disk_bytes_preserved": path.read_bytes() == before,
                             "disk_mtime_preserved": path.stat().st_mtime_ns == mtime,
                             "snapshot_preserved": store._system_prompt_snapshot == snapshot}, result=result,
                            fault_injection="Path.read_text PermissionError (actual _read_raw_checked retained)" if permission_error else "real invalid UTF-8 bytes",
                            raw_reads=raw_reads, cache_sets=cache_sets, writes=writes)

    def write_then_read(self):
        with self.fixture("write-then-read") as (store, path):
            snapshot = dict(store._system_prompt_snapshot)
            added = self.call(store, action="add", content="Synthetic afternoon preference.")
            read = self.call(store, action="read")
            expected = ["Synthetic baseline fact.", "Synthetic afternoon preference."]
            return measured({"write_applied": added.get("success") is True and not added.get("staged"),
                             "read_sees_write": read.get("success") is True and read.get("entries") == expected,
                             "disk_contains_write": store._parse_entries(path.read_text(encoding="utf-8")) == expected,
                             "cache_contains_write": store._entries_for("memory") == expected,
                             "snapshot_remains_frozen": store._system_prompt_snapshot == snapshot}, write_result=added, read_result=read)

    def race(self):
        self.require_read()
        with self.fixture("deterministic-cache-race") as (store, path):
            snapshot = dict(store._system_prompt_snapshot)
            baseline = list(store._entries_for("memory"))
            addition = "Synthetic concurrent writer fact."
            expected = baseline + [addition]
            raw_seen, publish_waiting, publish_release, writer_done, mutation_entered = (threading.Event() for _ in range(5))
            real_read, real_set, real_mutate = store._read_raw_checked, store._set_entries, store._mutate
            rows, results, errors, probe = [], {}, {}, {}
            rows_lock = threading.Lock()
            lock = getattr(store, "_mutation_lock", None)

            def row(kind, **fields):
                with rows_lock:
                    rows.append({"sequence": len(rows), "thread": threading.current_thread().name, "event": kind, **fields})

            def observe_read(p):
                result = real_read(p)  # Actual disk read occurs before the reader is paused.
                row("actual_read_returned", raw=result[0], read_ok=result[1])
                if threading.current_thread().name == "race-reader":
                    raw_seen.set()
                return result

            def observe_set(target, entries):
                if threading.current_thread().name == "race-reader":
                    row("before_reader_actual_set_entries", entries=list(entries))
                    publish_waiting.set()
                    checked_wait(publish_release, "reader cache publication release")
                result = real_set(target, entries)
                row("actual_set_entries_returned", entries=list(entries))
                return result

            def observe_mutate(*args, **kwargs):
                if threading.current_thread().name == "race-writer":
                    row("writer_entered_actual_mutation_wrapper")
                    mutation_entered.set()
                return real_mutate(*args, **kwargs)

            def reader():
                try:
                    results["reader"] = self.call(store, action="read")
                except Exception as exc:
                    errors["reader"] = exception_data(exc)
                    publish_waiting.set()

            def writer():
                try:
                    if lock is not None:
                        acquired = lock.acquire(blocking=False)  # Probe the ACTUAL lock object, not timing.
                        probe["writer_nonblocking_acquire"] = acquired
                        if acquired:
                            lock.release()
                    results["writer"] = self.call(store, action="add", content=addition)
                    row("writer_public_call_returned")
                except Exception as exc:
                    errors["writer"] = exception_data(exc)
                finally:
                    writer_done.set()

            reader_thread = threading.Thread(target=reader, name="race-reader", daemon=True)
            writer_thread = threading.Thread(target=writer, name="race-writer", daemon=True)
            threads = [reader_thread, writer_thread]
            before_release = {}
            try:
                with patch.object(store, "_read_raw_checked", observe_read), patch.object(store, "_set_entries", observe_set), patch.object(store, "_mutate", observe_mutate):
                    reader_thread.start()
                    checked_wait(publish_waiting, "reader before actual _set_entries")
                    if errors:
                        raise RuntimeError(f"Reader failed before deterministic interleaving: {errors}")
                    checked_wait(raw_seen, "reader actual _read_raw_checked")
                    writer_thread.start()
                    if lock is not None:
                        checked_wait(mutation_entered, "writer reaching actual locked mutation")
                    else:
                        checked_wait(writer_done, "unlocked writer commit before reader publishes")
                    before_release = {"writer_done": writer_done.is_set(), "cache": list(store._entries_for("memory")),
                                      "disk": real_read(path)[0]}
                    row("main_releases_reader", writer_done=writer_done.is_set())
                    publish_release.set()
                    for thread in threads:
                        thread.join(WAIT)
            finally:
                publish_release.set()
                for thread in threads:
                    if thread.ident is not None:
                        thread.join(WAIT)
            if any(thread.is_alive() for thread in threads):
                raise MeasurementBlocked("Race watchdog left a live daemon thread; this is a blocked measurement")
            raw, read_ok = real_read(path)
            disk_entries = store._parse_entries(raw)
            cache_entries = list(store._entries_for("memory"))
            fresh = cache_entries == disk_entries
            repair = self.call(store, action="read")
            checks = {"threads_finished_without_errors": not errors,
                      "both_public_calls_succeeded": all(results.get(key, {}).get("success") is True for key in ("reader", "writer")),
                      "actual_reader_snapshot_observed": raw_seen.is_set(),
                      "disk_survival_not_freshness": read_ok and disk_entries == expected,
                      "cache_fresh_after_join": fresh,
                      "snapshot_remains_frozen": store._system_prompt_snapshot == snapshot,
                      "next_read_repairs_cache": repair.get("entries") == expected and store._entries_for("memory") == expected}
            if lock is not None:
                checks["actual_shared_lock_excludes_writer"] = probe.get("writer_nonblocking_acquire") is False
                checks["writer_not_committed_before_reader_release"] = before_release.get("writer_done") is False
            else:
                checks["writer_committed_before_stale_reader_publish"] = before_release.get("writer_done") is True
            return measured(checks, findings=[] if fresh else ["Disk survived, but the same store's cache was overwritten by the stale read after writer commit."],
                            upstream_mutation_lock_present=self.mode == "unmodified" and lock is not None,
                            actual_lock_type=type(lock).__name__ if lock is not None else None,
                            lock_provenance="proposed PATCHED control" if self.mode != "unmodified" else "upstream checkout",
                            lock_probe=probe, before_reader_release=before_release,
                            expected=expected, disk_entries=disk_entries, cache_entries_before_repair=cache_entries,
                            cache_fresh_before_repair=fresh, results=results, errors=errors, trace=rows, repair_result=repair)

    def concurrency_survival(self):
        self.require_read()
        with self.fixture("concurrency-survival") as (store, path):
            barrier = threading.Barrier(3)
            results, errors = [], []
            guard = threading.Lock()
            additions = [f"Synthetic worker {worker} entry {number}." for worker in range(2) for number in range(6)]

            def worker(number):
                try:
                    barrier.wait(WAIT)
                    for index in range(6):
                        result = self.call(store, action="add", content=f"Synthetic worker {number} entry {index}.")
                        with guard:
                            results.append(result)
                except Exception as exc:
                    with guard:
                        errors.append(exception_data(exc))

            def reader():
                try:
                    barrier.wait(WAIT)
                    for _ in range(12):
                        result = self.call(store, action="read")
                        with guard:
                            results.append(result)
                except Exception as exc:
                    with guard:
                        errors.append(exception_data(exc))

            threads = [threading.Thread(target=worker, args=(number,), daemon=True) for number in range(2)]
            threads.append(threading.Thread(target=reader, daemon=True))
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(WAIT)
            if any(thread.is_alive() for thread in threads):
                barrier.abort()
                raise MeasurementBlocked("Concurrency watchdog left live threads; survival/freshness are not established")
            raw, read_ok = store._read_raw_checked(path)
            disk = store._parse_entries(raw)
            cache = list(store._entries_for("memory"))
            expected = ["Synthetic baseline fact."] + additions
            checks = {"all_calls_completed_successfully": len(results) == 24 and not errors and all(result.get("success") is True and not result.get("staged") for result in results),
                      "disk_no_missing_or_extra_entries": read_ok and len(disk) == len(expected) and set(disk) == set(expected),
                      "cache_fresh_after_join_separate_invariant": cache == disk}
            return measured(checks, disk_entries=disk, cache_entries=cache, errors=errors,
                            disk_survived=checks["disk_no_missing_or_extra_entries"], cache_fresh=cache == disk,
                            caveat="Finite survival probe is not a cache-freshness proof; event-controlled race is the deterministic falsifier.")

    def run(self):
        for target in ("memory", "user"):
            self.record("simple_read_" + target, lambda target=target: self.simple_read(target))
        self.record("missing_file_read", self.absent_file)
        self.record("batch_read_schema_vs_runtime", lambda: self.batch_read(False))
        self.record("mixed_batch_read_atomic_rejection", lambda: self.batch_read(True))
        self.record("read_with_write_operations", lambda: self.ambiguous_dispatch([{"action": "add", "content": "Synthetic ignored candidate."}]))
        self.record("read_with_empty_operations", lambda: self.ambiguous_dispatch([]))
        self.record("read_invalid_utf8_preserves_cache_and_disk", lambda: self.failed_read(False))
        self.record("read_oserror_preserves_cache_and_disk", lambda: self.failed_read(True))
        self.record("write_then_read", self.write_then_read)
        self.record("deterministic_same_store_stale_cache_race", self.race)
        self.record("concurrent_survival_and_cache_freshness_separate", self.concurrency_survival)
        return self.scenarios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    checkout, output = args.checkout.resolve(), args.output.resolve()
    report = {"harness": "read_dispatch", "authored_execution_status": "NOT RUN BY AUTHOR",
              "checkout": str(checkout), "head": None, "scenarios": [], "blockers": [],
              "native_neighboring_tests_suggested_not_run": NEIGHBOR_TESTS,
              "expected_heads": HEADS, "external_providers": "forbidden"}
    sys.dont_write_bytecode = True
    with tempfile.TemporaryDirectory(prefix="hermes-read-dispatch-") as tmp:
        root = Path(tmp).resolve()
        # Do not inherit a live Hermes profile, config override, auth, or telemetry settings.
        for key in list(os.environ):
            if key.startswith("HERMES_") or key in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"}:
                os.environ.pop(key)
        os.environ.update({"HERMES_HOME": str(root / "bootstrap"), "HOME": str(root / "home"),
                           "USERPROFILE": str(root / "home"), "XDG_CONFIG_HOME": str(root / "config"),
                           "XDG_CACHE_HOME": str(root / "cache"), "TMPDIR": str(root / "tmp")})
        for name in ("bootstrap", "home", "config", "cache", "tmp"):
            (root / name).mkdir()
        report["isolation"] = {"HERMES_HOME_set_before_production_imports": True,
                               "HOME_and_XDG_synthetic": True, "native_algorithms_replaced": False,
                               "network_blocked": True, "temporary_root_removed_on_exit": True}
        try:
            head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
            report.update(head=head, head_label=HEADS.get(head, "UNRECOGNIZED HEAD"))
            if head not in HEADS:
                raise RuntimeError(f"Unrecognized head {head}; refusing to label it an actual requested PR/control")
            source_files = {}
            for relative in ("tools/memory_tool.py", "tools/memory_tool_store.py"):
                actual = (checkout / relative).read_bytes()
                committed = subprocess.check_output(["git", "-C", str(checkout), "show", f"HEAD:{relative}"])
                source_files[relative] = {"sha256": hashlib.sha256(actual).hexdigest(), "matches_HEAD": actual == committed}
                if actual != committed:
                    raise RuntimeError(f"{relative} differs from exact HEAD; pristine upstream measurement required")
            report["source_files"] = source_files
            # All production imports occur only after environment isolation. No SDK/provider is used.
            def deny_network(event, arguments):
                if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.bind"}:
                    raise RuntimeError(f"Network forbidden in synthetic harness: {event}")
            sys.addaudithook(deny_network)
            sys.path.insert(0, str(checkout))
            os.chdir(checkout)
            mt = importlib.import_module("tools.memory_tool")
            ms = importlib.import_module("tools.memory_tool_store")
            for module in (mt, ms):
                if not Path(module.__file__).resolve().is_relative_to(checkout):
                    raise RuntimeError(f"Foreign installed module imported instead of checkout: {module.__file__}")
            probe = mt.MemoryStore()
            report["production_functions"] = {name: fingerprint(fn) for name, fn in {
                "memory_tool": mt.memory_tool, "_memory_tool": mt._memory_tool,
                "MemoryStore.read": getattr(ms.MemoryStore, "read", None),
                "MemoryStore._mutate": ms.MemoryStore._mutate,
                "MemoryStore._read_raw_checked": ms.MemoryStore._read_raw_checked,
                "MemoryStore._set_entries": ms.MemoryStore._set_entries,
                "MemoryStore._file_lock": ms.MemoryStore._file_lock,
            }.items()}
            report["upstream_lock_inspection"] = {
                "_mutation_lock_present": hasattr(probe, "_mutation_lock"),
                "_mutation_lock_type": type(getattr(probe, "_mutation_lock", None)).__name__,
                "_file_lock_present": callable(getattr(probe, "_file_lock", None)),
                "finding": "Do not attribute proposed _mutation_lock to upstream; inspected pinned source uses _file_lock in _mutate."}
            report["scenarios"].extend(Harness(mt, root, head, "unmodified").run())
            try:
                with patched_shared_lock_and_dispatch(mt) as control:
                    report["patched_control"] = control
                    report["scenarios"].extend(Harness(mt, root, head, "patched_control").run())
            except Exception as exc:
                report["patched_control"] = {"mode": "PATCHED_INSTRUMENTED_CONTROL", "acceptance": "BLOCKED",
                                             "error": exception_data(exc), "missing_read_not_reimplemented": True}
        except Exception as exc:
            report["blockers"].append(exception_data(exc))
    report["summary"] = {status: sum(row.get("acceptance") == status for row in report["scenarios"]) for status in ("GREEN", "RED", "BLOCKED")}
    report["summary"]["expected_red_findings_do_not_abort"] = True
    report["summary"]["runtime_errors_remain_findings"] = True
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "head": report["head"], "summary": report["summary"], "blockers": report["blockers"]}, ensure_ascii=False))
    return 2 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
