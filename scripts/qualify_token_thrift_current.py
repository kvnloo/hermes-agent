"""Extend the existing Z09 command check to current RTK and offline Headroom.

This measures exact fact retention and terminal-plus-transform latency, not
model answers, Hermes dispatch, or provider usage. No historical chats are read.
"""
import argparse
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import socket
import statistics
import subprocess
import tempfile
import time

from qualify_token_thrift import digest


def score(stdout, exit_code, task, error=None):
    missing = [fact for fact in task["required"] if fact not in stdout]
    return {"missing": missing, "evidence_pass": not missing and exit_code == task["expected_exit"] and error is None}


def self_check():
    task = {"required": ["required fact"], "expected_exit": 0}
    assert score("required fact", 0, task)["evidence_pass"]
    assert not score("0 errors", 0, task)["evidence_pass"]
    assert not score("required fact", 1, task)["evidence_pass"]
    assert not score("required fact", 0, task, "compression failed")["evidence_pass"]
    print("PASS: scorer rejects missing facts, changed exits, and transform errors")


def run(args):
    inputs, out = Path(args.inputs).resolve(), Path(args.out)
    rtk = Path(args.rtk).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tasks = json.loads((inputs / "tasks.json").read_text())
    vocabulary = Path(args.vocabulary).resolve()
    expected = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
    assert digest(vocabulary) == expected
    url = "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
    cache_name = hashlib.sha1(url.encode()).hexdigest()
    spec = importlib.util.spec_from_file_location("current_rtk_hook", inputs / "rtk_plugin.py")
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    records = []
    with tempfile.TemporaryDirectory(prefix="z09-current-") as scratch:
        os.environ.update({
            "HOME": scratch, "XDG_CONFIG_HOME": scratch + "/config",
            "XDG_DATA_HOME": scratch + "/data", "XDG_CACHE_HOME": scratch + "/cache",
            "TIKTOKEN_CACHE_DIR": scratch, "HEADROOM_OFFLINE": "1",
            "HF_HUB_OFFLINE": "1", "LITELLM_LOCAL_MODEL_COST_MAP": "True",
            "PATH": str(rtk.parent) + os.pathsep + os.environ["PATH"],
            "NO_COLOR": "1", "LC_ALL": "C",
        })
        Path(scratch, cache_name).write_bytes(vocabulary.read_bytes())

        def deny(*_args, **_kwargs):
            raise RuntimeError("Qualification must not access the network")

        socket.socket.connect = deny
        socket.create_connection = deny
        import tiktoken
        from headroom import compress
        encoding = tiktoken.get_encoding("o200k_base")
        version = subprocess.run([str(rtk), "--version"], text=True, capture_output=True, check=True)
        consent = subprocess.run([str(rtk), "telemetry", "disable"], text=True, capture_output=True, check=True)
        status = subprocess.run([str(rtk), "telemetry", "status"], text=True, capture_output=True, check=True)
        (out / "telemetry.txt").write_text(consent.stdout + status.stdout + consent.stderr + status.stderr)

        class Context:
            def register_hook(self, name, callback):
                assert name == "pre_tool_call"
                self.callback = callback

        context = Context()
        hook.register(context)
        arms = ["raw", "rtk_hook", "headroom_agent", "headroom_default_no_ml"]
        for repeat in range(3):
            ordered = arms[repeat:] + arms[:repeat]
            for task in tasks:
                for arm in ordered:
                    payload = {"command": task["command"]}
                    start = time.perf_counter_ns()
                    if arm == "rtk_hook":
                        context.callback(tool_name="terminal", args=payload)
                    proc = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-c", payload["command"]],
                        cwd=inputs, capture_output=True, text=True, timeout=15,
                    )
                    text, error, transforms, lossless = proc.stdout, None, [], None
                    if arm.startswith("headroom_"):
                        messages = [
                            {"role": "user", "content": task["question"]},
                            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "terminal", "arguments": json.dumps({"command": task["command"]})}}]},
                            {"role": "tool", "tool_call_id": "c1", "content": text},
                        ]
                        try:
                            result = compress(copy.deepcopy(messages), model="gpt-4o", protect_recent=0,
                                              mode="agent" if arm == "headroom_agent" else None,
                                              kompress_model="disabled")
                            text = result.messages[-1]["content"]
                            if not isinstance(text, str):
                                text = json.dumps(text)
                            transforms, lossless = result.transforms_applied, result.lossless
                        except Exception as exc:
                            error = repr(exc)
                    elapsed = (time.perf_counter_ns() - start) / 1_000_000
                    records.append({
                        "task": task["id"], "arm": arm, "repeat": repeat,
                        "command": task["command"], "executed_command": payload["command"],
                        "rewritten": payload["command"] != task["command"],
                        "stdout": text, "stderr": proc.stderr, "exit_code": proc.returncode,
                        "transform_error": error, "transforms": transforms, "lossless": lossless,
                        "stdout_tokens": len(encoding.encode(text, disallowed_special=())),
                        "stderr_tokens": len(encoding.encode(proc.stderr, disallowed_special=())),
                        "wall_ms_terminal_and_transform": elapsed,
                        "model_answer_accuracy": None, "provider_usage": None,
                        **score(text, proc.returncode, task, error),
                    })
    summary = {
        "scope": "Inspected source fact retention, not held-out model-answer accuracy or full Hermes dispatch",
        "hostname": platform.node(), "rtk_version": version.stdout.strip(),
        "headroom_version": importlib.metadata.version("headroom-ai"),
        "rtk_sha256": digest(rtk), "script_sha256": digest(__file__),
        "input_sha256": {p.name: digest(p) for p in sorted(inputs.iterdir()) if p.is_file()},
        "tokenizer": "o200k_base", "vocabulary_sha256": expected,
        "network": "Python socket connections denied; RTK telemetry disabled in temporary HOME",
        "headroom_settings": {"protect_recent": 0, "kompress_model": "disabled", "model_for_tokenization_only": "gpt-4o"},
        "provider_usage": None, "serena": "not exercised", "arms": {},
    }
    for arm in arms:
        rows = [r for r in records if r["arm"] == arm]
        summary["arms"][arm] = {
            "checks": len(rows), "passing_evidence_checks": sum(r["evidence_pass"] for r in rows),
            "transform_errors": sum(r["transform_error"] is not None for r in rows),
            "rewritten_commands": sum(r["rewritten"] for r in rows),
            "stdout_tokens_all_repeats": sum(r["stdout_tokens"] for r in rows),
            "stderr_tokens_all_repeats": sum(r["stderr_tokens"] for r in rows),
            "p50_terminal_and_transform_ms": statistics.median(r["wall_ms_terminal_and_transform"] for r in rows),
        }
    (out / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if all(r["evidence_pass"] for r in records if r["arm"] == "raw") else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--rtk")
    parser.add_argument("--inputs")
    parser.add_argument("--out")
    parser.add_argument("--vocabulary")
    args = parser.parse_args()
    if args.self_check:
        self_check()
    else:
        if not all([args.rtk, args.inputs, args.out, args.vocabulary]):
            parser.error("--rtk, --inputs, --out, and --vocabulary are required")
        raise SystemExit(run(args))
