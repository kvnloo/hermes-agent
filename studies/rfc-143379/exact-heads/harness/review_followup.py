#!/usr/bin/env python3
"""Read-only exact-head review diagnostics for RFC #143379.

Requires an existing Hermes git clone with complete merge history (or enough
history for the referenced merge bases). Never checks out/merges a branch,
contacts a provider, or changes a tracked file. git merge-tree may create
unreachable temporary Git tree objects but does not move refs.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess

HEADS = {
    "read": "af16e3ab16eed2492552c325ad1777533a8b7004",  # #141876
    "chain": "2c1941aac46efac3b35605d99a8628e75a91c670",  # #116673
    "governance": "5b31ccb7d56ad614da63588ef876584b9f95dd3f",  # #139606
    "main_fix": "95610a5db4",  # pathlib.Path import on main
}
PAIRS = (("read", "chain"), ("read", "governance"), ("chain", "governance"))
ONBOARDING = "tui_gateway/methods_onboarding.py"


def git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


def object_present(repo: Path, sha: str) -> bool:
    return git(repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def pathlib_probe(repo: Path, label: str, sha: str) -> dict:
    """Source preflight, not a native runtime/pytest reproduction."""
    raw = git(repo, "show", f"{sha}:{ONBOARDING}")
    if raw.returncode:
        return {"status": "BLOCKED", "detail": raw.stderr.strip()}
    try:
        tree = ast.parse(raw.stdout)
    except SyntaxError as exc:
        return {"status": "BLOCKED", "detail": f"parse failure: {exc}"}
    import_path = any(
        isinstance(node, ast.ImportFrom) and node.module == "pathlib"
        and any(alias.name == "Path" for alias in node.names)
        for node in tree.body
    )
    uses_path = any(
        isinstance(node, ast.Name) and node.id == "Path"
        for node in ast.walk(tree)
    )
    return {"status": "SOURCE_CHECKED", "label": label, "sha": sha,
            "uses_Path": uses_path, "imports_Path_from_pathlib": import_path,
            "potential_NameError": uses_path and not import_path,
            "scope": "AST source preflight only; runtime reproduction separately required"}


def merge_probe(repo: Path, a: str, b: str) -> dict:
    """Pairwise composition; a failed merge-base is BLOCKED, not conflict-free."""
    names = f"{a}+{b}"
    base = git(repo, "merge-base", HEADS[a], HEADS[b])
    if base.returncode or not base.stdout.strip():
        return {"pair": names, "status": "BLOCKED",
                "reason": "merge base unavailable (shallow history or unrelated ancestry)",
                "stderr": base.stderr.strip()}
    result = git(repo, "merge-tree", "--write-tree", HEADS[a], HEADS[b])
    conflicts = re.findall(r"^CONFLICT[^\n]*", result.stdout, re.MULTILINE)
    if result.returncode == 0:
        status = "CLEAN"
    elif result.returncode == 1 and conflicts:
        status = "CONFLICT"
    else:
        status = "BLOCKED"
    return {"pair": names, "status": status, "exit_code": result.returncode,
            "merge_base": base.stdout.strip(), "conflicts": conflicts,
            "output": result.stdout, "stderr": result.stderr.strip(),
            "scope": "exact-head pairwise merge-tree; not a rebase or tested combined runtime"}


def report(repo: Path) -> dict:
    if git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        raise ValueError("--repo must be an existing full Git worktree")
    present = {name: object_present(repo, sha) for name, sha in HEADS.items()}
    sources = {
        name: pathlib_probe(repo, name, HEADS[name]) if present[name]
        else {"status": "BLOCKED", "reason": "pinned commit object unavailable", "sha": HEADS[name]}
        for name in ("chain", "governance", "main_fix")
    }
    combinations = [merge_probe(repo, a, b) if present[a] and present[b]
                    else {"pair": f"{a}+{b}", "status": "BLOCKED", "reason": "pinned commit unavailable"}
                    for a, b in PAIRS]
    return {"scope": "source and merge-composition preflight (no native read or LLM recall run)",
            "heads": HEADS, "all_objects_present": all(present.values()),
            "object_presence": present, "path_import": sources, "combinations": combinations,
            "gate": {"actual_integrated_tests": "NOT_RUN",
                     "real_compressor_300_cycle": "NOT_RUN",
                     "rfc_scope_bug_fixed": "NOT_VERIFIED"}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = report(args.repo.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path_import": {k: v.get("potential_NameError")
                                     for k, v in result["path_import"].items()},
                      "pairs": {x["pair"]: x["status"] for x in result["combinations"]},
                      "object_presence": result["object_presence"]}))
    return 0 if result["all_objects_present"] and all(
        x["status"] != "BLOCKED" for x in result["combinations"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
