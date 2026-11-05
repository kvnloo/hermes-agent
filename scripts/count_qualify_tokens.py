"""Count saved terminal text, not provider usage, using a pinned local vocabulary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import statistics
import time


def run(args):
    start = time.perf_counter()
    vocabulary = Path(args.vocabulary).resolve()
    expected = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
    if hashlib.sha256(vocabulary.read_bytes()).hexdigest() != expected:
        raise ValueError("Vocabulary hash mismatch")
    url = "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
    cache = vocabulary.parent / hashlib.sha1(url.encode()).hexdigest()
    if cache != vocabulary:
        shutil.copyfile(vocabulary, cache)
    os.environ["TIKTOKEN_CACHE_DIR"] = str(vocabulary.parent)

    def deny(*_args, **_kwargs):
        raise RuntimeError("Token counting must not access the network")

    socket.socket.connect = deny
    socket.create_connection = deny
    import tiktoken
    encoding = tiktoken.get_encoding("o200k_base")
    records = [json.loads(line) for line in Path(args.records).read_text().splitlines()]
    result = {
        "encoding": encoding.name, "vocabulary_sha256": expected,
        "scope": "Saved stdout and stderr text only; not model input/output or billing receipts",
        "tasks": [], "provider_usage": None,
    }
    for task in dict.fromkeys(row["task"] for row in records):
        item = {"task": task}
        for arm in ["raw", "rtk_hook"]:
            rows = [r for r in records if r["task"] == task and r["arm"] == arm]
            outputs = {r["stdout"] for r in rows}
            errors = {r["stderr"] for r in rows}
            if len(outputs) != 1 or len(errors) != 1:
                raise ValueError("Output changed between repetitions: " + task + " " + arm)
            item[arm] = {
                "stdout_tokens": len(encoding.encode(rows[0]["stdout"], disallowed_special=())),
                "stderr_tokens": len(encoding.encode(rows[0]["stderr"], disallowed_special=())),
                "stdout_bytes": len(rows[0]["stdout"].encode()),
                "p50_hook_and_command_ms": statistics.median(r["wall_ms_hook_and_command"] for r in rows),
                "evidence_passes": sum(r["evidence_pass"] for r in rows),
            }
        result["tasks"].append(item)
    for arm in ["raw", "rtk_hook"]:
        result[arm + "_stdout_tokens_one_pass"] = sum(task[arm]["stdout_tokens"] for task in result["tasks"])
        result[arm + "_stderr_tokens_one_pass"] = sum(task[arm]["stderr_tokens"] for task in result["tasks"])
    result["elapsed_s"] = time.perf_counter() - start
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True)
    parser.add_argument("--vocabulary", required=True)
    parser.add_argument("--out", required=True)
    run(parser.parse_args())
