"""Compare real Serena LSP retrieval with full-file and targeted shell reads.

Exact source-fact retention is not model-answer accuracy. No model is called.
"""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def facts(text):
    """Decode JSON tool text for fact scoring, but count the original text tokens."""
    try:
        value = json.loads(text)
    except ValueError:
        return text
    def strings(item):
        if isinstance(item, str):
            return item
        if isinstance(item, list):
            return "\n".join(strings(child) for child in item)
        if isinstance(item, dict):
            return "\n".join(str(key) + ": " + strings(child) for key, child in item.items())
        return str(item)
    return strings(value)


def score(text, required, error):
    missing = [fact for fact in required if fact not in facts(text)]
    return {"missing": missing, "evidence_pass": not missing and not error}


def self_check():
    assert score('{"body":"required\\nsource"}', ["required\nsource"], False)["evidence_pass"]
    assert not score("0 errors", ["required source"], False)["evidence_pass"]
    assert not score("required source", ["required source"], True)["evidence_pass"]
    assert not score("[]", ["real caller"], False)["evidence_pass"]
    print("PASS: scorer accepts decoded source and rejects missing facts, tool errors and empty references")


async def run(args):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import tiktoken

    project = Path(args.inputs).resolve()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    assert not (out / "records.jsonl").exists(), "Choose a fresh output directory; never append to an old experiment"
    tasks = json.loads((project / "tasks.json").read_text())
    assert digest(args.vocabulary) == "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
    records = []
    with tempfile.TemporaryDirectory(prefix="z09-serena-home-") as home:
        url = "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
        cache = Path(home, hashlib.sha1(url.encode()).hexdigest())
        cache.write_bytes(Path(args.vocabulary).read_bytes())
        os.environ["TIKTOKEN_CACHE_DIR"] = home
        encoding = tiktoken.get_encoding("o200k_base")
        env = {key: value for key, value in os.environ.items() if key not in {
            "DISPLAY", "WAYLAND_DISPLAY", "SWAYSOCK", "HYPRLAND_INSTANCE_SIGNATURE", "DBUS_SESSION_BUS_ADDRESS"}}
        env.update(HOME=home, XDG_CONFIG_HOME=home + "/config", XDG_CACHE_HOME=home + "/cache",
                   BROWSER="/bin/false", PATH=str(Path.cwd()) + os.pathsep + env["PATH"])
        params = StdioServerParameters(command=str(Path(sys.executable).parent / "serena"), args=[
            "start-mcp-server", "--transport", "stdio", "--agent-interface", "tools", "--project", str(project),
            "--enable-web-dashboard", "false", "--open-web-dashboard", "false", "--enable-gui-log-window", "false"], env=env)
        started = time.perf_counter()
        with (out / "server-stderr.log").open("w") as errlog:
            async with asyncio.timeout(300):
                async with stdio_client(params, errlog=errlog) as streams:
                    async with ClientSession(*streams) as session:
                        initialized = await session.initialize()
                        tools = await session.list_tools()
                        instructions = await session.call_tool("initial_instructions", {})
                        assert not instructions.is_error
                        bootstrap_ms = (time.perf_counter() - started) * 1000
                        (out / "bootstrap.json").write_text(json.dumps({
                            "initialize": initialized.model_dump(mode="json"), "tools": tools.model_dump(mode="json"),
                            "instructions": instructions.model_dump(mode="json"), "wall_ms": bootstrap_ms}, indent=2) + "\n")
                        available = {tool.name for tool in tools.tools}
                        assert all(task["tool"] in available for task in tasks)
                        arms = ["full_file", "targeted_shell", "serena_lsp"]
                        for repeat in range(3):
                            for task in tasks:
                                for arm in arms[repeat:] + arms[:repeat]:
                                    start = time.perf_counter()
                                    response = None
                                    if arm == "serena_lsp":
                                        response = await session.call_tool(task["tool"], task["arguments"])
                                        text = "\n".join(block.text for block in response.content if block.type == "text")
                                        stderr = ""
                                        error = response.is_error
                                        command = {"name": task["tool"], "arguments": task["arguments"]}
                                    else:
                                        command = ["cat", "rtk_plugin.py"] if arm == "full_file" else task["targeted_command"]
                                        result = subprocess.run(command, cwd=project, capture_output=True, text=True, timeout=30)
                                        text, stderr, error = result.stdout, result.stderr, result.returncode != 0
                                    wall_ms = (time.perf_counter() - start) * 1000
                                    record = {"task": task["id"], "arm": arm, "repeat": repeat, "command": command,
                                              "text": text, "stderr": stderr, "error": error, "wall_ms": wall_ms,
                                              "text_tokens": len(encoding.encode(text, disallowed_special=())),
                                              "stderr_tokens": len(encoding.encode(stderr, disallowed_special=())),
                                              "mcp_response": response.model_dump(mode="json") if response is not None else None,
                                              "provider_usage": None, "model_answer_accuracy": None,
                                              **score(text, task["required"], error)}
                                    records.append(record)
                                    with (out / "records.jsonl").open("a") as handle:
                                        handle.write(json.dumps(record) + "\n")
                                    print(task["id"], arm, repeat, record["evidence_pass"], round(wall_ms, 3), flush=True)
        summary = {"scope": "Three inspected tasks on one real hook file. Source evidence only, not representative model accuracy.",
                   "hostname": platform.node(), "serena_version": importlib.metadata.version("serena-agent"),
                   "tiktoken_version": importlib.metadata.version("tiktoken"), "encoding": "o200k_base",
                   "source_sha256": digest(project / "rtk_plugin.py"), "tasks_sha256": digest(project / "tasks.json"),
                   "runner_sha256": digest(__file__), "bootstrap_ms": bootstrap_ms,
                   "bootstrap_text_tokens": sum(len(encoding.encode(block.text, disallowed_special=())) for block in instructions.content if block.type == "text"),
                   "bootstrap_tool_schemas_json_tokens": len(encoding.encode(tools.model_dump_json(), disallowed_special=())),
                   "provider_usage": None, "production_enabled": False, "arms": {}}
        for arm in ["full_file", "targeted_shell", "serena_lsp"]:
            rows = [row for row in records if row["arm"] == arm]
            summary["arms"][arm] = {"checks": len(rows), "passing_evidence_checks": sum(row["evidence_pass"] for row in rows),
                                     "text_tokens_all_repeats": sum(row["text_tokens"] for row in rows),
                                     "stderr_tokens_all_repeats": sum(row["stderr_tokens"] for row in rows),
                                     "p50_call_ms": statistics.median(row["wall_ms"] for row in rows),
                                     "first_call_ms": rows[0]["wall_ms"], "total_call_ms": sum(row["wall_ms"] for row in rows)}
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        assert all(row["evidence_pass"] for row in records), "Retained task-evidence failures; do not qualify"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--inputs", default="scripts/fixtures/z09-semantic")
    parser.add_argument("--out", default="serena-semantic")
    parser.add_argument("--vocabulary", default="o200k_base.tiktoken")
    args = parser.parse_args()
    if args.self_check:
        self_check()
    else:
        asyncio.run(run(args))
