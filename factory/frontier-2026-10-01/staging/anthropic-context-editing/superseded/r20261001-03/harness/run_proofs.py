"""Run every $0 proof for staging/anthropic-context-editing on one worktree, base then head.

RED (contract test copied onto base), adjacent (base), guards (base), F09 (base); then GREEN x3,
adjacent, guards, F09 and per-hunk sabotage on the head. Writes raw outputs plus run_meta.json
(wall and child CPU seconds per step) into --raw. Nothing absolute is written: the worktree path in
the guard scripts' own output is replaced with "<worktree>".

Usage:
  HERMES_PYTHON=<venv python> XF_TESTHOME=<isolated test home> \
    python run_proofs.py --worktree <checkout> --base <sha> --head <sha> --raw <dir>
"""
import argparse
import json
import os
import re
import resource
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST = "tests/agent/test_anthropic_context_editing.py"
ADJACENT = [
    "tests/agent/test_anthropic_adapter.py", "tests/hermes_cli/test_fast_command.py", "tests/agent/test_fast_mode_auto.py",
    "tests/agent/test_native_compaction.py", "tests/agent/test_nous_portal_anthropic_wire.py", "tests/gateway/test_agent_cache.py",
    "tests/tui_gateway/test_compression_config_hot_reload.py", "tests/hermes_cli/test_config_edit_seed.py",
    "tests/hermes_cli/test_config_unversioned_migration.py", "tests/agent/test_413_compression.py",
    "tests/agent/transports/test_transport.py", "tests/agent/test_anthropic_stream_fallbacks.py",
    "tests/agent/test_codex_token_expired_replay_recovery.py", "tests/agent/test_error_classifier.py",
    "tests/e2e/core/providers/test_anthropic_oracle.py",
]
GUARDS = [("replay_gates", "evals/token_accounting/replay_gates.py"),
          ("ab_checkpoint_preflight", "evals/native_compaction/ab_checkpoint_preflight.py")]

ap = argparse.ArgumentParser()
ap.add_argument("--worktree", required=True)
ap.add_argument("--base", required=True)
ap.add_argument("--head", required=True)
ap.add_argument("--raw", required=True)
ARGS = ap.parse_args()
W = Path(ARGS.worktree).resolve()
RAW = Path(ARGS.raw).resolve()
RAW.mkdir(parents=True, exist_ok=True)
PY = os.environ["HERMES_PYTHON"]
HOME = Path(os.environ["XF_TESTHOME"])
META: list[dict] = []


def step(name, fn):
    t0, c0 = time.monotonic(), resource.getrusage(resource.RUSAGE_CHILDREN)
    result = fn()
    c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    META.append({"step": name, "wall_s": round(time.monotonic() - t0, 1),
                 "cpu_core_s": round((c1.ru_utime - c0.ru_utime) + (c1.ru_stime - c0.ru_stime), 1)})
    print(json.dumps(META[-1]), flush=True)
    return result


def git(*args):
    return subprocess.run(["git", *args], cwd=W, check=True, capture_output=True, text=True).stdout


def pytest(files):
    env = {**os.environ, "HOME": str(HOME), "HERMES_HOME": str(HOME / ".hermes"), "HERMES_PYTHON": PY}
    proc = subprocess.run(["bash", "scripts/run_tests.sh", "-j", "2", *files, "-q"], cwd=W, env=env,
                          capture_output=True, text=True, timeout=1800)
    return proc.stdout + proc.stderr


def summary(out):
    return [ln.strip() for ln in out.splitlines() if ln.strip().startswith("=== Summary:")]


def guard(name, script, arm):
    env = {"PATH": "/usr/bin:/bin", "HOME": str(HOME), "HERMES_HOME": str(HOME / ".hermes"),
           "HERMES_DISABLE_LAZY_INSTALLS": "1", "HERMES_DISABLE_MODEL_METADATA_FETCH": "1", "TZ": "UTC", "LANG": "C.UTF-8"}
    out = RAW / f"{name}_{arm}.json"
    subprocess.run([PY, script, "--out", str(out)], cwd=W, env=env, check=True, capture_output=True, text=True, timeout=900)
    out.write_text(out.read_text(encoding="utf-8").replace(str(W), "<worktree>"), encoding="utf-8")


def f09(arm):
    subprocess.run([PY, str(HERE / "f09_gate_probe.py"), "--repo", str(W), "--arm", arm, "--out", str(RAW / f"f09_{arm}.json")],
                   check=True, capture_output=True, text=True, timeout=900)


def main() -> int:
    (HOME / ".hermes").mkdir(parents=True, exist_ok=True)
    test_src = git("show", f"{ARGS.head}:{TEST}")

    # ---- base ---------------------------------------------------------------------------------
    git("checkout", "-q", "--detach", ARGS.base)
    assert git("rev-parse", "HEAD").strip() == ARGS.base
    (W / TEST).write_text(test_src, encoding="utf-8")
    red = step("red_base", lambda: pytest([TEST]))
    (W / TEST).unlink()
    keep = [ln.rstrip() for ln in red.splitlines()
            if "FAILED tests/" in ln or ln.strip().startswith("=== Summary:") or re.match(r"^E\s", ln)]
    (RAW / "red_base.txt").write_text("\n".join(keep) + "\n", encoding="utf-8")
    assert git("status", "--porcelain").strip() == "", "base checkout dirty after RED"
    adj = step("adjacent_base", lambda: pytest(ADJACENT))
    (RAW / "adjacent_base.txt").write_text("\n".join(summary(adj)) + "\n", encoding="utf-8")
    for name, script in GUARDS:
        step(f"{name}_base", lambda n=name, s=script: guard(n, s, "base"))
    step("f09_base", lambda: f09("base"))

    # ---- head ---------------------------------------------------------------------------------
    git("checkout", "-q", "--detach", ARGS.head)
    assert git("rev-parse", "HEAD").strip() == ARGS.head
    greens = []
    for rep in range(3):
        greens += summary(step(f"green_rep{rep + 1}", lambda: pytest([TEST])))
    (RAW / "green3.txt").write_text("\n".join(greens) + "\n", encoding="utf-8")
    adj = step("adjacent_head", lambda: pytest(ADJACENT))
    (RAW / "adjacent_head.txt").write_text("\n".join(summary(adj)) + "\n", encoding="utf-8")
    for name, script in GUARDS:
        step(f"{name}_head", lambda n=name, s=script: guard(n, s, "head"))
    step("f09_head", lambda: f09("head"))
    env = {**os.environ}
    step("sabotage_head", lambda: subprocess.run(
        [PY, str(HERE / "sabotage.py"), "--worktree", str(W), "--out", str(RAW / "sabotage.json")],
        env=env, check=True, capture_output=True, text=True, timeout=3600))
    assert git("status", "--porcelain").strip() == "", "head checkout dirty after sabotage"

    (RAW / "run_meta.json").write_text(json.dumps({"base": ARGS.base, "head": ARGS.head, "steps": META,
                                                   "wall_s_total": round(sum(m["wall_s"] for m in META), 1),
                                                   "cpu_core_s_total": round(sum(m["cpu_core_s"] for m in META), 1)},
                                                  indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
