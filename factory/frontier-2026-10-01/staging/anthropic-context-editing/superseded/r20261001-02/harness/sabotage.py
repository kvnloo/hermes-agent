"""Per-hunk sabotage for staging/anthropic-context-editing: revert one production hunk at a time,
run the contract tests, restore. Writes a JSON summary to --out.

Usage (from anywhere):
  HERMES_PYTHON=<venv python> XF_TESTHOME=<isolated test home> \
    python sabotage.py --worktree <checkout at the staging head> --out raw/sabotage.json

No absolute paths are written to the output; the worktree is passed in, never recorded.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

TEST = "tests/agent/test_anthropic_context_editing.py"

# (id, file, old, new): each reverts exactly one non-test behavioural hunk of the change.
# Not mutated (no behaviour to pin): config_defaults default entry, cli-config.yaml.example,
# the two website docs pages, the adapter beta constant / signature / docstring.
MUTATIONS = [
    ("helpers-call-site", "agent/chat_completion_helpers.py",
     "context_management=anthropic_context_management(agent))", "context_management=None)"),
    ("adapter-extra-body", "agent/anthropic_adapter.py",
     '        kwargs.setdefault("extra_body", {})["context_management"] = context_management\n', ""),
    ("adapter-beta", "agent/anthropic_adapter.py",
     "        request_betas.append(_CONTEXT_MANAGEMENT_BETA)\n", ""),
    ("agent-init-parse", "agent/agent_init.py",
     'anthropic_context_editing=is_truthy_value(cfg.get("anthropic_context_editing"), default=False),',
     "anthropic_context_editing=False,"),
    ("agent-init-attr", "agent/agent_init.py",
     "    agent.anthropic_context_editing = cs.anthropic_context_editing\n", ""),
    ("recovery-anthropic-row", "agent/turn_recovery.py",
     '    "anthropic_messages": ("anthropic_context_editing", "context editing", "anthropic_context_editing"),\n', ""),
    ("recovery-setattr", "agent/turn_recovery.py",
     "            setattr(agent, flag, False)\n", ""),
    ("gate-native-route", "agent/anthropic_context_editing.py",
     "    if _is_third_party_anthropic_endpoint(getattr(agent, \"_anthropic_base_url\", None)):",
     "    if not _is_third_party_anthropic_endpoint(getattr(agent, \"_anthropic_base_url\", None)):"),
    ("gate-trigger-margin", "agent/anthropic_context_editing.py",
     "    trigger = resolve_compact_threshold(None, getattr(compressor, \"threshold_tokens\", None))",
     "    trigger = int(getattr(compressor, \"threshold_tokens\", 0) or 200_000) + 1"),
    ("transport-default", "agent/transports/anthropic.py",
     '    "context_management": None,\n', ""),
    # Sibling config paths: not reached by the contract tests (reported as unpinned).
    ("tui-hot-reload", "tui_gateway/session_compression.py",
     '    agent.anthropic_context_editing = is_truthy_value(compression.get("anthropic_context_editing", False))\n', ""),
    ("gateway-cache-key", "gateway/run.py",
     ' ("compression", "anthropic_context_editing"),', ""),
]


def run_tests(worktree: Path) -> dict:
    home = Path(os.environ["XF_TESTHOME"])
    env = {**os.environ, "HOME": str(home), "HERMES_HOME": str(home / ".hermes"),
           "HERMES_PYTHON": os.environ["HERMES_PYTHON"]}
    proc = subprocess.run(["bash", "scripts/run_tests.sh", "-j", "2", TEST, "-q", "-p", "no:logging"],
                          cwd=worktree, env=env, capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    m = re.search(r"Summary: \d+ files, (\d+) tests passed, (\d+) failed", out)
    failed = sorted(set(re.findall(r"FAILED (tests/\S+)", out)))
    errors = sorted(set(re.findall(r"^E\s+(.{0,160})", out, re.M)))[:6]
    return {"passed": int(m.group(1)) if m else None, "failed": int(m.group(2)) if m else None,
            "failed_tests": failed, "assertions": errors, "rc": proc.returncode}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    worktree = Path(args.worktree)
    results = []
    for mid, rel, old, new in MUTATIONS:
        path = worktree / rel
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            results.append({"id": mid, "file": rel, "error": f"anchor count {original.count(old)}"})
            continue
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            res = run_tests(worktree)
        finally:
            path.write_text(original, encoding="utf-8")
        res.update({"id": mid, "file": rel, "re_red": bool(res.get("failed"))})
        results.append(res)
        print(json.dumps({k: res[k] for k in ("id", "re_red", "passed", "failed")}), flush=True)
    Path(args.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
