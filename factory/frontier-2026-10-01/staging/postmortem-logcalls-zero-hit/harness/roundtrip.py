"""Producer -> parser round trip (T1, direct calls, no network).

Drives the REAL agent.turn_usage.record_response_usage of the checkout at argv[1] for five provider
usage shapes (hit, miss, cold write, no cache field, no usage at all), writes the lines through the real
agent.log formatter (hermes_logging._LOG_FORMAT with the session tag), then parses that log with each
logcalls.py variant given as label=path. Prints one JSON object.

Isolation: env cleared, HOME/HERMES_HOME in a fresh temp dir, loopback-only socket guard (lifted from
evals/provider_fallback/probe_104260.py), audit hook that fails on any exec/subprocess.
"""
import importlib.util
import inspect
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO, ARM = sys.argv[1], sys.argv[2]
PARSERS = dict(a.split("=", 1) for a in sys.argv[3:])
sys.dont_write_bytecode = True
sandbox = tempfile.mkdtemp(prefix="pmlc-rt-")
os.environ.clear()
os.environ.update(HOME=sandbox, HERMES_HOME=sandbox + "/hermes", PATH="/usr/bin:/bin",
                  PYTHONDONTWRITEBYTECODE="1", HERMES_DISABLE_MODEL_METADATA_FETCH="1")
Path(os.environ["HERMES_HOME"]).mkdir()
os.chdir(sandbox)
sys.path.insert(0, REPO)

import socket  # noqa: E402

_orig_connect = socket.socket.connect
blocked = []


def _loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
        blocked.append(str(address))
        raise RuntimeError("round trip blocks non-loopback network")
    return _orig_connect(self, address)


socket.socket.connect = _loopback_only
exec_attempts = []
probe_reads = []


def _audit(event, args):
    if event == "subprocess.Popen":
        argv0 = os.path.basename(str(args[0] or (args[1][0] if args[1] else "")))
        # read-only probes seen at import: hermes_cli/version_info.py (git), ctypes.util.find_library (ldconfig -p)
        if argv0 in ("git", "ldconfig"):
            probe_reads.append(" ".join(map(str, args[1]))[:80])
            return
    if event in ("os.exec", "os.posix_spawn", "subprocess.Popen", "os.system"):
        exec_attempts.append(f"{event}:{os.path.basename(str(args[0])) if args else ''}" + (f":{args[1][:3]}" if event == "subprocess.Popen" and len(args) > 1 else ""))
        raise RuntimeError(f"round trip blocks {event}")


sys.addaudithook(_audit)

import hermes_logging  # noqa: E402
from agent import turn_usage  # noqa: E402
from run_agent import AIAgent  # noqa: E402

SID = "rt1"
log_path = Path(sandbox) / "agent.log"
handler = logging.FileHandler(log_path, encoding="utf-8")
handler.setFormatter(logging.Formatter(hermes_logging._LOG_FORMAT))
turn_usage.logger.addHandler(handler)
turn_usage.logger.setLevel(logging.INFO)
hermes_logging.set_session_context(SID)

agent = AIAgent(api_key="fixture", provider="openai", api_mode="chat_completions",
                base_url="https://api.openai.com/v1", model="gpt-4o", quiet_mode=True,
                skip_context_files=True, skip_memory=True, enabled_toolsets=[], session_id=SID)
supports_ttfb = "api_start_time" in inspect.signature(turn_usage.record_response_usage).parameters
CASES = [
    ("hit", {"cached_tokens": 40, "cache_write_tokens": 0}),
    ("miss", {"cached_tokens": 0, "cache_write_tokens": 0}),
    ("cold_write", {"cached_tokens": 0, "cache_write_tokens": 60}),
    ("no_field", {}),
    ("unavailable", None),
]
emitted = []
try:
    for i, (name, details) in enumerate(CASES, 1):
        usage = None if details is None else {"prompt_tokens": 100, "completion_tokens": 7, "prompt_tokens_details": details}
        resp = SimpleNamespace(usage=usage, id=f"r{i}", provider="Fixture upstream", model="gpt-4o", choices=None)
        kw = {}
        if supports_ttfb:
            agent._last_api_first_chunk_at = 1_000.0 + 1.5
            kw["api_start_time"] = 1_000.0
        turn_usage.record_response_usage(agent, resp, messages=[{"role": "user", "content": "x"}], api_call_count=1,
                                         api_duration=0.2, compression_attempts=0, max_compression_attempts=3, **kw)
        emitted.append(name)
finally:
    handler.flush()
    turn_usage.logger.removeHandler(handler)
    handler.close()
    agent.close()

lines = [ln.rstrip("\n") for ln in log_path.read_text(encoding="utf-8").splitlines(True) if "API call #" in ln]
result = {"arm": ARM, "repo_head_files": {}, "supports_ttfb": supports_ttfb, "cases": emitted,
          "lines": [ln.split(" agent.conversation_loop: ", 1)[1] for ln in lines], "parsers": {},
          "safety": {"egress_blocked": blocked, "exec_blocked": exec_attempts, "probe_reads_allowed": probe_reads,
                     "home": "isolated-temp"}}
for label, path in PARSERS.items():
    spec = importlib.util.spec_from_file_location(f"logcalls_{label}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    parsed = mod.parse_logs([str(log_path)], {SID})
    by_n = {c["n"]: c for c in parsed}
    result["parsers"][label] = {
        "matched": len(parsed), "of": len(lines),
        "per_case": {name: ({k: by_n[n].get(k) for k in ("inp", "hit", "cache_state", "upstream")} if n in by_n else None)
                     for n, name in enumerate(emitted, 1)},
    }
print(json.dumps(result, indent=1))
