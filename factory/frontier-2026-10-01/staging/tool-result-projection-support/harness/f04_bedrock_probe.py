"""F04 Bedrock Converse probe (T1, $0): the preserved-thinking scenario of test B, on the
``bedrock_converse`` wire instead of native Anthropic Messages.

A real ``AIAgent`` (provider ``bedrock``, a Claude model id) with the real ``read_file`` tool and the
real request assembly talks to the repo's loopback ``FakeBedrock`` through the real boto3 client
(botocore's documented ``AWS_ENDPOINT_URL_BEDROCK_RUNTIME`` override; SigV4 is re-verified by the
fake). The responder signs each ``reasoningContent.reasoningText`` block over its conversation prefix
(system, the name-sorted tool set, every earlier message, with reasoning blocks and cachePoint markers
excluded, mirroring test B's digest) and audits every replayed block against the prefix it was signed
over. It also reads projection passes off the wire (a toolResult that shrinks after it was first sent).

Usage: env -i PATH=/usr/bin:/bin PYTHONHASHSEED=0 <venv python> f04_bedrock_probe.py <repo> <out.json> <arm>

Same isolation as f04_probe.py: cleared environment, fresh HOME/HERMES_HOME, loopback-only
socket.connect + getaddrinfo guard (blocked attempts recorded).
"""

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO, OUT, ARM = sys.argv[1], sys.argv[2], sys.argv[3]
SCRATCH = os.environ.get("F04_SCRATCH") or "/tmp"
sys.dont_write_bytecode = True
sandbox = tempfile.mkdtemp(prefix="f04b-", dir=SCRATCH)
os.environ.clear()
os.environ.update(
    HOME=sandbox + "/home",
    HERMES_HOME=sandbox + "/hermes",
    TMPDIR=sandbox + "/tmp",
    PATH="/usr/bin:/bin",
    TZ="UTC",
    LANG="C.UTF-8",
    PYTHONHASHSEED="0",
    PYTHONDONTWRITEBYTECODE="1",
    HERMES_DISABLE_MODEL_METADATA_FETCH="1",
)
for d in ("home", "hermes", "tmp", "work"):
    Path(sandbox, d).mkdir()
os.chdir(REPO)
sys.path.insert(0, REPO)

_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_original_connect = socket.socket.connect
_original_getaddrinfo = socket.getaddrinfo
blocked: list = []


def loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in _LOOPBACK:
        blocked.append(f"connect {address!r}")
        raise RuntimeError("F04 probe blocks non-loopback network")
    return _original_connect(self, address)


def loopback_getaddrinfo(host, *args, **kwargs):
    if host not in _LOOPBACK and host is not None:
        blocked.append(f"getaddrinfo {host!r}")
        raise socket.gaierror("F04 probe blocks non-loopback name resolution")
    return _original_getaddrinfo(host, *args, **kwargs)


socket.socket.connect = loopback_only
socket.getaddrinfo = loopback_getaddrinfo

import tests.e2e.core.history.test_tool_result_projection_wire as wire  # noqa: E402
from tests.e2e.core.history._helpers import NO_BACKGROUND_REVIEW, OFFLINE_CONFIG, canon  # noqa: E402
from tests.fakes.providers.bedrock_converse import (  # noqa: E402
    ACCESS_KEY, REGION, SECRET_KEY, FakeBedrock, Reasoning, Text, ToolUse, Turn,
)

MODEL = "anthropic.claude-opus-5-5"  # Claude on Bedrock: signed reasoning bound to its prefix


def converse_prefix_digest(body, upto):
    messages = []
    for msg in (body.get("messages") or [])[:upto]:
        content = [b for b in msg.get("content") or []
                   if isinstance(b, dict) and "reasoningContent" not in b and "cachePoint" not in b]
        messages.append({"role": msg.get("role"), "content": content})
    tools = [t for t in ((body.get("toolConfig") or {}).get("tools") or []) if "cachePoint" not in t]
    tools = sorted(tools, key=lambda t: str((t.get("toolSpec") or {}).get("name")))
    system = [b for b in body.get("system") or [] if "cachePoint" not in b]
    return hashlib.sha256(canon([system, tools, messages]).encode()).hexdigest()


class SigningConverse:
    def __init__(self):
        self.turns: list = []
        self.bound: dict = {}
        self.replayed = 0
        self.invalidated: list = []
        self.n = 0
        self.bodies: list = []

    def __call__(self, record):
        body = record["body"]
        self.n += 1
        self.bodies.append(json.loads(json.dumps(body.get("messages") or [])))
        for m, msg in enumerate(body.get("messages") or []):
            for b in msg.get("content") or []:
                rt = (b.get("reasoningContent") or {}).get("reasoningText") if isinstance(b, dict) else None
                if rt:
                    self.replayed += 1
                    want = self.bound.get(rt.get("signature", ""))
                    if want != converse_prefix_digest(body, m):
                        self.invalidated.append(f"request {self.n}: messages[{m}] reasoning block replayed over "
                                                f"a rewritten prefix (signed: {want is not None})")
        blocks = self.turns.pop(0) if self.turns else [Text("ok")]
        digest = converse_prefix_digest(body, len(body.get("messages") or []))
        out = []
        for b in blocks:
            if isinstance(b, Reasoning):
                sig = f"sig-{self.n}-{digest[:32]}"
                self.bound[sig] = digest
                b = Reasoning(b.text, sig)
            out.append(b)
        return Turn(out)


def tool_results(messages):
    rows = {}
    for msg in messages:
        for b in msg.get("content") or []:
            tr = b.get("toolResult") if isinstance(b, dict) else None
            if tr:
                rows[tr.get("toolUseId")] = canon(tr.get("content"))
    return rows


def passes_from(bodies):
    first, projected, passes = {}, {}, {}
    for i, messages in enumerate(bodies):
        for tid, content in tool_results(messages).items():
            original = first.setdefault(tid, content)
            if tid not in projected and content != original and len(content) < len(original):
                projected[tid] = i
                passes.setdefault(i, []).append(tid)
    return {"tool_rows": len(first), "rows_projected": len(projected),
            "pass_request_indices": sorted(passes), "passes": {str(k): v for k, v in sorted(passes.items())}}


hermes_home = Path(os.environ["HERMES_HOME"])
(hermes_home / "config.yaml").write_text(
    "model:\n  provider: bedrock\n"
    f"  default: {MODEL}\n  context_length: 200000\n"
    "agent:\n  api_max_retries: 1\n  reasoning_effort: medium\n"
    "telemetry:\n  shared_metrics:\n    enabled: false\n"
    + OFFLINE_CONFIG + NO_BACKGROUND_REVIEW + wire.PROJECTION_CONFIG, encoding="utf-8")

provider = SigningConverse()
outcome, error = "passed", ""
t0 = time.monotonic()
with FakeBedrock(provider) as fake:
    os.environ.update(AWS_ENDPOINT_URL_BEDROCK_RUNTIME=fake.endpoint, AWS_ACCESS_KEY_ID=ACCESS_KEY,
                      AWS_SECRET_ACCESS_KEY=SECRET_KEY, AWS_REGION=REGION, AWS_DEFAULT_REGION=REGION,
                      AWS_EC2_METADATA_DISABLED="true")
    workdir = Path(sandbox, "work")
    os.chdir(workdir)
    paths = wire.write_corpus(workdir, wire.TURNS)
    from run_agent import AIAgent

    agent = AIAgent(provider="bedrock", base_url=f"https://bedrock-runtime.{REGION}.amazonaws.com",
                    model=MODEL, quiet_mode=True, platform="cli", enabled_toolsets=["file"],
                    skip_memory=True, skip_context_files=True, max_iterations=4)
    api_mode = getattr(agent, "api_mode", None)
    history: list = []
    try:
        for i, path in enumerate(paths):
            provider.turns += [
                [Reasoning(f"plan the read of file {i:02d}"), ToolUse("read_file", {"path": str(path)})],
                [Reasoning(f"file {i:02d} read"), Text(f"noted file {i:02d}")],
            ]
            result = agent.run_conversation(f"read notes_{i:02d}.txt and remember it",
                                            conversation_history=history, task_id="projection-thinking-bedrock")
            history = result.get("messages") or history
            if result.get("final_response") is None:
                outcome, error = "failed", f"turn {i}: no final_response: {str(result)[:300]}"
                break
    except Exception as exc:  # noqa: BLE001 - recorded, not hidden
        outcome, error = "error", f"{type(exc).__name__}: {exc}"[:600]
    finally:
        agent.close()
    rejected = [r.get("rejected") for r in fake.snapshot() if r.get("rejected")]
wall = time.monotonic() - t0
if outcome == "passed" and provider.invalidated:
    outcome, error = "failed", "a request replayed signed reasoning over a rewritten prefix"
if outcome == "passed" and not provider.replayed:
    outcome, error = "vacuous", "no signed reasoning block was replayed"


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


receipt = {
    "arm": ARM,
    "repo_head": git("rev-parse", "HEAD"),
    "repo_tree": git("rev-parse", "HEAD^{tree}"),
    "dirty_files": git("status", "--porcelain").splitlines(),
    "route": {"provider": "bedrock", "api_mode": api_mode, "model": MODEL},
    "outcome": outcome,
    "message": error,
    "requests": provider.n,
    "replayed_reasoning_blocks": provider.replayed,
    "invalidated_reasoning_blocks": len(provider.invalidated),
    "invalidated": provider.invalidated,
    "fake_rejections": rejected,
    "projection": passes_from(provider.bodies),
    "egress_blocked": blocked,
    "wall_s": round(wall, 2),
    "python": sys.version.split()[0],
}
Path(OUT).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({k: receipt[k] for k in ("arm", "route", "outcome", "message", "requests",
                                          "replayed_reasoning_blocks", "invalidated_reasoning_blocks",
                                          "projection", "fake_rejections", "egress_blocked")}, indent=1))
