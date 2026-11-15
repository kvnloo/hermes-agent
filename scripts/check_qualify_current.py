"""Validate current Z09 saved receipts without replaying tasks or calling a model."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args):
    artifacts, inputs = Path(args.artifacts), Path(args.inputs)
    summary = json.loads((artifacts / "summary.json").read_text())
    records = [json.loads(line) for line in (artifacts / "records.jsonl").read_text().splitlines()]
    tasks = {task["id"]: task for task in json.loads((inputs / "tasks.json").read_text())}
    assert len(tasks) == 7 and len(records) == 84
    assert summary["script_sha256"] == digest(args.runner)
    for name, expected in summary["input_sha256"].items():
        assert digest(inputs / name) == expected, name
    assert digest(args.hook) == summary["input_sha256"]["rtk_plugin.py"], "Installed hook has drifted"
    assert digest(args.rtk) == summary["rtk_sha256"], "Installed RTK binary has drifted"
    assert summary["provider_usage"] is None
    assert json.loads(Path(args.receipt).read_text())["terminal"]["exit_code"] == 0
    assert summary["hostname"] == "mbp"
    for arm in ["raw", "rtk_hook", "headroom_agent", "headroom_default_no_ml"]:
        rows = [row for row in records if row["arm"] == arm]
        measured = summary["arms"][arm]
        assert len(rows) == measured["checks"] == 21
        assert measured["passing_evidence_checks"] == sum(row["evidence_pass"] for row in rows)
        assert measured["transform_errors"] == sum(row["transform_error"] is not None for row in rows)
        assert measured["stdout_tokens_all_repeats"] == sum(row["stdout_tokens"] for row in rows)
        assert measured["stderr_tokens_all_repeats"] == sum(row["stderr_tokens"] for row in rows)
        assert measured["p50_terminal_and_transform_ms"] == statistics.median(row["wall_ms_terminal_and_transform"] for row in rows)
        assert measured["rewritten_commands"] == sum(row["rewritten"] for row in rows)
        for task_id, task in tasks.items():
            selected = [row for row in rows if row["task"] == task_id]
            assert len(selected) == 3 and {row["repeat"] for row in selected} == {0, 1, 2}
            for row in selected:
                missing = [fact for fact in task["required"] if fact not in row["stdout"]]
                assert missing == row["missing"]
                assert row["evidence_pass"] == (not missing and row["exit_code"] == task["expected_exit"] and row["transform_error"] is None)
                assert row["provider_usage"] is None and row["model_answer_accuracy"] is None
    print("PASS: 84 records, all arm summaries, exact required facts, repeats, source hashes, current installed RTK/hook hashes, and fleet exit 0")
    print("Treatment failures remain experiment results. NOT PROVEN: model accuracy, full Hermes dispatch, provider usage, Serena.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["artifacts", "inputs", "runner", "hook", "rtk", "receipt"]:
        parser.add_argument("--" + name, required=True)
    run(parser.parse_args())
