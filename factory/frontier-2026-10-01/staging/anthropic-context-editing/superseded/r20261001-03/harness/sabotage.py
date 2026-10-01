"""Per-hunk sabotage for staging/anthropic-context-editing: break one production hunk at a time,
run the tests that should notice, restore. Writes a JSON summary to --out.

Usage (from anywhere):
  HERMES_PYTHON=<venv python> XF_TESTHOME=<isolated test home> \
    python sabotage.py --worktree <checkout at the staging head> --out raw/sabotage.json

Kinds: "revert" deletes or undoes one added line or condition; "mutation" changes a value instead
(used where deleting the line would only crash the import). Every gate condition is removed on its
own. "adjacent" rows break a refactored pre-existing path and run the existing test that owns it,
not the contract test. No absolute paths are written to the output; the worktree is never recorded.

Not mutated (no behaviour of their own, or only bounded by the tests): config_defaults default
entry, cli-config.yaml.example, the two website docs pages, the adapter beta constant / signature /
docstring, CLEAR_AT_LEAST_FRACTION's value (the test only checks 0 < clear_at_least < trigger), and
the recovery display name / log text.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

TEST = "tests/agent/test_anthropic_context_editing.py"
GATE = "agent/anthropic_context_editing.py"

# (id, kind, file, old, new, tests)
MUTATIONS = [
    ("helpers-call-site", "revert", "agent/chat_completion_helpers.py",
     "context_management=anthropic_context_management(agent))", "context_management=None)", TEST),
    ("adapter-extra-body", "revert", "agent/anthropic_adapter.py",
     '        kwargs.setdefault("extra_body", {})["context_management"] = context_management\n', "", TEST),
    ("adapter-beta", "revert", "agent/anthropic_adapter.py",
     "        request_betas.append(_CONTEXT_MANAGEMENT_BETA)\n", "", TEST),
    ("agent-init-parse", "mutation", "agent/agent_init.py",
     'anthropic_context_editing=is_truthy_value(cfg.get("anthropic_context_editing"), default=False),',
     "anthropic_context_editing=False,", TEST),
    ("agent-init-attr", "revert", "agent/agent_init.py",
     "    agent.anthropic_context_editing = cs.anthropic_context_editing\n", "", TEST),
    ("recovery-anthropic-row", "revert", "agent/turn_recovery.py",
     '    "anthropic_messages": ("anthropic_context_editing", "context editing", "anthropic_context_editing"),\n', "", TEST),
    ("recovery-setattr", "revert", "agent/turn_recovery.py",
     "            setattr(agent, flag, False)\n", "", TEST),
    ("gate-flag", "revert", GATE,
     '    if not getattr(agent, "anthropic_context_editing", False) or not getattr(agent, "compression_enabled", True):',
     '    if not getattr(agent, "compression_enabled", True):', TEST),
    ("gate-compression-enabled", "revert", GATE,
     '    if not getattr(agent, "anthropic_context_editing", False) or not getattr(agent, "compression_enabled", True):',
     '    if not getattr(agent, "anthropic_context_editing", False):', TEST),
    ("gate-checkpoint-required", "revert", GATE,
     '    if getattr(agent, "compression_checkpoint_required", False) is True:\n        return None\n', "", TEST),
    ("gate-claude-model", "revert", GATE,
     '    if "claude" not in str(getattr(agent, "model", None) or "").lower():\n        return None\n', "", TEST),
    ("gate-third-party-endpoint", "revert", GATE,
     '    if _is_third_party_anthropic_endpoint(getattr(agent, "_anthropic_base_url", None)):\n        return None\n', "", TEST),
    ("gate-trigger-margin", "mutation", GATE,
     '    trigger = resolve_compact_threshold(None, getattr(compressor, "threshold_tokens", None))',
     '    trigger = int(getattr(compressor, "threshold_tokens", 0) or 200_000) + 1', TEST),
    ("transport-default", "revert", "agent/transports/anthropic.py",
     '    "context_management": None,\n', "", TEST),
    # Sibling config paths: not reached by the contract tests (reported as unpinned).
    ("tui-hot-reload", "revert", "tui_gateway/session_compression.py",
     '    agent.anthropic_context_editing = is_truthy_value(compression.get("anthropic_context_editing", False))\n', "", TEST),
    ("gateway-cache-key", "revert", "gateway/run.py",
     ' ("compression", "anthropic_context_editing"),', "", TEST),
    # Refactored pre-existing paths, checked against the existing tests that own them.
    ("adapter-fast-mode-beta", "adjacent", "agent/anthropic_adapter.py",
     "        request_betas.append(_FAST_MODE_BETA)\n", "", "tests/hermes_cli/test_fast_command.py"),
    ("recovery-codex-row", "adjacent", "agent/turn_recovery.py",
     '    "codex_responses": ("codex_responses_native_compaction", "native compaction", "codex_responses_native"),\n', "",
     "tests/agent/test_native_compaction.py"),
]


def run_tests(worktree: Path, test: str) -> dict:
    home = Path(os.environ["XF_TESTHOME"])
    env = {**os.environ, "HOME": str(home), "HERMES_HOME": str(home / ".hermes"),
           "HERMES_PYTHON": os.environ["HERMES_PYTHON"]}
    proc = subprocess.run(["bash", "scripts/run_tests.sh", "-j", "2", test, "-q", "-p", "no:logging"],
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
    for mid, kind, rel, old, new, test in MUTATIONS:
        path = worktree / rel
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            results.append({"id": mid, "kind": kind, "file": rel, "test": test, "error": f"anchor count {original.count(old)}"})
            continue
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            res = run_tests(worktree, test)
        finally:
            path.write_text(original, encoding="utf-8")
        res.update({"id": mid, "kind": kind, "file": rel, "test": test, "re_red": bool(res.get("failed"))})
        results.append(res)
        print(json.dumps({k: res[k] for k in ("id", "re_red", "passed", "failed")}), flush=True)
    Path(args.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
