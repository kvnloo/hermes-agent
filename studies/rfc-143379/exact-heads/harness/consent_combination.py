#!/usr/bin/env python3
"""Deterministic semantic resolver for DISPOSABLE native consent merge worktrees.

Do not run against a user worktree. Do not run tests here. See consent-merge.json.
The actual upstream main files remain the baseline. AST-selected consent changes
come from the exact PR commits. The resolver does not replace the real memory API.
It retains main's patch/remove semantics and metrics. It adds the target boundary
and, in combined mode, the exact upstream detector. Native git merges retain both
PR heads as ancestors. An ours-strategy merge needs this explicit semantic resolution.
The resulting combination is downstream code, not an untouched upstream PR head.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess


MAIN = "fab9b01c915a3118cc8daa6cc1b18c15b3f982d0"
TARGET = "f678f4c7e5d994f03d8759fe0e950d3407ccca7e"
DETECTOR = "96dc75192a82b6c5645a89c2eb894fba97ad2bbd"


def source(checkout, sha, path):
    return subprocess.run(["git", "-C", str(checkout), "show", f"{sha}:{path}"],
                          check=True, capture_output=True, text=True).stdout


def named_node(text, name):
    matches = []
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
            matches.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name
                                                 for target in node.targets):
            matches.append(node)
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one AST declaration: {name}")
    return matches[0]


def block(text, node):
    return "".join(text.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])


def replace_block(text, node, replacement):
    lines = text.splitlines(keepends=True)
    return "".join(lines[:node.lineno - 1]) + replacement + "".join(lines[node.end_lineno:])


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one exact source anchor: {old!r}")
    return text.replace(old, new, 1)


def consolidate(checkout, phase):
    memory_path, review_path = "tools/memory_tool.py", "agent/background_review.py"
    test_path = "tests/tools/test_memory_tool.py"
    main_memory = source(checkout, MAIN, memory_path)
    target_memory = source(checkout, TARGET, memory_path)
    detector_memory = source(checkout, DETECTOR, memory_path)
    memory = main_memory
    target_helper = block(target_memory, named_node(target_memory, "_background_op_needs_staging"))
    additions = target_helper
    if phase == "combined":
        # Preserve the exact upstream detector and helper, not a reimplementation.
        detector_regex = block(detector_memory, named_node(detector_memory, "_BG_NO_SAVE_RE"))
        detector_helper = block(detector_memory, named_node(detector_memory, "_consent_sensitive_add"))
        memory = replace_once(memory, "import logging\n", "import logging\nimport re\n")
        # Keep target=user adds staged even when no refusal appears in the proposal.
        # Main's destructive_ops includes patch as well as legacy replace/remove.
        target_helper = '''def _background_op_needs_staging(payload):
    """Downstream consolidation: destructive writes OR user adds OR self-reporting adds."""
    if destructive_ops(payload):
        return True
    ops = (payload.get("operations") or []) if payload.get("action") == "batch" else [payload]
    return any(
        (payload.get("target") == "user" and (op or {}).get("action") == "add")
        or _consent_sensitive_add((op or {}).get("action"), (op or {}).get("content"))
        for op in ops)
'''
        additions = detector_regex + "\n\n" + detector_helper + "\n\n" + target_helper
    gate_node = named_node(memory, "_background_delete_gate")
    gate = block(memory, gate_node)
    gate = replace_once(gate, "    if not destructive_ops(payload):\n",
                        "    if not _background_op_needs_staging(payload):\n")
    # These descriptions change only the staging policy. All main pinning, metrics,
    # error handling, patch support, and native stage_write calls remain intact.
    doc = ast.get_docstring(gate_node, clean=False)
    if doc is None:
        raise RuntimeError("The main background gate has no expected docstring")
    gate = replace_once(gate, '"""' + doc + '"""',
                        '"""Downstream consent consolidation. Unattended destructive writes, '
                        'user adds, and matched no-save adds stage through the native pending store. '
                        'Staging persists the proposal and is not a strict privacy refusal."""')
    gate = replace_once(gate, "Background review may not delete memory entries unattended.",
                        "Background review may not delete memory entries, add to the user profile, or persist facts the user asked not to save unattended.")
    gate = replace_once(gate, "batch); 'add' is still available.",
                        "batch) or persist gated user-profile/consent-sensitive adds unattended.")
    memory = replace_block(memory, gate_node, additions + "\n\n" + gate)

    review = source(checkout, MAIN, review_path)
    target_review = source(checkout, TARGET, review_path)
    if phase == "target":
        # The routing assignment carries the PR's consent rule. Preserve other main prompts.
        review = replace_block(review, named_node(review, "_MEMORY_ROUTING_BLOCK"),
                               block(target_review, named_node(target_review, "_MEMORY_ROUTING_BLOCK")))
    else:
        detector_review = source(checkout, DETECTOR, review_path)
        consent = block(detector_review, named_node(detector_review, "_MEMORY_CONSENT_BLOCK"))
        prompt_node = named_node(review, "_MEMORY_REVIEW_PROMPT")
        original_prompt = block(review, prompt_node)
        review = replace_block(review, prompt_node, consent + "\n\n" + original_prompt)
        for name in ("_MEMORY_REVIEW_PROMPT", "_COMBINED_REVIEW_PROMPT"):
            node = named_node(review, name)
            revised = replace_once(block(review, node), "_MEMORY_ROUTING_BLOCK +",
                                   "_MEMORY_ROUTING_BLOCK + _MEMORY_CONSENT_BLOCK +")
            review = replace_block(review, node, revised)

    tests = source(checkout, MAIN, test_path)
    target_tests = source(checkout, TARGET, test_path)
    target_methods = {"test_add_to_user_profile_staged_not_applied",
                      "test_batch_add_to_user_profile_staged",
                      "test_foreground_add_to_user_profile_unaffected"}
    methods = [node for node in ast.walk(ast.parse(target_tests))
               if isinstance(node, ast.FunctionDef) and node.name in target_methods]
    if {node.name for node in methods} != target_methods or len(methods) != 3:
        raise RuntimeError("Could not locate the three exact upstream target-boundary regressions")
    tests += "\n\nclass TestConsentCombinationTargetBoundary:\n"
    tests += "\n".join(block(target_tests, node) for node in sorted(methods, key=lambda node: node.lineno))
    outputs = {memory_path: memory, review_path: review, test_path: tests}
    if phase == "combined":
        detector_tests = source(checkout, DETECTOR, test_path)
        tests += "\n\n" + block(detector_tests, named_node(detector_tests, "TestBackgroundReviewConsentGate"))
        outputs[test_path] = tests
        prompt_test_path = "tests/agent/test_review_prompt_consent.py"
        outputs[prompt_test_path] = source(checkout, DETECTOR, prompt_test_path)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--phase", choices=("target", "combined"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    # MERGE_HEAD proves that this operation resolves a native merge, not a faux checkout.
    merge_head = subprocess.run(["git", "-C", str(checkout), "rev-parse", "--verify", "MERGE_HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
    expected = TARGET if args.phase == "target" else DETECTOR
    if merge_head != expected:
        raise RuntimeError(f"Wrong native merge head: expected {expected}, got {merge_head}")
    outputs = consolidate(checkout, args.phase)
    # Materialize only after every source anchor resolves. No tests or formatters run.
    files = []
    for relative, content in outputs.items():
        path = checkout / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        files.append({"path": relative, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"label": "downstream_semantic_combination_with_exact_native_merge_parents",
                                      "phase": args.phase, "native_merge_head": merge_head,
                                      "main": MAIN, "target": TARGET, "detector": DETECTOR,
                                      "files": files, "tests_executed": False}, indent=2) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
