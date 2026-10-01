"""E37 synthetic arm (T1, $0): one tool-heavy session replayed through config arms, real AIAgent +
SessionDB + read_file against the recording loopback provider, with provider usage derived from
the request size so the prune / compaction gates see realistic numbers.

Arms (config.yaml only): prune-off (shipped default), prune-on (proactive_prune_tokens: 48000, the
value the config comment suggests), projection (tool_result_projection: auto, defaults), and
projection-cached (same, with the provider reporting cached input so the route is classified as
prefix-caching). Wire sizes and prefix breaks are OBSERVED on the loopback wire; token counts are
chars/4 and every billing / cache figure is MODELED (perfect prefix cache, no TTL expiry).

Usage: env -i PATH=/usr/bin:/bin PYTHONHASHSEED=0 E37_SCRATCH=<dir> <venv python> e37_synthetic.py <repo> <out.json> <arm> [turns]
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
TURNS = int(sys.argv[4]) if len(sys.argv) > 4 else 20
SCRATCH = os.environ.get("E37_SCRATCH") or "/tmp"
sys.dont_write_bytecode = True
sandbox = Path(tempfile.mkdtemp(prefix=f"e37-{ARM}-", dir=SCRATCH))
os.environ.clear()
os.environ.update(HOME=str(sandbox / "home"), HERMES_HOME=str(sandbox / "hermes"), TMPDIR=str(sandbox / "tmp"),
                  PATH="/usr/bin:/bin", TZ="UTC", LANG="C.UTF-8", PYTHONHASHSEED="0",
                  PYTHONDONTWRITEBYTECODE="1", HERMES_DISABLE_MODEL_METADATA_FETCH="1",
                  OPENAI_API_KEY="sk-fake-e2e")
for d in ("home", "hermes", "tmp", "work"):
    (sandbox / d).mkdir()
os.chdir(sandbox / "work")
sys.path.insert(0, REPO)

_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_connect, _gai = socket.socket.connect, socket.getaddrinfo
blocked: list[str] = []


def _guard_connect(self, address):
    if isinstance(address, tuple) and address[0] not in _LOOPBACK:
        blocked.append(f"connect {address!r}")
        raise RuntimeError("E37 probe blocks non-loopback network")
    return _connect(self, address)


def _guard_gai(host, *a, **k):
    if host is not None and host not in _LOOPBACK:
        blocked.append(f"getaddrinfo {host!r}")
        raise socket.gaierror("E37 probe blocks non-loopback name resolution")
    return _gai(host, *a, **k)


socket.socket.connect, socket.getaddrinfo = _guard_connect, _guard_gai

ARMS = {
    "prune-off": "",
    "prune-on": "compression:\n  proactive_prune_tokens: 48000\n",
    "projection": "compression:\n  tool_result_projection: auto\n",
    "projection-cached": "compression:\n  tool_result_projection: auto\n",
}
CACHED = ARM == "projection-cached"

from tests.e2e.core.history._helpers import (  # noqa: E402
    NO_BACKGROUND_REVIEW, OFFLINE_CONFIG, InProcessSession, Script, canon, prefix_breaks, views,
)
from tests.fakes.fake_llm_provider import FakeLLMServer, Text, ToolCall, write_hermes_home  # noqa: E402
from tests.e2e.core.history.test_tool_result_projection_wire import (  # noqa: E402
    projection_ledger, write_corpus,
)


def prompt_tokens(body):
    return len(json.dumps(body.get("messages", []))) // 4 + len(json.dumps(body.get("tools", []))) // 4


script = Script()
paths = write_corpus(sandbox / "work", TURNS)
t0 = time.monotonic()
errors: list[str] = []
with FakeLLMServer(script, prompt_tokens_fn=prompt_tokens) as srv:
    write_hermes_home(Path(os.environ["HERMES_HOME"]), srv.base_url,
                      extra_config=OFFLINE_CONFIG + NO_BACKGROUND_REVIEW + ARMS[ARM])
    session = InProcessSession(srv.base_url, Path(os.environ["HERMES_HOME"]), f"e37-{ARM}")
    try:
        for i in range(TURNS):
            script.actions += [ToolCall("read_file", {"path": str(paths[i])}),
                               Text(f"noted file {i:02d}", cached_tokens=1 if CACHED else 0)]
            result = session.turn(f"read notes_{i:02d}.txt and remember it")
            if result.get("final_response") is None:
                errors.append(f"turn {i}: {str(result)[:300]}")
        sid = session.sid
    finally:
        session.close()
    main = srv.main_requests()
    aux = srv.aux_requests()

ledger = projection_ledger(main)
breaks = prefix_breaks(main, tools=False)
rows, prev = [], None
for r in main:
    msgs = r["messages"]
    sizes = [len(canon(m)) for m in msgs]
    k = 0
    if prev is not None:
        while k < min(len(prev), len(msgs)) and canon(prev[k]) == canon(msgs[k]):
            k += 1
    rows.append({"total_chars": sum(sizes), "common_prefix_chars": sum(sizes[:k])})
    prev = msgs
total = sum(x["total_chars"] for x in rows)
common = sum(x["common_prefix_chars"] for x in rows)
model_view = views(Path(os.environ["HERMES_HOME"]), sid)[0]


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


receipt = {
    "arm": ARM, "turns": TURNS, "repo_head": git("rev-parse", "HEAD"), "repo_tree": git("rev-parse", "HEAD^{tree}"),
    "dirty_files": git("status", "--porcelain").splitlines(),
    "config_overlay": ARMS[ARM], "provider_reports_cached_input": CACHED,
    "observed": {
        "label": "OBSERVED (loopback wire)",
        "main_requests": len(main), "aux_requests": len(aux),
        "prefix_breaks": [i for i, _ in breaks], "prefix_break_reasons": [w[:140] for _, w in breaks],
        "projection_passes": {str(i): v for i, v in sorted(ledger["passes"].items())},
        "rows_projected": len(ledger["projected_at"]), "unstable_archived_rows": ledger["unstable"],
        "wire_chars_per_request": [x["total_chars"] for x in rows],
        "last_request_chars": rows[-1]["total_chars"], "max_request_chars": max(x["total_chars"] for x in rows),
        "sum_request_chars": total,
        "durable_model_view_tool_rows_chars": sum(len(m.get("content") or "") for m in model_view if m.get("role") == "tool"),
        "turn_errors": errors,
    },
    "modeled": {
        "label": "MODELED (chars/4 tokens; perfect prefix cache; write 1.25x, read 0.10x)",
        "cache_read_ratio": round(common / total, 4),
        "billed_input_tokens_no_cache": total // 4,
        "billed_input_token_units_cached": round((1.25 * (total - common) + 0.10 * common) / 4),
        "reprefill_tokens_after_breaks": sum(x["total_chars"] - x["common_prefix_chars"] for x in rows[1:]) // 4,
    },
    "egress_blocked": blocked, "wall_s": round(time.monotonic() - t0, 2), "python": sys.version.split()[0],
}
Path(OUT).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({"arm": ARM, "main": len(main), "aux": len(aux), "breaks": receipt["observed"]["prefix_breaks"],
                  "passes": list(receipt["observed"]["projection_passes"]), "sum_chars": total,
                  "last": rows[-1]["total_chars"], **{k: v for k, v in receipt["modeled"].items() if k != "label"},
                  "errors": errors, "egress": blocked}, indent=None))
