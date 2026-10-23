#!/usr/bin/env python3
"""Offline exact-head reproduction for Finn763 Hermes PR #116673.

Run only by the integrating parent:
  python chain_bounds.py --checkout /full/exact/head --output /results/chain.json

No source edits, model/provider calls, live profiles, fake modules or substituted
MemoryStore. RED findings are data, not process failures. Import/runtime failures
are BLOCKED with their actual exception. Candidate helper is separate downstream
code, never presented as upstream's implementation.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback

EXPECTED_HEAD = "2c1941aac46efac3b35605d99a8628e75a91c670"
SIZES = (4096, 128 * 1024, 1024 * 1024)
UPSTREAM = f"https://github.com/NousResearch/hermes-agent/blob/{EXPECTED_HEAD}/"


def verdict(passed: bool) -> str:
    return "GREEN" if passed else "RED"


def failure(exc: Exception, phase: str) -> dict:
    return {"status": "BLOCKED", "phase": phase,
            "exception": type(exc).__name__, "error": str(exc),
            "missing_module": getattr(exc, "name", None),
            "traceback": traceback.format_exc()}


def synthetic_text(size: int) -> str:
    # Mixed UTF-8 widths and JSON escaping; not a delimiter or a threat fixture.
    pattern = 'α中🙂é\\"\t\nZ'
    units, remaining = divmod(size - 2, len(pattern.encode("utf-8")))
    return "S" + pattern * units + "x" * remaining + "E"


def run(checkout: Path, home: Path) -> dict:
    # Set before ANY upstream import. Never inherit a live Hermes profile.
    os.environ["HERMES_HOME"] = str(home)
    for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        os.environ[key] = str(home / key.lower())
    (home / "config.yaml").write_text(
        "memory:\n  write_approval: false\n  memory_enabled: true\n"
        "  user_profile_enabled: true\n", encoding="utf-8")
    report = {"pr": 116673, "expected_head": EXPECTED_HEAD,
              "execution": "actual checkout modules, synthetic temporary HERMES_HOME",
              "candidate": {"kind": "downstream helper, NOT upstream patch applied",
                            "file": "chain_page_candidate.py",
                            "sha256": hashlib.sha256(Path(__file__).with_name(
                                "chain_page_candidate.py").read_bytes()).hexdigest(),
                            "contract": {"payload_utf8_bytes_max": 4096,
                                         "serialized_json_utf8_bytes_max": 4096,
                                         "serializer": "ensure_ascii=False, compact separators",
                                         "envelope_definition": "wire bytes minus serialized JSON content value bytes",
                                         "offset_unit": "on-disk UTF-8 bytes",
                                         "cursor_identity": "checkout SHA + absolute actual doc path + SHA-256 + byte length",
                                         "io_cost": "full streaming hash per page; bounded response, not bounded total I/O"}},
              "sources": [{"url": UPSTREAM + "tools/memory_tool.py",
                           "symbols": ["memory_tool", "_memory_tool", "_resolve_target"]},
                          {"url": UPSTREAM + "tools/memory_tool_store.py",
                           "symbols": ["MemoryStore.read", "MemoryStore._path_for", "MemoryStore._mutate",
                                       "MemoryStore._anchor_gate", "MemoryStore._file_lock", "MemoryStore._chain_line"]}],
              "measurements": [], "blockers": []}
    try:
        head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                                       text=True).strip()
        report["head"] = head
        if head != EXPECTED_HEAD:
            raise RuntimeError(f"Exact head required: expected {EXPECTED_HEAD}, got {head}")
        # Pin the actual implementation bytes as well as commit metadata. No
        # detached PR fragments or dirty memory implementations count as exact.
        hashes = {}
        for relative in ("tools/memory_tool.py", "tools/memory_tool_store.py"):
            actual = (checkout / relative).read_bytes()
            committed = subprocess.check_output(["git", "-C", str(checkout), "show", f"HEAD:{relative}"])
            if actual != committed:
                raise RuntimeError(f"Checkout implementation differs from exact head: {relative}")
            hashes[relative] = hashlib.sha256(actual).hexdigest()
        report["source_sha256"] = hashes
        sys.path.insert(0, str(checkout))
        mt = importlib.import_module("tools.memory_tool")
        ms = importlib.import_module("tools.memory_tool_store")
        from chain_page_candidate import PAGE_BYTES, read_chain_page, serialize
        from hermes_constants import get_hermes_home
        if Path(get_hermes_home()).resolve() != home.resolve():
            raise RuntimeError("Upstream HERMES_HOME resolution escaped the isolated fixture")
        for mod in (mt, ms):
            if not Path(mod.__file__).resolve().is_relative_to(checkout):
                raise RuntimeError(f"Imported wrong checkout module: {mod.__file__}")
        store = mt.MemoryStore()
        store.load_from_disk()
        memory_dir = Path(mt.get_memory_dir()).resolve()
        if not memory_dir.is_relative_to(home):
            raise RuntimeError(f"Memory directory escaped isolated home: {memory_dir}")
        report["isolation"] = {"temporary_home": str(home), "actual_memory_directory": str(memory_dir),
                               "config_write_approval": False, "providers_called": False}
    except Exception as exc:
        report["blockers"].append(failure(exc, "exact head / actual module import / isolation"))
        report["status"] = "BLOCKED"
        return report

    def call(which=store, **kwargs):
        wire = mt.memory_tool(store=which, target="memory", **kwargs)
        return wire, json.loads(wire)

    def require_write(**kwargs):
        wire, data = call(**kwargs)
        if not data.get("success") or data.get("staged"):
            raise RuntimeError(f"Actual memory write did not commit: {wire}")
        return data

    try:
        anchor = "Synthetic chain index: " + " ".join(f"@doc:fixture-{size}" for size in SIZES)
        require_write(action="add", content=anchor)
        store.load_from_disk()
        baseline_prompt = store.format_for_system_prompt("memory") or ""
        report["anchor"] = {"content_utf8_bytes": len(anchor.encode("utf-8")),
                            "baseline_prompt_utf8_bytes": len(baseline_prompt.encode("utf-8"))}
    except Exception as exc:
        report["blockers"].append(failure(exc, "anchor write via actual memory_tool"))
        report["status"] = "BLOCKED"
        return report

    for size in SIZES:
        measurement = {"requested_doc_utf8_bytes": size, "doc": f"fixture-{size}"}
        report["measurements"].append(measurement)
        try:
            text = synthetic_text(size)
            write = require_write(action="add", doc=measurement["doc"], content=text)
            path = Path(store._path_for(ms.doc_target(measurement["doc"])))
            disk = path.read_bytes()
            wire, data = call(action="read", doc=measurement["doc"])
            store.load_from_disk()  # Frozen prompt must be measured after a fresh load.
            prompt = store.format_for_system_prompt("memory") or ""
            anchor_wire, anchor_read = call(action="read")
            measurement["upstream"] = {
                "write_success": write.get("success"), "read_success": data.get("success"),
                "error": data.get("error"), "actual_doc_path": str(path),
                "actual_doc_utf8_bytes": len(disk), "actual_doc_sha256": hashlib.sha256(disk).hexdigest(),
                "read_serialized_utf8_bytes": len(wire.encode("utf-8")),
                "read_content_utf8_bytes": sum(len(e.encode("utf-8")) for e in data.get("entries", [])),
                "read_exact_entry": data.get("entries") == [text],
                "anchor_read_serialized_utf8_bytes": len(anchor_wire.encode("utf-8")),
                "anchor_read_error": anchor_read.get("error"),
                "anchor_prompt_utf8_bytes": len(prompt.encode("utf-8")),
                "anchor_prompt_growth_bytes": len(prompt.encode("utf-8")) - len(baseline_prompt.encode("utf-8")),
                "doc_contents_excluded_from_prompt": text[:100] not in prompt,
                "bounded_read_contract": verdict(len(wire.encode("utf-8")) <= PAGE_BYTES),
                "expected_finding": "RED: full doc entries are returned without pagination"}
            if disk != text.encode("utf-8"):
                raise RuntimeError("Actual API-written file does not equal requested synthetic UTF-8 bytes")
            cursor, chunks, sizes, payloads, envelopes = None, [], [], [], []
            offsets_valid, cursor_identity_valid = True, True
            offset = 0
            page_errors = []
            # Bounded by bytes/pages to surface any broken no-progress loop.
            for page_number in range(size + 1):
                page = read_chain_page(store, measurement["doc"], head, cursor)
                if not page.get("success"):
                    page_errors.append(page)
                    break
                page_wire = serialize(page).encode("utf-8")
                payload = page["content"].encode("utf-8")  # Strictly decodes every character independently.
                content_value_wire = json.dumps(page["content"], ensure_ascii=False,
                                                separators=(",", ":")).encode("utf-8")
                sizes.append(len(page_wire))
                payloads.append(len(payload))
                envelopes.append(len(page_wire) - len(content_value_wire))
                offsets_valid &= (page["byte_offset"] == offset
                                  and page["next_byte_offset"] == offset + len(payload))
                cursor_identity_valid &= (page["source"]["checkout_sha"] == head
                                          and page["source"]["path"] == str(path.resolve())
                                          and page["source"]["sha256"] == hashlib.sha256(disk).hexdigest())
                offset += len(payload)
                chunks.append(payload)
                if page["eof"]:
                    offsets_valid &= page["next_cursor"] is None
                    break
                # Persist/restore JSON cursor for EVERY page: no in-memory iterator state.
                cursor = json.loads(json.dumps(page["next_cursor"]))
                if not payload:
                    page_errors.append({"error": "non_eof_page_made_no_progress"})
                    break
            else:
                page_errors.append({"error": "page_iteration_bound_exceeded"})
            exact = b"".join(chunks) == disk
            bounded = bool(sizes) and max(sizes) <= PAGE_BYTES and max(payloads) <= PAGE_BYTES
            green = exact and bounded and offsets_valid and cursor_identity_valid and not page_errors
            measurement["candidate"] = {
                "status": verdict(green), "page_count": len(sizes),
                "max_serialized_utf8_bytes": max(sizes, default=0),
                "max_payload_utf8_bytes": max(payloads, default=0),
                "max_envelope_utf8_bytes": max(envelopes, default=0),
                "total_serialized_utf8_bytes": sum(sizes),
                "reconstructed_utf8_bytes": sum(payloads), "exact_byte_reconstruction": exact,
                "utf8_no_split_character": exact and all(c.decode("utf-8").encode("utf-8") == c for c in chunks),
                "contiguous_byte_offsets": bool(offsets_valid),
                "source_path_sha_hash_pinned": bool(cursor_identity_valid),
                "json_cursor_roundtrip_between_pages": True, "errors": page_errors}
        except Exception as exc:
            measurement["runtime"] = failure(exc, f"actual API / pagination for {size} bytes")
            report["blockers"].append(measurement["runtime"])

    try:
        doc = f"fixture-{SIZES[0]}"
        first = read_chain_page(store, doc, head)
        cursor = first.get("next_cursor")
        if not first.get("success") or cursor is None:
            raise RuntimeError(f"Mutation fixture needs a resumable first page: {first.get('error')}")
        require_write(action="add", doc=doc, content="Synthetic source mutation marker")
        resumed = read_chain_page(store, doc, head, json.loads(json.dumps(cursor)))
        restarted = read_chain_page(store, doc, head)
        malformed = read_chain_page(store, doc, head, {"version": 999})
        bad_sha_cursor = json.loads(json.dumps(restarted.get("next_cursor")))
        if not isinstance(bad_sha_cursor, dict):
            raise RuntimeError("Mutated fixture did not supply a cursor")
        bad_sha_cursor["source"]["checkout_sha"] = "0" * 40
        wrong_sha = read_chain_page(store, doc, head, bad_sha_cursor)
        bad_offset = json.loads(json.dumps(restarted["next_cursor"]))
        bad_offset["byte_offset"] = 2  # S is byte 0; byte 2 is inside the first alpha character.
        interior = read_chain_page(store, doc, head, bad_offset)
        passed = (resumed.get("error") == "source_changed" and restarted.get("success")
                  and malformed.get("error") == "invalid_cursor"
                  and wrong_sha.get("error") == "source_changed"
                  and interior.get("error") == "invalid_utf8_or_offset")
        report["cursor_controls"] = {"status": verdict(bool(passed)),
                                     "mutation_via_actual_api": True,
                                     "resume_after_mutation": resumed,
                                     "restart_success": restarted.get("success"),
                                     "invalid_version": malformed,
                                     "different_checkout_sha": wrong_sha,
                                     "inside_utf8_character": interior}
    except Exception as exc:
        report["cursor_controls"] = failure(exc, "cursor mutation / validation controls")
        report["blockers"].append(report["cursor_controls"])

    try:
        # Deterministic schedule, not a replica: the first writer has passed its
        # actual _anchor_gate; the second actual writer removes the anchor just
        # before the first acquires the doc lock. Restore the seam in finally.
        require_write(action="add", content="Synthetic race reference @doc:race")
        other = mt.MemoryStore()
        other.load_from_disk()
        race_path = Path(store._path_for(ms.doc_target("race")))
        original_lock = store._file_lock
        schedule = {}

        @contextmanager
        def interleave(path):
            if Path(path) == race_path and not schedule:
                _, removed = call(which=other, action="remove", old_text="@doc:race")
                schedule["anchor_removal"] = removed
                if not removed.get("success") or removed.get("staged"):
                    raise RuntimeError("Actual interleaved anchor removal failed")
            with original_lock(path):
                yield

        store._file_lock = interleave
        try:
            _, added = call(action="add", doc="race", content="Synthetic write after anchor removal")
        finally:
            del store._file_lock
        _, anchor_after = call(action="read")
        _, readable = call(action="read", doc="race")
        _, later_write = call(action="add", doc="race", content="Synthetic subsequent write")
        removed_ok = schedule.get("anchor_removal", {}).get("success") is True
        leaked_write = removed_ok and added.get("success") is True and not added.get("staged")
        report["anchor_removal_race"] = {
            "status": verdict(not leaked_write), "expected_finding": "RED: gate checks anchor before acquiring only the doc lock",
            "schedule": "actual gate -> second actual API removes anchor -> first actual doc lock/write",
            "scheduler_only_instrumentation": "instance _file_lock wrapper; actual gate/store/file locks/writes retained",
            "anchor_removal_success": removed_ok, "write_after_removal": added,
            "read_still_succeeds": readable.get("success"),
            "orphan_reported": any(d["name"] == "race" for d in anchor_after.get("orphan_docs", [])),
            "subsequent_write_refused": later_write.get("success") is False,
            "subsequent_write_error": later_write.get("error"),
            "not_a_pagination_fix": "Candidate only bounds reads; it does not fix cross-file anchor/write atomicity."}
    except Exception as exc:
        report["anchor_removal_race"] = failure(exc, "anchor removal deterministic interleaving")
        report["blockers"].append(report["anchor_removal_race"])

    upstream_red = all(
        m.get("upstream", {}).get("bounded_read_contract") == "RED"
        and m["upstream"].get("read_success") is True
        and m["upstream"].get("read_exact_entry") is True
        and m["upstream"].get("actual_doc_utf8_bytes") == m["requested_doc_utf8_bytes"]
        and m["upstream"].get("doc_contents_excluded_from_prompt") is True
        and m["upstream"].get("anchor_read_error") is None
        for m in report["measurements"])
    candidate_green = all(m.get("candidate", {}).get("status") == "GREEN"
                          for m in report["measurements"])
    candidate_green &= report.get("cursor_controls", {}).get("status") == "GREEN"
    report["acceptance"] = {"upstream_unbounded_red_reproduced": upstream_red,
                            "candidate_bounded_reconstruction_green": bool(candidate_green),
                            "all_requested_sizes_measured": len(report["measurements"]) == len(SIZES)}
    report["status"] = ("BLOCKED" if report["blockers"] else
                        "GREEN" if upstream_red and candidate_green else "RED")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="hermes-chain-bounds-") as isolated:
        try:
            report = run(args.checkout.resolve(), Path(isolated))
        except Exception as exc:
            report = {"status": "BLOCKED", "expected_head": EXPECTED_HEAD,
                      "blockers": [failure(exc, "harness runtime")]}
        report["temporary_fixture_removed_on_exit"] = True
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Expected RED findings never abort the run. Parent evaluates JSON acceptance;
    # nonzero only denotes missing prerequisites or runtime/import blockers.
    print(json.dumps({"output": str(args.output), "status": report["status"]}))
    return 2 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
