"""F04 third-party probe (T1, $0): test B's scenario on a third-party Anthropic-compatible endpoint.

Same 12-turn read_file session, projection config and signing responder as
``test_projection_never_invalidates_replayed_preserved_thinking``, but the agent runs the MiniMax
provider at its production base URL ``https://api.minimax.io/anthropic``. ``api.minimax.io`` is
TLS-intercepted to the repo's ``AnthropicMessagesServer`` (the test's own pattern for
api.anthropic.com), so only the vendor HTTP boundary is faked. The responder still returns signed
thinking blocks, so Hermes stores signed copies on every assistant row; the Messages converter
strips all thinking for this endpoint (``_manage_thinking_signatures``), so nothing bound is sent.

Recorded per run: requests, thinking blocks on the wire, invalidated replays (the responder's
audit), projection passes read off the Anthropic wire (a ``tool_result`` whose bytes shrink from
what it was first sent with), unstable archived rows, and the sum of request chars.

Usage: env -i PATH=/usr/bin:/bin PYTHONHASHSEED=0 F04_SCRATCH=<dir> <venv python> f04_thirdparty_probe.py <repo> <out.json> <arm>
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

REPO, OUT, ARM = sys.argv[1], sys.argv[2], sys.argv[3]
SCRATCH = os.environ.get("F04_SCRATCH") or "/tmp"
VENDOR_HOST, BASE_URL, MODEL = "api.minimax.io", "https://api.minimax.io/anthropic", "MiniMax-M2.7"
sys.dont_write_bytecode = True
sandbox = Path(tempfile.mkdtemp(prefix="f04tp-", dir=SCRATCH))
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
ca = make_test_ca(sandbox / "ca", [VENDOR_HOST])
proxy = TLSInterceptProxy(srv, ca, [VENDOR_HOST]).start()  # type: ignore[arg-type]
os.environ.update(HTTPS_PROXY=proxy.url, https_proxy=proxy.url, NO_PROXY="127.0.0.1,localhost",
                  no_proxy="127.0.0.1,localhost", SSL_CERT_FILE=str(ca.ca_pem), MINIMAX_API_KEY="fake-minimax-key")
(sandbox / "hermes" / "config.yaml").write_text(
    f"model:\n  provider: minimax\n  default: {MODEL}\n  base_url: {BASE_URL}\n  context_length: 200000\n"
    "agent:\n  api_max_retries: 1\n  reasoning_effort: medium\n"
    "telemetry:\n  shared_metrics:\n    enabled: false\n"
    + OFFLINE_CONFIG + NO_BACKGROUND_REVIEW + wire.PROJECTION_CONFIG, encoding="utf-8")

from run_agent import AIAgent  # noqa: E402

paths = wire.write_corpus(sandbox / "work", wire.TURNS)
agent = AIAgent(provider="minimax", base_url=BASE_URL, api_key="fake-minimax-key", model=MODEL, quiet_mode=True,
                platform="cli", enabled_toolsets=["file"], skip_memory=True, skip_context_files=True, max_iterations=4)
history: list = []
errors: list = []
t0 = time.monotonic()
try:
    for i, path in enumerate(paths):
        provider.turns += [
            [Thinking(f"plan the read of file {i:02d}", ""), ToolUse("read_file", {"path": str(path)})],
            [Thinking(f"file {i:02d} read", ""), AnthropicText(f"noted file {i:02d}")],
        ]
        result = agent.run_conversation(f"read notes_{i:02d}.txt and remember it", conversation_history=history,
                                        task_id="projection-thinking-thirdparty")
        history = result.get("messages") or history
        if result.get("final_response") is None:
            errors.append(f"turn {i}: no final response")
finally:
    agent.close()
    proxy.stop()
    srv.stop()
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
thinking_on_wire = signed_on_wire = 0
for i, body in enumerate(bodies):
    for msg in body.get("messages", []):
        for blk in msg.get("content") if isinstance(msg.get("content"), list) else []:
            if isinstance(blk, dict) and blk.get("type") in ("thinking", "redacted_thinking"):
                thinking_on_wire += 1
                signed_on_wire += bool(blk.get("signature") or blk.get("data"))
    for tid, content in tool_results(body).items():
        original = first_seen.setdefault(tid, content)
        if tid in projected_at:
            if content != stub_of[tid]:
                unstable.append(f"request {i}: {tid}")
        elif content != original and len(content) < len(original):
            projected_at[tid], stub_of[tid] = i, content
            passes.setdefault(i, []).append(tid)


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


receipt = {
    "arm": ARM, "endpoint": BASE_URL, "provider": "minimax", "model": MODEL,
    "repo_head": git("rev-parse", "HEAD"), "repo_tree": git("rev-parse", "HEAD^{tree}"),
    "dirty_files": git("status", "--porcelain").splitlines(),
    "agent_api_mode": getattr(agent, "api_mode", None),
    "agent_anthropic_base_url": getattr(agent, "_anthropic_base_url", None),
    "requests": len(bodies), "errors": errors, "proxy_refused": list(proxy.refused),
    "stored_assistant_rows_with_signed_copies": sum(
        1 for m in history if m.get("role") == "assistant"
        and any(isinstance(b, dict) and b.get("signature") for k in ("reasoning_details", "anthropic_content_blocks")
                for b in (m.get(k) or []))),
    "thinking_blocks_on_wire": thinking_on_wire, "signed_thinking_blocks_on_wire": signed_on_wire,
    "replayed_thinking_blocks_audited": provider.replayed, "invalidated_thinking_blocks": len(provider.invalidated),
    "tool_results": len(first_seen), "rows_archived": len(projected_at), "projection_passes": len(passes),
    "pass_request_indices": sorted(passes), "unstable_archived_rows": len(unstable),
    "sum_request_chars": sum(len(json.dumps(b.get("messages", []))) for b in bodies),
    "egress_blocked": blocked, "wall_s": round(wall, 2), "python": sys.version.split()[0],
}
Path(OUT).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({k: receipt[k] for k in ("arm", "agent_api_mode", "requests", "errors", "thinking_blocks_on_wire",
                                          "invalidated_thinking_blocks", "projection_passes", "pass_request_indices",
                                          "sum_request_chars", "egress_blocked")}, indent=1))
