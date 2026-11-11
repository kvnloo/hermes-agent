#!/usr/bin/env python3
"""Production boundary exercise, NOT reproduction of the unpublished RFC probe.

Only summary generation is replaced with a deterministic 4:1 extractive
identifier selector. Fixed K=10 is a study-side candidate, not upstream code.
Source recovery reads an external hash-verified archive, separately metered.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import traceback
import types

ID = re.compile(r"RFCID_[0-9a-f]{24}")


def ids(text):
    return list(dict.fromkeys(ID.findall(text)))


def run(checkout, base):
    sys.path.insert(0, str(checkout))
    from agent.context_compressor import ContextCompressor
    rows = []
    for cycles in (150, 300, 600):
        for policy in ("baseline", "fixed_k10", "source_anchored"):
            archive = base / f"{cycles}-{policy}"
            archive.mkdir()
            compressor = ContextCompressor(
                model="synthetic-no-provider", config_context_length=4096,
                summary_target_ratio=0.25, protect_first_n=0,
                protect_last_n=3, quiet_mode=True, min_tail_user_messages=0,
                tail_mode="legacy", proactive_prune_tokens=0,
            )
            compressor.tail_token_budget = 256
            # Deliberately retain all production boundary/assembly logic.
            # Fixtures stay below the production pruning minimum, so pruning
            # should not fire. This replacement is the ONLY summarizer.
            calls = []
            def summarize(self, turns, *args, **kwargs):
                prior = self._previous_summary or ""
                text = prior + "\n" + json.dumps(turns, ensure_ascii=False)
                observations = ids(text)
                if not observations:
                    raise RuntimeError("No identifiers reached the summarizer; fixture is confounded by upstream preprocessing")
                selected = observations[::4]
                if policy == "fixed_k10":
                    selected = list(dict.fromkeys(selected + observations[-10:]))
                if policy == "source_anchored":
                    raw = json.dumps(turns, ensure_ascii=False, sort_keys=True).encode()
                    digest = hashlib.sha256(raw).hexdigest()
                    (archive / f"{digest}.json").write_bytes(raw)
                    source = f"\nSource: sha256:{digest}"
                else:
                    source = ""
                calls.append({"input_identifiers": len(observations),
                              "selected_identifiers": len(selected),
                              "input_bytes": len(text.encode()),
                              "summary_payload_bytes": len("\n".join(selected).encode())})
                return self._with_summary_prefix("## Critical Context\n" + "\n".join(selected) + source)
            compressor._generate_summary = types.MethodType(summarize, compressor)
            history = [{"role": "user", "content": "Observe synthetic identifiers. Do not make external requests."}]
            all_ids = []
            for cycle in range(cycles):
                for observation in range(4):
                    token = "RFCID_" + hashlib.sha256(f"20261023:{cycle}:{observation}".encode()).hexdigest()[:24]
                    all_ids.append(token)
                    call_id = f"fixture-{cycle}-{observation}"
                    history.extend([
                        {"role": "assistant", "content": "", "tool_calls": [
                            {"id": call_id, "type": "function", "function": {
                                "name": "synthetic_sensor", "arguments": "{}"}}]},
                        {"role": "tool", "tool_call_id": call_id, "name": "synthetic_sensor",
                         "content": "Observation " + token + " " + ("synthetic observation filler " * 4)},
                    ])
                history = compressor.compress(history, force=True)
            visible = set(ids(json.dumps(history, ensure_ascii=False)))
            in_context = sum(x in visible for x in all_ids)
            recovered = set(visible)
            archive_bytes = 0
            reads = 0
            # This exhaustive source scan is metered. It is not constant-cost
            # retrieval and not equivalent to model recall from the summary.
            if policy == "source_anchored":
                for path in archive.glob("*.json"):
                    raw = path.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != path.stem:
                        raise RuntimeError("archive hash mismatch")
                    recovered.update(ids(raw.decode()))
                    archive_bytes += len(raw)
                    reads += 1
            if len(calls) != cycles or not all(call["input_identifiers"] for call in calls):
                raise RuntimeError(f"Invalid fixture: {len(calls)} identifier-bearing summary calls for {cycles} cycles")
            rows.append({"cycles": cycles, "policy": policy,
                         "observations": len(all_ids), "summarizer_calls": len(calls),
                         "in_context_hits": in_context,
                         "in_context_recall_pct": 100 * in_context / len(all_ids),
                         "source_recoverable_hits": sum(x in recovered for x in all_ids),
                         "archive_bytes": archive_bytes, "archive_reads": reads,
                         "final_context_bytes": len(json.dumps(history).encode()),
                         "summary_measurements": calls})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkout", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    result = {"head": subprocess.check_output(["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True).strip(),
              "scope": "exact-head production compress boundary with isolated deterministic summarizer replacement",
              "rfc_reproduction": False,
              "rfc_blocker": "RFC K-recency patch, probe source, fixture and seed are not published in its body or constituent PR diffs.",
              "ratio_definition": "select every fourth distinct input identifier, not a claim of 4:1 total token ratio",
              "seed": "SHA-256 of 20261023:cycle:observation",
              "rfc_reported_300": {"baseline_pct": 9.6, "k10_pct": 6.1, "delta_pp": -3.5},
              "chatgpt_isolated_reported": {"150_pct": 7.3, "300_pct": 3.65}}
    with tempfile.TemporaryDirectory(prefix="rfc-long-") as temp:
        home = Path(temp)
        os.environ["HERMES_HOME"] = str(home / "home")
        os.environ["HOME"] = str(home / "os-home")
        Path(os.environ["HOME"]).mkdir()
        for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            os.environ[key] = str(home / key.lower())
        def deny_network(event, arguments):
            if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.bind"}:
                raise RuntimeError(f"Network forbidden in synthetic long-session harness: {event}")
        sys.addaudithook(deny_network)
        try:
            result["measurements"] = run(args.checkout.resolve(), home)
        except Exception as exc:
            result["blocker"] = f"{type(exc).__name__}: {exc}"
            result["traceback"] = traceback.format_exc()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key != "measurements"}))
    return 2 if "blocker" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
