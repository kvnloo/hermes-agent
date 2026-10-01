#!/usr/bin/env python3
"""Per-hunk sabotage for the compressor media extraction commit.

    python3 sabotage_perhunk.py <head-checkout> <base-checkout> --python $HERMES_PYTHON \
        --home <scratch-home> --json sabotage.json [--wide-files-from wide.txt] [--only ID ...]

<head-checkout> must be a clean checkout of the extraction commit; <base-checkout> a clean checkout of
its parent. Every mutation is applied to <head-checkout>, measured, and undone with
``git checkout -- . && git clean -fdq`` (never stash). The script refuses to start on a dirty tree
and stops if a restore leaves the tree dirty.

Mutations, one per row:

* ``hunk:<file>#<n>``: reverse-apply hunk n of the commit's ``-U0`` diff for every file except the
  new sibling (``git apply -R --unidiff-zero``). This puts that one line range back the way main had it.
* ``facade-import:<name>``: drop one name from the facade's ``from agent.context_compressor_media
  import (...)``, i.e. the per-name split of the facade import hunk.
* ``sibling:<name>``: the sibling file is one added hunk, so it is sabotaged per moved statement:
  a function gets ``raise RuntimeError`` as its first statement; a constant gets an empty value
  (``0`` or ``frozenset()``).
* ``hunk:agent/context_compressor.py#deletions``: every pure-deletion hunk of the facade reversed
  together, i.e. the facade gets its own copies of the moved code back (behaviour-neutral by
  construction; single deletion hunks can break import because the constant and its users sit in
  different hunks).
* ``control:reexport:<name>``: a moved name the facade does not read is added to its sibling import
  (a re-export shim); a control for the ``no_shim`` gate, not a hunk.

Each mutation is measured two ways:

* tests: ``scripts/run_tests.sh -j 2 <narrow set> -q -rfE`` with HOME/HERMES_HOME at <scratch-home>.
  ``RED`` means a failed test, a collection error or a non-zero exit.
* static: ``verify_media.py <base> <head>``; the gates that flip to FAIL are listed.

A mutation whose narrow tests stay green and that changes behaviour (``sibling:*`` and
``facade-import:*``) is re-run on the wide set when ``--wide-files-from`` is given. A row with tests
GREEN and no static gate FAIL is UNPINNED; the summary lists every unpinned row.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACADE = "agent/context_compressor.py"
SIBLING = "agent/context_compressor_media.py"
SIBLING_MOD = "agent.context_compressor_media"

NARROW = (
    # the five test files the commit touches plus the unchanged compressor guard
    "tests/agent/test_compressor_historical_media.py",
    "tests/agent/test_compressor_stale_tool_images.py",
    "tests/agent/test_outbound_stale_vision.py",
    "tests/agent/test_protected_tail_pressure.py",
    "tests/agent/test_image_eviction_policy.py",
    "tests/agent/test_compressor_zero_user_guard.py",
    # iteration-summary send path (chat_completion_helpers)
    "tests/agent/test_image_rejection_fallback.py",
    "tests/agent/test_iteration_summary_reasoning_details.py",
    # per-turn send path (conversation_loop -> turn_request_assembly)
    "tests/agent/test_dict_tool_call_args.py",
    "tests/agent/test_context_token_tracking.py",
    "tests/agent/test_degenerate_final_recovery.py",
)

_ID = re.compile(r"^\s*(?:║\s*)?(FAILED|ERROR) (tests/\S+)", re.M)
_SUMMARY = re.compile(r"Summary: (\d+) files?, (\d+) tests passed, (\d+) failed")
_NO_TESTS = re.compile(r"=== (\d+) files? where no tests ran")
_FAILED_FILE = re.compile(r"\] \u2717 (tests/\S+\.py) \(")


def git(tree: Path, *args: str, check: bool = True, input: str | None = None) -> str:
    p = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, input=input)
    if check and p.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout


def assert_clean(tree: Path) -> None:
    dirty = git(tree, "status", "--porcelain")
    if dirty.strip():
        raise SystemExit(f"tree not clean:\n{dirty}")


def restore(tree: Path) -> None:
    git(tree, "checkout", "--", ".")
    git(tree, "clean", "-fdq")
    assert_clean(tree)


def hunks(tree: Path) -> list[tuple[str, str, str]]:
    """(row id, header, patch) for every -U0 hunk of HEAD except the new sibling."""
    out = []
    files = [f for f in git(tree, "diff", "--name-only", "HEAD~1", "HEAD").split() if f != SIBLING]
    for f in files:
        diff = git(tree, "diff", "-U0", "HEAD~1", "HEAD", "--", f)
        head, _, body = diff.partition("\n@@")
        parts = ("@@" + body).split("\n@@")
        for n, part in enumerate(parts, 1):
            hunk = part if part.startswith("@@") else "@@" + part
            header = hunk.splitlines()[0]
            out.append((f"hunk:{f}#{n}", header, head + "\n" + hunk.rstrip("\n") + "\n"))
    return out


def facade_import_names(tree: Path) -> list[str]:
    mod = ast.parse((tree / FACADE).read_text(encoding="utf-8"))
    for node in mod.body:
        if isinstance(node, ast.ImportFrom) and node.module == SIBLING_MOD:
            return [a.name for a in node.names]
    return []


def drop_facade_name(tree: Path, name: str, add: str | None = None) -> None:
    """Rewrite the facade's sibling import without ``name`` (and with ``add``, if given)."""
    path = tree / FACADE
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    for node in ast.parse(src).body:
        if isinstance(node, ast.ImportFrom) and node.module == SIBLING_MOD:
            keep = sorted([a.name for a in node.names if a.name != name] + ([add] if add else []))
            new = f"from {SIBLING_MOD} import (\n" + "".join(f"    {k},\n" for k in keep) + ")\n"
            lines[node.lineno - 1:node.end_lineno] = [new]
            path.write_text("".join(lines), encoding="utf-8")
            return
    raise SystemExit("facade sibling import not found")


def sibling_targets(tree: Path) -> list[str]:
    names = []
    for node in ast.parse((tree / SIBLING).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef):
            names.append(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(tgt, ast.Name):
                names.append(tgt.id)
    return names


def sabotage_sibling(tree: Path, name: str) -> str:
    path = tree / SIBLING
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            first = node.body[0]
            lines.insert(first.lineno - 1, " " * first.col_offset + f'raise RuntimeError("sabotage {name}")\n')
            path.write_text("".join(lines), encoding="utf-8")
            return "first statement raises RuntimeError"
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(tgt, ast.Name) and tgt.id == name:
                v = node.value
                empty = "0" if isinstance(v, ast.Constant) and isinstance(v.value, int) else "frozenset()"
                line = lines[v.lineno - 1]
                if v.lineno != v.end_lineno:
                    raise SystemExit(f"{name}: multi-line constant not supported")
                lines[v.lineno - 1] = line[:v.col_offset] + empty + line[v.end_col_offset:]
                path.write_text("".join(lines), encoding="utf-8")
                return f"value replaced with {empty}"
    raise SystemExit(f"{name}: not found in sibling")


def run_tests(tree: Path, files: list[str], home: Path, py: str, log: Path,
              known: frozenset[str] = frozenset()) -> dict:
    """Run the files; RED means a failing/erroring id or failed file that is not in ``known``.

    ``known`` holds test ids (and file paths) that already fail on the unmutated tree, e.g. the
    pre-existing failures of the full tests/agent + tests/tools run. Without it, any failure is RED.
    """
    (home / ".hermes").mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "HOME": str(home), "HERMES_HOME": str(home / ".hermes"), "HERMES_PYTHON": py}
    p = subprocess.run(["bash", "scripts/run_tests.sh", "-j", "2", *files, "-q", "-rfE"], cwd=tree, env=env,
                       capture_output=True, text=True)
    text = p.stdout + p.stderr
    log.write_text(text, encoding="utf-8")
    m = _SUMMARY.search(text)
    nt = _NO_TESTS.search(text)
    found = _ID.findall(text)
    ids = sorted({f"{k} {i}" for k, i in found})
    failed_files = sorted(set(_FAILED_FILE.findall(text)))
    passed, failed = (int(m.group(2)), int(m.group(3))) if m else (0, 0)
    no_tests = int(nt.group(1)) if nt else 0

    # ids are cut at the first space by the same \S+ the known list was parsed with, so exact match
    # works for truncated parametrized ids; a bare file path in ``known`` covers the whole file.
    new_ids = sorted({f"{k} {i}" for k, i in found if i not in known and i.split("::")[0] not in known})
    known_files = {k.split("::")[0] for k in known}
    new_files = [f for f in failed_files if f not in known_files and not any(i.split(" ", 1)[1].startswith(f)
                                                                             for i in new_ids)]
    red = (not m) or bool(new_ids) or bool(new_files) or (not known and (failed > 0 or no_tests > 0))
    return {"outcome": "RED" if red else "GREEN", "rc": p.returncode, "passed": passed, "failed": failed,
            "files_no_tests": no_tests, "failed_files": failed_files, "ids": ids, "new_ids": new_ids,
            "new_failed_files_without_ids": new_files}


def run_static(base: Path, tree: Path, py: str) -> dict:
    p = subprocess.run([sys.executable, "-B", str(HERE / "verify_media.py"), str(base), str(tree), "--python", py],
                       capture_output=True, text=True)
    try:
        rep = json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"overall": "ERROR", "failed_gates": [], "stderr_tail": p.stderr.strip().splitlines()[-3:]}
    return {"overall": rep["overall"], "failed_gates": [k for k, g in rep["gates"].items() if g["result"] != "PASS"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("head", type=Path)
    ap.add_argument("base", type=Path)
    ap.add_argument("--python", required=True)
    ap.add_argument("--home", type=Path, required=True)
    ap.add_argument("--json", type=Path, required=True)
    ap.add_argument("--logs", type=Path, help="directory for per-row test logs (default: next to --json)")
    ap.add_argument("--wide-files-from", type=Path)
    ap.add_argument("--known-failures", type=Path,
                    help="ids already failing on the unmutated tree (one per line); excluded on the wide set")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    head, base = a.head.resolve(), a.base.resolve()
    logs = (a.logs or a.json.parent / "sabotage-logs").resolve()
    logs.mkdir(parents=True, exist_ok=True)
    assert_clean(head)
    if git(head, "rev-parse", "HEAD~1").strip() != git(base, "rev-parse", "HEAD").strip():
        raise SystemExit("base checkout is not the parent of head")
    wide = a.wide_files_from.read_text().split() if a.wide_files_from else []
    known = frozenset(a.known_failures.read_text().split()) if a.known_failures else frozenset()

    rows: list[dict] = []
    plan: list[tuple[str, str, object]] = []
    for rid, header, patch in hunks(head):
        plan.append((rid, header, ("patch", patch)))
    for name in facade_import_names(head):
        plan.append((f"facade-import:{name}", f"drop {name} from the facade's sibling import", ("drop", name)))
    for name in sibling_targets(head):
        plan.append((f"sibling:{name}", "", ("sib", name)))
    deletions = [patch for rid, _h, patch in hunks(head)
                 if rid.startswith(f"hunk:{FACADE}#") and not any(
                     ln.startswith("+") and not ln.startswith("+++") for ln in patch.splitlines())]
    plan.append((f"hunk:{FACADE}#deletions", f"reverse all {len(deletions)} pure-deletion facade hunks together",
                 ("patches", deletions)))
    unread = [n for n in sibling_targets(head) if n not in facade_import_names(head)
              and not n.isupper()]
    if unread:
        plan.append((f"control:reexport:{unread[0]}", f"add {unread[0]} to the facade's sibling import (a shim)",
                     ("reexport", unread[0])))

    baseline = run_tests(head, list(NARROW), a.home, a.python, logs / "baseline.log")
    if baseline["outcome"] != "GREEN":
        raise SystemExit(f"unmutated head is not green on the narrow set: {baseline}")

    for rid, desc, (kind, arg) in plan:
        if a.only and rid not in a.only:
            continue
        if kind in ("patch", "patches"):
            # several hunks of one file: reverse them bottom-up so earlier line numbers stay valid
            for patch in ([arg] if kind == "patch" else list(reversed(arg))):
                p = subprocess.run(["git", "-C", str(head), "apply", "-R", "--unidiff-zero", "-"], input=patch,
                                   text=True, capture_output=True)
                if p.returncode:
                    raise SystemExit(f"{rid}: reverse apply failed: {p.stderr.strip()}")
        elif kind == "drop":
            drop_facade_name(head, arg)
        elif kind == "reexport":
            drop_facade_name(head, "", add=arg)
        else:
            desc = sabotage_sibling(head, arg)
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", rid)
        row = {"id": rid, "mutation": desc,
               "tests_narrow": run_tests(head, list(NARROW), a.home, a.python, logs / f"{safe}.log"),
               "static": run_static(base, head, a.python)}
        if wide and kind in ("sib", "drop") and row["tests_narrow"]["outcome"] == "GREEN":
            row["tests_wide"] = run_tests(head, wide, a.home, a.python, logs / f"{safe}.wide.log", known)
        tests_red = any(row.get(k, {}).get("outcome") == "RED" for k in ("tests_narrow", "tests_wide"))
        row["pinned_by"] = (["tests"] if tests_red else []) + (["static:" + g for g in row["static"]["failed_gates"]])
        rows.append(row)
        print(f"{rid:70s} tests={'RED' if tests_red else 'GREEN':5s} static={','.join(row['static']['failed_gates']) or '-'}",
              flush=True)
        restore(head)

    unpinned = [r["id"] for r in rows if not r["pinned_by"]]
    tests_only_green = [r["id"] for r in rows if "tests" not in r["pinned_by"]]
    report = {"head": git(head, "rev-parse", "HEAD").strip(), "base": git(base, "rev-parse", "HEAD").strip(),
              "narrow_set": list(NARROW), "wide_set_files": len(wide), "known_failures": sorted(known), "baseline_narrow": baseline,
              "rows": rows, "summary": {"rows": len(rows), "tests_red": len(rows) - len(tests_only_green),
                                        "green_under_tests_pinned_by_static_only": [r for r in tests_only_green
                                                                                    if r not in unpinned],
                                        "unpinned": unpinned}}
    a.json.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
