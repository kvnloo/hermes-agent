"""Check saved Z09 receipts and source hashes without rerunning task commands."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def run(args):
    artifacts = Path(args.artifacts)
    inputs = Path(args.inputs)
    summary = json.loads((artifacts / "summary.json").read_text())
    tokens = json.loads((artifacts / "tokens.json").read_text())
    records = [json.loads(line) for line in (artifacts / "records.jsonl").read_text().splitlines()]
    tasks = {t["id"]: t for t in json.loads((inputs / "tasks.json").read_text())}
    assert len(tasks) == 7 and len(records) == 42
    assert hashlib.sha256(Path(args.runner).read_bytes()).hexdigest() == summary["script_sha256"]
    for name, expected in summary["input_sha256"].items():
        assert hashlib.sha256((inputs / name).read_bytes()).hexdigest() == expected, name
    for arm in ["raw", "rtk_hook"]:
        selected = [r for r in records if r["arm"] == arm]
        assert len(selected) == 21
        assert sum(r["rewritten"] for r in selected) == (18 if arm == "rtk_hook" else 0)
        assert summary["arms"][arm]["p50_hook_and_command_ms"] == statistics.median(r["wall_ms_hook_and_command"] for r in selected)
        for r in selected:
            task = tasks[r["task"]]
            assert r["exit_code"] == task["expected_exit"]
            assert all(fact in r["stdout"] for fact in task["required"])
            assert r["model_answer_accuracy"] is None and r["provider_usage"] is None
        for task_id in tasks:
            rows = [r for r in selected if r["task"] == task_id]
            assert {r["repeat"] for r in rows} == {0, 1, 2}
    for task_id in tasks:
        for repeat in range(3):
            pair = [r for r in records if r["task"] == task_id and r["repeat"] == repeat]
            assert len(pair) == 2 and pair[0]["stdout"] == pair[1]["stdout"]
            assert pair[0]["stderr"] == pair[1]["stderr"]
    assert tokens["raw_stdout_tokens_one_pass"] == tokens["rtk_hook_stdout_tokens_one_pass"] == 2331
    receipt = json.loads(Path(args.receipt).read_text())
    assert receipt["terminal"]["exit_code"] == 0
    assert summary["hostname"] == "mbp"
    print("PASS: 42 saved records, exact required facts and exits, alternating repeats, identical paired output text, source hashes, and fleet exit 0")
    print("NOT PROVEN: model-answer accuracy, full Hermes dispatch, provider usage, Headroom or Serena behavior")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--receipt", required=True)
    run(parser.parse_args())
