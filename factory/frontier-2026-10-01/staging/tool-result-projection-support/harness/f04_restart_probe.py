"""F04 restart probe (T1, $0): does an archived row stay archived across an agent restart when the
history holds signed Claude thinking on the native Messages route?

ProjectionState (the carrier's stickiness) lives in memory on the agent. The fold-in gate declines a
FRESH pass when the request replays signed thinking. After a restart, every row archived earlier
counts as fresh again, so the gate can decline the re-projection and send those rows in full,
under a thinking block that was signed over their stubs.

Scenario (real AIAgent, real read_file, real SessionDB, real Anthropic converter; api.anthropic.com
TLS-intercepted to the repo's AnthropicMessagesServer with test B's signing responder):

* phase A, agent 1, reasoning off (``reasoning_config={"enabled": False}``): 6 read_file turns, the
  responder returns no thinking, so nothing in the history is signed and projection runs;
* phase B, agent 2, reasoning on: the CLI's ``/reasoning`` retires the agent and builds a new one
  over the same in-memory history (``_retire_agent``), so this probe does the same. 4 more turns;
  the responder now returns signed thinking, bound to the prefix as sent (stubs included);
* phase C, 2 more turns, one of:
  - ``restart``: agent 3, history loaded from SessionDB with ``get_resume_conversations`` (what a
    resumed CLI/TUI session or a restarted process sees);
  - ``continue``: agent 2 keeps going (no restart; the control).

Recorded per run: requests per phase, rows archived on the wire, and for the first request of
phase C how many rows that the last phase-B request sent as stubs now go out in full or as the
same stub bytes; the responder's audit of replayed / invalidated thinking blocks, split by phase.

Usage: env -i PATH=/usr/bin:/bin PYTHONHASHSEED=0 F04_SCRATCH=<dir> <venv python> f04_restart_probe.py <repo> <out.json> <arm> <restart|continue>
Guard: os.environ cleared, loopback-only socket.connect / getaddrinfo (evals/provider_fallback/probe_104260.py:11-39).
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO, OUT, ARM, MODE = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
assert MODE in ("restart", "continue"), MODE
SCRATCH = os.environ.get("F04_SCRATCH") or "/tmp"
TURNS_A, TURNS_B, TURNS_C = 6, 4, 2
sys.dont_write_bytecode = True
sandbox = Path(tempfile.mkdtemp(prefix="f04rs-", dir=SCRATCH))
os.environ.clear()
os.environ.update(HOME=str(sandbox / "home"), HERMES_HOME=str(sandbox / "hermes"), TMPDIR=str(sandbox / "tmp"),
                  PATH="/usr/bin:/bin", TZ="UTC", LANG="C.UTF-8", PYTHONHASHSEED="0",
                  PYTHONDONTWRITEBYTECODE="1", HERMES_DISABLE_MODEL_METADATA_FETCH="1")
for d in ("home", "hermes", "tmp", "work", "ca"):
    (sandbox / d).mkdir()
os.chdir(sandbox / "work")
sys.path.insert(0, REPO)

_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_connect, _gai = socket.socket.connect, socket.getaddrinfo
blocked: list = []


def loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in _LOOPBACK:
        blocked.append(f"connect {address!r}")
        raise RuntimeError("probe blocks non-loopback network")
    return _connect(self, address)


def loopback_getaddrinfo(host, *args, **kwargs):
    if host not in _LOOPBACK and host is not None:
        blocked.append(f"getaddrinfo {host!r}")
        raise socket.gaierror("probe blocks non-loopback name resolution")
    return _gai(host, *args, **kwargs)


socket.socket.connect, socket.getaddrinfo = loopback_only, loopback_getaddrinfo

import tests.e2e.core.history.test_tool_result_projection_wire as wire  # noqa: E402
from tests.e2e.core.history._helpers import NO_BACKGROUND_REVIEW, OFFLINE_CONFIG  # noqa: E402
from tests.fakes.providers.anthropic_messages import AnthropicMessagesServer, Thinking, ToolUse  # noqa: E402
from tests.fakes.providers.anthropic_messages import Text as AnthropicText  # noqa: E402
from tests.fakes.providers.oauth_token_server import TLSInterceptProxy, make_test_ca  # noqa: E402

provider = wire.SigningProvider()
bodies: list = []
_orig_call = wire.SigningProvider.__call__


def call_spy(self, record):
    bodies.append(json.loads(json.dumps(record["body"])))
    return _orig_call(self, record)


wire.SigningProvider.__call__ = call_spy
srv = AnthropicMessagesServer(provider).start()
ca = make_test_ca(sandbox / "ca", ["api.anthropic.com"])
proxy = TLSInterceptProxy(srv, ca, ["api.anthropic.com"]).start()  # type: ignore[arg-type]
os.environ.update(HTTPS_PROXY=proxy.url, https_proxy=proxy.url, NO_PROXY="127.0.0.1,localhost",
                  no_proxy="127.0.0.1,localhost", SSL_CERT_FILE=str(ca.ca_pem),
                  ANTHROPIC_API_KEY="sk-ant-api03-e2e-fake-key")
(sandbox / "hermes" / "config.yaml").write_text(
    f"model:\n  provider: anthropic\n  default: {wire.ANTHROPIC_MODEL}\n  context_length: 200000\n"
    "agent:\n  api_max_retries: 1\n  reasoning_effort: medium\n"
    "telemetry:\n  shared_metrics:\n    enabled: false\n"
    + OFFLINE_CONFIG + NO_BACKGROUND_REVIEW + wire.PROJECTION_CONFIG, encoding="utf-8")

from hermes_state import SessionDB  # noqa: E402
from run_agent import AIAgent  # noqa: E402

SID = f"restart-probe-{MODE}"
db = SessionDB(db_path=sandbox / "hermes" / "state.db")
paths = wire.write_corpus(sandbox / "work", TURNS_A + TURNS_B + TURNS_C)


def new_agent(reasoning: dict):
    return AIAgent(provider="anthropic", api_key="sk-ant-api03-e2e-fake-key", model=wire.ANTHROPIC_MODEL,
                   quiet_mode=True, platform="cli", enabled_toolsets=["file"], skip_memory=True,
                   skip_context_files=True, max_iterations=4, session_db=db, session_id=SID,
                   reasoning_config=reasoning)


errors: list = []
phase_start: dict = {}


def run_turns(agent, history, start, stop, thinking):
    for i in range(start, stop):
        if thinking:
            provider.turns += [
                [Thinking(f"plan the read of file {i:02d}", ""), ToolUse("read_file", {"path": str(paths[i])})],
                [Thinking(f"file {i:02d} read", ""), AnthropicText(f"noted file {i:02d}")],
            ]
        else:
            provider.turns += [[ToolUse("read_file", {"path": str(paths[i])})], [AnthropicText(f"noted file {i:02d}")]]
        result = agent.run_conversation(f"read notes_{i:02d}.txt and remember it", conversation_history=history,
                                        task_id=SID)
        history = result.get("messages") or history
        if result.get("final_response") is None:
            errors.append(f"turn {i}: no final response")
    return history


ON = {"enabled": True, "effort": "medium"}
t0 = time.monotonic()
agents = []
try:
    phase_start["A"] = len(bodies)
    a1 = new_agent({"enabled": False})
    agents.append(a1)
    history = run_turns(a1, [], 0, TURNS_A, thinking=False)
    a1.close()
    phase_start["B"] = len(bodies)
    a2 = new_agent(ON)  # /reasoning retires the agent; the surface keeps its in-memory history
    agents.append(a2)
    history = run_turns(a2, history, TURNS_A, TURNS_A + TURNS_B, thinking=True)
    phase_start["C"] = len(bodies)
    if MODE == "restart":
        a2.close()
        resumed = db.get_resume_conversations(SID)[0]
        resumed_signed_rows = sum(1 for m in resumed if m.get("role") == "assistant" and any(
            isinstance(b, dict) and b.get("signature") for b in (m.get("reasoning_details") or [])))
        a3 = new_agent(ON)
        agents.append(a3)
        history = run_turns(a3, resumed, TURNS_A + TURNS_B, TURNS_A + TURNS_B + TURNS_C, thinking=True)
        a3.close()
    else:
        resumed_signed_rows = None
        history = run_turns(a2, history, TURNS_A + TURNS_B, TURNS_A + TURNS_B + TURNS_C, thinking=True)
        a2.close()
finally:
    proxy.stop()
    srv.stop()
    db.close()
wall = time.monotonic() - t0


def tool_results(body):
    out = {}
    for msg in body.get("messages", []):
        for blk in msg.get("content") if isinstance(msg.get("content"), list) else []:
            if isinstance(blk, dict) and blk.get("type") == "tool_result":
                content = blk.get("content")
                out[blk.get("tool_use_id")] = content if isinstance(content, str) else json.dumps(content, sort_keys=True)
    return out


first_seen, stub_of, projected_at, passes, unstable = {}, {}, {}, {}, []
for i, body in enumerate(bodies):
    for tid, content in tool_results(body).items():
        original = first_seen.setdefault(tid, content)
        if tid in projected_at:
            if content != stub_of[tid]:
                unstable.append({"request": i, "tool_use_id": tid, "archived_at": projected_at[tid],
                                 "back_to_full_bytes": content == first_seen[tid]})
        elif content != original and len(content) < len(original):
            projected_at[tid], stub_of[tid] = i, content
            passes.setdefault(i, []).append(tid)

c0 = phase_start["C"]
last_b, first_c = tool_results(bodies[c0 - 1]), tool_results(bodies[c0])
stubbed_before = [t for t, c in last_b.items() if c != first_seen[t]]
first_c_full = [t for t in stubbed_before if first_c.get(t) == first_seen[t]]
first_c_same_stub = [t for t in stubbed_before if first_c.get(t) == last_b[t]]
first_c_new_stubs = [t for t, c in first_c.items() if c != first_seen[t] and t not in stubbed_before]


def phase_of(n):  # SigningProvider numbers requests from 1
    i = n - 1
    return "C" if i >= phase_start["C"] else "B" if i >= phase_start["B"] else "A"


inv_by_phase = {"A": 0, "B": 0, "C": 0}
inv_first_c = 0
for line in provider.invalidated:
    n = int(line.split("request ", 1)[1].split(":", 1)[0])
    inv_by_phase[phase_of(n)] += 1
    inv_first_c += (n - 1) == c0


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


receipt = {
    "arm": ARM, "mode": MODE, "turns": {"A_reasoning_off": TURNS_A, "B_reasoning_on": TURNS_B, f"C_{MODE}": TURNS_C},
    "repo_head": git("rev-parse", "HEAD"), "repo_tree": git("rev-parse", "HEAD^{tree}"),
    "dirty_files": git("status", "--porcelain").splitlines(),
    "projection_module_blob": git("hash-object", "agent/tool_result_projection.py") if (Path(REPO) / "agent/tool_result_projection.py").exists() else None,
    "agent_api_modes": [getattr(a, "api_mode", None) for a in agents],
    "requests": len(bodies), "phase_start_request_index": phase_start, "errors": errors,
    "proxy_refused": list(proxy.refused),
    "resumed_assistant_rows_with_signed_reasoning_details": resumed_signed_rows,
    "tool_results": len(first_seen), "rows_archived": len(projected_at), "projection_passes": len(passes),
    "pass_request_indices": sorted(passes),
    "rows_archived_before_phase_C": sum(1 for i in projected_at.values() if i < c0),
    "first_request_of_phase_C": {
        "request_index": c0,
        "rows_stubbed_on_last_phase_B_request": len(stubbed_before),
        "of_those_sent_in_full": len(first_c_full),
        "of_those_same_stub_bytes": len(first_c_same_stub),
        "rows_newly_stubbed": len(first_c_new_stubs),
        "invalidated_thinking_blocks": inv_first_c,
    },
    "archived_rows_changed_later": unstable,
    "replayed_thinking_blocks_audited": provider.replayed,
    "invalidated_thinking_blocks": len(provider.invalidated),
    "invalidated_by_phase": inv_by_phase,
    "invalidated": provider.invalidated,
    "sum_request_chars": sum(len(json.dumps(b.get("messages", []))) for b in bodies),
    "egress_blocked": blocked, "wall_s": round(wall, 2), "python": sys.version.split()[0],
}
Path(OUT).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({k: receipt[k] for k in ("arm", "mode", "requests", "errors", "rows_archived", "pass_request_indices",
                                          "first_request_of_phase_C", "invalidated_by_phase", "egress_blocked")}, indent=1))
