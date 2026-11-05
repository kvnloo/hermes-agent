"""Offline RTK evidence-retention check, not a model-answer accuracy benchmark.

Run through fleet-build with the reviewed Z09 input snapshot. No historical
commands, services, provider APIs, or live Hermes profile are executed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args):
    rtk = Path(args.rtk).resolve()
    inputs = Path(args.inputs).resolve()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = json.loads((inputs / "tasks.json").read_text())
    spec = importlib.util.spec_from_file_location("frozen_rtk_hook", inputs / "rtk_plugin.py")
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    records = []
    with tempfile.TemporaryDirectory(prefix="z09-rtk-") as scratch:
        os.environ.update({
            "HOME": scratch,
            "XDG_CONFIG_HOME": scratch + "/config",
            "XDG_DATA_HOME": scratch + "/data",
            "XDG_CACHE_HOME": scratch + "/cache",
            "PATH": str(rtk.parent) + os.pathsep + os.environ["PATH"],
            "NO_COLOR": "1",
            "LC_ALL": "C",
        })
        version = subprocess.run([str(rtk), "--version"], text=True, capture_output=True, check=True)
        consent = subprocess.run([str(rtk), "telemetry", "disable"], text=True, capture_output=True, check=True)
        status = subprocess.run([str(rtk), "telemetry", "status"], text=True, capture_output=True, check=True)
        (out / "telemetry.txt").write_text(consent.stdout + consent.stderr + status.stdout + status.stderr)

        class Context:
            def register_hook(self, name, callback):
                assert name == "pre_tool_call"
                self.callback = callback

        context = Context()
        hook.register(context)
        for repeat in range(3):
            arms = ["raw", "rtk_hook"] if repeat % 2 == 0 else ["rtk_hook", "raw"]
            for task in tasks:
                for arm in arms:
                    payload = {"command": task["command"]}
                    start = time.perf_counter_ns()
                    if arm == "rtk_hook":
                        context.callback(tool_name="terminal", args=payload)
                    proc = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-c", payload["command"]],
                        cwd=inputs, capture_output=True, text=True, timeout=15,
                    )
                    wall_ms = (time.perf_counter_ns() - start) / 1_000_000
                    missing = [fact for fact in task["required"] if fact not in proc.stdout]
                    records.append({
                        "task": task["id"], "question": task["question"],
                        "arm": arm, "repeat": repeat,
                        "command": task["command"], "executed_command": payload["command"],
                        "rewritten": payload["command"] != task["command"],
                        "exit_code": proc.returncode, "expected_exit": task["expected_exit"],
                        "stdout": proc.stdout, "stderr": proc.stderr,
                        "required": task["required"], "missing": missing,
                        "evidence_pass": not missing and proc.returncode == task["expected_exit"],
                        "wall_ms_hook_and_command": wall_ms,
                        "model_answer_accuracy": None, "provider_usage": None,
                    })
    (out / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    summary = {
        "scope": "Deterministic evidence retention on inspected source tasks; not held-out agent accuracy",
        "hostname": platform.node(), "platform": platform.platform(),
        "rtk_version": version.stdout.strip(), "rtk_sha256": digest(rtk),
        "script_sha256": digest(__file__),
        "input_sha256": {p.name: digest(p) for p in sorted(inputs.iterdir()) if p.is_file()},
        "repeats": 3, "tasks": len(tasks), "arms": {},
        "headroom": "not exercised; command resolution is not an installation audit",
        "serena": "not exercised; command resolution is not an installation audit",
    }
    for arm in ["raw", "rtk_hook"]:
        selected = [r for r in records if r["arm"] == arm]
        summary["arms"][arm] = {
            "passing_evidence_checks": sum(r["evidence_pass"] for r in selected),
            "checks": len(selected),
            "rewritten_commands": sum(r["rewritten"] for r in selected),
            "p50_hook_and_command_ms": statistics.median(r["wall_ms_hook_and_command"] for r in selected),
            "failures": [{"task": r["task"], "repeat": r["repeat"], "exit_code": r["exit_code"], "missing": r["missing"]} for r in selected if not r["evidence_pass"]],
        }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    # A lossy treatment is an experiment result, not a harness failure.
    return 0 if all(r["evidence_pass"] for r in records if r["arm"] == "raw") else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtk", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--out", required=True)
    raise SystemExit(run(parser.parse_args()))
