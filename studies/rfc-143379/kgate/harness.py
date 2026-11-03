"""REAL Hermes compressor, deterministic replaced LLM seam; NOT model recall.

K is requested optional recency in user rounds, not a claimed exact native tail:
K0 disables optional multi-user protection; Hermes still requires active anchors.
K10 asks the native guard for ten recent user rounds. All realized tail tokens
and actual compression ratios are measured. No post-hoc cohort/ratio dropping.
"""
import argparse
from contextlib import ExitStack
from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from manifest import CHECKPOINTS, SLOTS_PER_CYCLE, load_manifest, source
from stats import PairedRow, digest, evaluate

MAIN_SHA = "e82bf01eec9bb58848209b07f0bc7d8895a39f9b"
SCORER = "v1: exact target_literal substring in visible message content after compress; no tool arguments"


def exact_present(messages, literal):
    return int(any(literal in (m.get("content") or "") for m in messages))


def no_network(*args, **kwargs):
    raise AssertionError("network forbidden in deterministic boundary harness")


def verify_pin():
    from agent import context_compressor as cc
    root = Path(cc.__file__).resolve().parents[1]
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if actual != MAIN_SHA:
        raise ValueError(f"wrong compressor checkout: {actual}; need {MAIN_SHA}")
    return cc


def new_rounds(seed, cycle):
    messages = []
    for slot in range(1, SLOTS_PER_CYCLE + 1):
        # Fixed non-target interference creates enough compressible middle for
        # an 8x request without changing the ten-round tail or frozen targets.
        padding = " Context filler for the synthetic workload." * 32 if slot <= 30 else ""
        messages += [{"role": "user", "content": f"Inspect synthetic record {cycle}/{slot}." + padding},
                     {"role": "assistant", "content": source(seed, cycle, slot)}]
    # Exercise the real deterministic tool-result pruning path each generation.
    # The target literals are not in this tool payload or its call arguments.
    call_id = f"tool-{seed}-{cycle}"
    messages[2:2] = [{"role": "assistant", "content": "", "tool_calls": [{
        "id": call_id, "type": "function", "function": {
            "name": "terminal", "arguments": json.dumps({"command": "synthetic-no-execution"})}}]},
        {"role": "tool", "tool_name": "terminal", "tool_call_id": call_id,
         "content": f"cycle {cycle}: " + "synthetic tool observation. " * 100},
        {"role": "assistant", "content": "Tool observation received."}]
    return messages


def run_arm(cc, seed, ratio, k, probes, checkpoints=CHECKPOINTS):
    from agent.model_metadata import estimate_messages_tokens_rough, estimate_tokens_rough
    compressor = cc.ContextCompressor(model="study/no-model", quiet_mode=True,
        config_context_length=100000, protect_first_n=1, protect_last_n=0,
        min_tail_user_messages=k, tail_mode="legacy", abort_on_summary_failure=True)
    compressor.tail_token_budget = 1  # native anchors, not a replacement cut implementation
    messages = [{"role": "system", "content": "Synthetic deterministic boundary study."}]
    trace = []
    checkpoints_out = {}
    generation_calls = 0
    target_total = 900  # identical total post-boundary budget in both arms
    scaffold_tokens = 70
    raw_summary_tokens = 0

    def summarizer(prompt, started):
        nonlocal generation_calls, raw_summary_tokens
        generation_calls += 1
        telemetry = compressor._active_compression_telemetry
        tail = telemetry["protected_tail_tokens"] or 0
        head = telemetry["protected_head_tokens"] or 0
        # Fixed total output budget: K10 consumes room otherwise available to the
        # summary. A constant, literal-free replacement is intentionally lossy.
        budget = max(30, target_total - tail - head - scaffold_tokens)
        text = "## Goal\nContinue the synthetic study.\n## Progress\nEarlier observations were processed.\n"
        unit = "Background observation recorded.\n"
        low, high = 0, max(1, budget)
        while low < high:
            middle = (low + high + 1) // 2
            if estimate_tokens_rough(text + unit * middle) < budget:
                low = middle
            else:
                high = middle - 1
        text += unit * low
        raw_summary_tokens = estimate_tokens_rough(text)
        return text

    with patch.object(compressor, "_call_summary_llm", side_effect=summarizer):
        for cycle in range(1, max(checkpoints) + 1):
            raw_rounds = new_rounds(seed, cycle)
            raw_digest = digest(raw_rounds)
            messages.extend(raw_rounds)
            before = estimate_messages_tokens_rough(messages)
            # Budget declared before either arm runs; same function of the frozen
            # source workload, not arm-specific input or observed outcomes.
            source_tokens = estimate_messages_tokens_rough(raw_rounds)
            target_total = max(100, int(source_tokens / (ratio - 1)))
            calls_before = generation_calls
            previous_count = compressor.compression_count
            result = compressor.compress(messages, current_tokens=before, force=True)
            if generation_calls != calls_before + 1 or compressor.compression_count != previous_count + 1:
                raise AssertionError(f"generation {cycle} was not a real successful summary boundary")
            telemetry = compressor._last_compression_telemetry
            if telemetry.get("fallback_used"):
                raise AssertionError("unexpected fallback; replaced summarizer must run")
            messages = result
            after = estimate_messages_tokens_rough(messages)
            tail = telemetry["protected_tail_tokens"] or 0
            head = telemetry["protected_head_tokens"] or 0
            # Price native prefix/scaffold and merge overhead, not target hits.
            # This deterministic budget controller settles before checkpoints;
            # every transient mismatch remains in the complete per-cycle trace.
            scaffold_tokens = max(0, after - tail - head - raw_summary_tokens)
            summary = max(0, after - tail - head)
            trace.append({"cycle": cycle, "source_digest": raw_digest,
                          "tokens_before": before, "tokens_after": after,
                          "ratio_actual": before / after, "token_budget": target_total,
                          "retained_K_tokens": telemetry["protected_tail_tokens"],
                          "summary_tokens": summary, "summary_calls": generation_calls,
                          "compression_count": compressor.compression_count,
                          "tool_results_pruned": telemetry.get("tool_results_pruned"),
                          "target_literals_present": sum(exact_present(messages, p.target_literal) for p in probes)})
            if cycle in checkpoints:
                checkpoints_out[cycle] = {"trace": trace[-1],
                    "scores": {p.probe_id: exact_present(messages, p.target_literal) for p in probes}}
    return checkpoints_out, trace


def run(manifest_path, out, checkpoints=CHECKPOINTS):
    payload, probes = load_manifest(manifest_path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    traces = []
    for name in ("paired.jsonl", "trace.jsonl", "progress.jsonl"):
        (out / name).write_text("")
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", no_network))
        stack.enter_context(patch.object(socket, "create_connection", no_network))
        cc = verify_pin()
        for seed in sorted({p.session_seed for p in probes}):
            subset = [p for p in probes if p.session_seed == seed]
            for ratio in payload["ratios_requested"]:
                order = (0, 10) if seed % 2 == 0 else (10, 0)
                arms = {}
                arm_sources = {}
                for k in order:
                    arms[k], trace = run_arm(cc, seed, ratio, k, subset, checkpoints)
                    batch = [{"session_seed": seed, "ratio_target": ratio, "k": k, **t} for t in trace]
                    traces.extend(batch)
                    with (out / "trace.jsonl").open("a") as trace_file:
                        trace_file.write("".join(json.dumps(t, sort_keys=True) + "\n" for t in batch))
                    arm_sources[k] = [t["source_digest"] for t in trace]
                assert arm_sources[0] == arm_sources[10], "unpaired source trajectory"
                trajectory = digest(arm_sources[0])
                batch_start = len(rows)
                for cycle in checkpoints:
                    a, b = arms[10][cycle], arms[0][cycle]
                    ta, tb = a["trace"], b["trace"]
                    assert ta["token_budget"] == tb["token_budget"]
                    for probe in subset:
                        rows.append(PairedRow(probe, cycle, ratio, ta["ratio_actual"], tb["ratio_actual"],
                            a["scores"][probe.probe_id], b["scores"][probe.probe_id], payload["probes_digest"],
                            ta["retained_K_tokens"], tb["retained_K_tokens"], ta["summary_tokens"],
                            tb["summary_tokens"], ta["token_budget"], ",".join(f"K{k}" for k in order),
                            "deterministic_boundary", "NO_MODEL", sha256((SCORER + inspect.getsource(exact_present)).encode()).hexdigest(),
                            trajectory, "native-compress-phase1;legacy-tail", "none", 0))
                with (out / "paired.jsonl").open("a") as paired_file:
                    paired_file.write("".join(json.dumps(r.to_dict(), sort_keys=True) + "\n"
                                              for r in rows[batch_start:]))
                # Append batch receipts so a later failure cannot erase progress.
                with (out / "progress.jsonl").open("a") as progress:
                    progress.write(json.dumps({"seed": seed, "ratio": ratio, "completed": list(checkpoints)}) + "\n")
    assert len(rows) == len(probes) * len(checkpoints) * len(payload["ratios_requested"])
    for name, records in (("paired.jsonl", [r.to_dict() for r in rows]), ("trace.jsonl", traces)):
        assert [json.loads(line) for line in (out / name).read_text().splitlines()] == records
    report = {"measurement": "deterministic boundary measurement, NOT model recall",
              "main_sha": MAIN_SHA, "manifest_digest": payload["probes_digest"],
              "rows": len(rows), "trace_rows": len(traces),
              "successful_compressions": sum(t["cycle"] == max(checkpoints) for t in traces) * max(checkpoints),
              "gate": evaluate(rows, probes),
              "caveats": ["K0 retains mandatory native active-turn anchors; not a zero-tail fiction",
                          "K10 is ten native user-round anchors; actual tokens are measured",
                          "Requested ratios are not assumed realized; all rows retained",
                          "No real paraphrase, retrieval, model inference, or production certification"]}
    (out / "harness-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("frozen-manifest.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    # The hosted runner supplies a disposable home; refuse accidental live-home use.
    if not os.environ.get("HERMES_HOME"):
        parser.error("set an isolated HERMES_HOME before importing Hermes")
    result = run(args.manifest, args.out)
    print(json.dumps({k: result[k] for k in ("measurement", "main_sha", "rows", "trace_rows")}))
