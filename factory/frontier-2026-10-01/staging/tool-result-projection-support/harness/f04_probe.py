"""F04 probe (T1, $0): run tests/e2e/core/history/test_tool_result_projection_wire.py in-process
under a loopback-only socket guard and a cleared environment, and record what the request stream
showed per scenario (projection passes, reclaim per pass, prefix breaks, replayed / invalidated
preserved-thinking blocks).

Usage: env -i PATH=/usr/bin:/bin PYTHONHASHSEED=0 <venv python> f04_probe.py <repo> <out.json> <arm>

Guard pattern lifted from evals/provider_fallback/probe_104260.py:11-39 (os.environ cleared and
replaced, socket.connect restricted to loopback, blocked attempts recorded).
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
ENFORCE = len(sys.argv) > 4 and sys.argv[4] == "enforce"  # emulate an enforced account: 400 on a replayed block over a rewritten prefix
SCRATCH = os.environ.get("F04_SCRATCH") or "/tmp"
sys.dont_write_bytecode = True
sandbox = tempfile.mkdtemp(prefix="f04-", dir=SCRATCH)
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
for d in ("home", "hermes", "tmp"):
    Path(sandbox, d).mkdir()
os.chdir(REPO)
sys.path.insert(0, REPO)

_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_original_connect = socket.socket.connect
_original_getaddrinfo = socket.getaddrinfo
blocked: list[str] = []


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

import pytest  # noqa: E402

import tests.e2e.core.history.test_tool_result_projection_wire as wire  # noqa: E402

captured: dict = {"ledgers": [], "breaks": [], "providers": [], "anthropic_bodies": []}


def wire_model(message_lists):
    """MODELED cache economics from the OBSERVED request stream: message-granular longest common
    prefix with the previous request (a perfect prefix cache that never expires), chars/4 tokens,
    Anthropic-style multipliers (cache write 1.25x, cache read 0.10x). System prompt and tools are
    identical across arms and excluded; ``cache_control`` markers are ignored (moving a marker does
    not change the cached bytes)."""
    from tests.e2e.core.history._helpers import canon
    rows, prev = [], None
    for msgs in message_lists:
        msgs = wire._drop_cache_control(msgs)
        sizes = [len(canon(m)) for m in msgs]
        k = 0
        if prev is not None:
            while k < min(len(prev), len(msgs)) and canon(prev[k]) == canon(msgs[k]):
                k += 1
        common = sum(sizes[:k])
        rows.append({"total_chars": sum(sizes), "common_prefix_chars": common})
        prev = msgs
    total = sum(r["total_chars"] for r in rows)
    common = sum(r["common_prefix_chars"] for r in rows)
    return {
        "label": "MODELED",
        "requests": len(rows),
        "sum_input_chars": total,
        "last_request_chars": rows[-1]["total_chars"] if rows else 0,
        "cache_read_ratio_perfect_prefix_cache": round(common / total, 4) if total else None,
        "billed_input_tokens_no_cache": total // 4,
        "billed_input_token_units_cached_1.25w_0.10r": round((1.25 * (total - common) + 0.10 * common) / 4),
        "reprefill_chars_after_breaks": sum(r["total_chars"] - r["common_prefix_chars"] for r in rows[1:]),
        "per_request": rows,
    }
_orig_ledger, _orig_breaks, _orig_init = wire.projection_ledger, wire.prefix_breaks, wire.SigningProvider.__init__


def ledger_spy(requests):
    out = _orig_ledger(requests)
    captured["ledgers"].append({
        "requests": len(requests),
        "tool_rows": len(out["first_seen"]),
        "rows_projected": len(out["projected_at"]),
        "passes": {str(i): rows for i, rows in sorted(out["passes"].items())},
        "reclaim_tokens_per_pass": {str(i): t for i, t in sorted(out["reclaim_tokens"].items())},
        "unstable": out["unstable"],
        "wire_chars_per_request": [len(json.dumps(r["messages"])) for r in requests],
        "modeled": wire_model([r["messages"] for r in requests]),
    })
    return out


def breaks_spy(requests, **kw):
    out = _orig_breaks(requests, **kw)
    captured["breaks"].append({"requests": len(requests), "break_indices": [i for i, _ in out],
                               "reasons": [why[:160] for _, why in out]})
    return out


def init_spy(self):
    _orig_init(self)
    captured["providers"].append(self)


_orig_call = wire.SigningProvider.__call__


ENFORCED_MESSAGE = ("messages.{m}.content.0: Invalid `signature` in `thinking` block. The block is bound to a "
                    "different conversation. Remove the block, or set `thinking.block_binding.prefix_mismatch_behavior` "
                    "to \"drop_block\".")
captured["rejected_400"] = 0


def call_spy(self, record):
    captured["anthropic_bodies"].append(json.loads(json.dumps(record["body"].get("messages", []))))
    before = len(self.invalidated)
    reply = _orig_call(self, record)
    if ENFORCE and len(self.invalidated) > before:
        from tests.fakes.providers.anthropic_messages import ApiError
        captured["rejected_400"] += 1
        m = self.invalidated[before].split("messages[", 1)[1].split("]", 1)[0]
        return ApiError(400, "invalid_request_error", ENFORCED_MESSAGE.format(m=m))
    return reply


wire.SigningProvider.__call__ = call_spy


wire.projection_ledger, wire.prefix_breaks, wire.SigningProvider.__init__ = ledger_spy, breaks_spy, init_spy


class Outcomes:
    def __init__(self):
        self.results: dict = {}

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            msg = str(report.longrepr).splitlines()[-1][:600] if report.longrepr else ""
            for line in str(report.longrepr or "").splitlines():
                if line.startswith("E       AssertionError") or line.startswith("E   AssertionError"):
                    msg = line[:600]
                    break
            self.results[report.nodeid.split("::")[-1]] = {"outcome": report.outcome, "message": msg}


plugin = Outcomes()
t0 = time.monotonic()
rc = pytest.main([str(Path(wire.__file__)), "-q", "-p", "no:cacheprovider", "-p", "no:randomly"], plugins=[plugin])
wall = time.monotonic() - t0


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


receipt = {
    "arm": ARM,
    "repo_head": git("rev-parse", "HEAD"),
    "repo_tree": git("rev-parse", "HEAD^{tree}"),
    "dirty_files": git("status", "--porcelain").splitlines(),
    "test_file_blob": git("hash-object", "tests/e2e/core/history/test_tool_result_projection_wire.py"),
    "pytest_rc": int(rc),
    "outcomes": plugin.results,
    "ledgers": captured["ledgers"],
    "prefix_breaks": captured["breaks"],
    "preserved_thinking": [{"requests": p.n, "replayed_thinking_blocks": p.replayed,
                            "invalidated_thinking_blocks": len(p.invalidated), "invalidated": p.invalidated}
                           for p in captured["providers"]],
    "enforced_account_emulation": ENFORCE,
    "rejected_400_thinking_binding": captured["rejected_400"],
    "anthropic_route_modeled": wire_model(captured["anthropic_bodies"]) if captured["anthropic_bodies"] else None,
    "egress_blocked": blocked,
    "wall_s": round(wall, 2),
    "python": sys.version.split()[0],
}
Path(OUT).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({k: receipt[k] for k in ("arm", "repo_head", "pytest_rc", "outcomes", "egress_blocked")}, indent=2))
