"""Audit saved Serena receipts without replaying tasks or claiming model accuracy."""
import argparse
import ast
import json
from pathlib import Path
import statistics

from qualify_serena_semantic import digest, score


def run(args):
    out, inputs = Path(args.artifacts), Path(args.inputs)
    summary = json.loads((out / "summary.json").read_text())
    rows = [json.loads(line) for line in (out / "records.jsonl").read_text().splitlines()]
    tasks = {task["id"]: task for task in json.loads((inputs / "tasks.json").read_text())}
    source = (inputs / "rtk_plugin.py").read_text()
    lines = source.splitlines()
    functions = {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
    assert len(rows) == 27 and len(tasks) == 3
    assert summary["source_sha256"] == digest(inputs / "rtk_plugin.py") == digest(args.hook)
    assert summary["tasks_sha256"] == digest(inputs / "tasks.json")
    assert summary["runner_sha256"] == digest(args.runner)
    receipt = json.loads(Path(args.receipt).read_text())
    assert receipt["terminal"]["exit_code"] == 0
    assert summary["hostname"] == "mbp" and summary["serena_version"] == "2.1.0"
    assert summary["tiktoken_version"] == "0.12.0" and summary["encoding"] == "o200k_base"
    assert summary["provider_usage"] is None and summary["production_enabled"] is False
    for arm in ["full_file", "targeted_shell", "serena_lsp"]:
        selected = [row for row in rows if row["arm"] == arm]
        measured = summary["arms"][arm]
        assert len(selected) == measured["checks"] == 9
        assert measured["passing_evidence_checks"] == sum(row["evidence_pass"] for row in selected) == 9
        assert measured["text_tokens_all_repeats"] == sum(row["text_tokens"] for row in selected)
        assert measured["stderr_tokens_all_repeats"] == sum(row["stderr_tokens"] for row in selected) == 0
        assert measured["p50_call_ms"] == statistics.median(row["wall_ms"] for row in selected)
        assert measured["total_call_ms"] == sum(row["wall_ms"] for row in selected)
        for task_id, task in tasks.items():
            matches = [row for row in selected if row["task"] == task_id]
            assert len(matches) == 3 and {row["repeat"] for row in matches} == {0, 1, 2}
            for row in matches:
                expected = score(row["text"], task["required"], row["error"])
                assert row["missing"] == expected["missing"] and row["evidence_pass"] == expected["evidence_pass"]
                assert row["evidence_pass"] and row["wall_ms"] >= 0
                assert row["provider_usage"] is None and row["model_answer_accuracy"] is None
                if arm == "serena_lsp":
                    assert row["command"] == {"name": task["tool"], "arguments": task["arguments"]}
                    assert row["mcp_response"]["is_error"] is False
                    text = "\n".join(block["text"] for block in row["mcp_response"]["content"] if block["type"] == "text")
                    assert text == row["text"]
                    result = json.loads(text)
                    if task["tool"] == "find_symbol":
                        assert len(result) == 1
                        symbol = result[0]
                        name = task["arguments"]["name_path_pattern"]
                        node = functions[name]
                        assert symbol["name_path"] == name and symbol["relative_path"] == "rtk_plugin.py"
                        assert symbol["body"] == "\n".join(lines[node.lineno - 1:node.end_lineno])
                        assert symbol["body_location"] == {"start_line": node.lineno - 1, "end_line": node.end_lineno - 1}
                    else:
                        assert list(result) == ["rtk_plugin.py"]
                        assert list(result["rtk_plugin.py"]) == ["Function"]
                        refs = result["rtk_plugin.py"]["Function"]
                        assert len(refs) == 1 and refs[0]["name_path"] == "_pre_tool_call"
                        node = functions["_pre_tool_call"]
                        calls = [child for child in ast.walk(node) if isinstance(child, ast.Call)
                                 and isinstance(child.func, ast.Name) and child.func.id == "_rewrite_timeout"]
                        assert len(calls) == 1 and calls[0].lineno == 66
                        assert "65:                timeout=_rewrite_timeout()" in refs[0]["content_around_reference"]
                else:
                    assert row["command"] == (["cat", "rtk_plugin.py"] if arm == "full_file" else task["targeted_command"])
    print("PASS: 27 saved records, 3 tasks x 3 repeats x 3 arms; facts, MCP text/errors, summaries, current hook hashes, fleet exit 0")
    print("NOT PROVEN: representative model accuracy, provider usage, full client dispatch or live enablement.")
    print("Token counts are worker measurements, not independently retokenized by this lightweight metadata audit.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["artifacts", "inputs", "runner", "hook", "receipt"]:
        parser.add_argument("--" + name, required=True)
    run(parser.parse_args())
