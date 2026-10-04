#!/usr/bin/env python3
"""Fork-only evidence probes for the code-health architecture discussion.

This is intentionally not a production test file. It asks whether broader design claims are
actually supported by current-head behavior:
1. Is a verdict bound to the exact subject + policy artifact?
2. Does measurement failure fail closed?
3. Do debt-preserving/refactor transformations obey conservation?
4. How stable are semantic rules across equivalent Python spellings/scopes?
5. Are the probes sensitive to the enforcement seam they claim to test?
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts.code_health import py_rules
from scripts.code_health.cli import run

ROOT = Path(__file__).resolve().parents[1]
RESULTS: dict[str, object] = {"head": subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
).strip(), "experiments": {}}


def git(repo: Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True,
        encoding="utf-8", timeout=60, check=False,
    )
    if check and p.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr}")
    return p.stdout.strip()


def commit(repo: Path, files: dict[str, str | None], message: str = "step") -> str:
    for rel, text in files.items():
        p = repo / rel
        if text is None:
            if p.exists():
                p.unlink()
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def fresh_repo() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    td = tempfile.TemporaryDirectory(prefix="health-arch-")
    repo = Path(td.name)
    (repo / "scripts" / "ci").mkdir(parents=True)
    shutil.copy(ROOT / "pyproject.toml", repo / "pyproject.toml")
    shutil.copy(ROOT / "scripts/ci/profile_scope_patterns.json", repo / "scripts/ci/")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "probe@example.com")
    git(repo, "config", "user.name", "probe")
    return td, repo


def verdict(repo: Path, base: str, head: str | None) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = run(repo, base, head)
    return code, buf.getvalue()


def eval_pair(base_files: dict[str, str], head_files: dict[str, str | None]) -> tuple[int, str]:
    td, repo = fresh_repo()
    try:
        base = commit(repo, base_files, "base")
        head = commit(repo, head_files, "head")
        return verdict(repo, base, head)
    finally:
        td.cleanup()


def record(group: str, name: str, expected: int | str | bool, actual: int | str | bool, detail: str = "") -> None:
    g = RESULTS["experiments"].setdefault(group, {})
    g[name] = {"expected": expected, "actual": actual, "pass": actual == expected, "detail": detail}


def experiment_artifact_identity() -> None:
    td, repo = fresh_repo()
    try:
        base = commit(repo, {"pkg/a.py": "def ok():\n    return 1\n"}, "base")
        # Keep policy in the index, stage only the violating source, then pin the exact index tree.
        (repo / "pkg/a.py").write_text(
            "import os\n\ndef f():\n    env = os.environ.copy()\n    return env\n",
            encoding="utf-8",
        )
        git(repo, "add", "pkg/a.py")
        tree = git(repo, "write-tree")
        code_a, out_a = verdict(repo, base, tree)

        policy = repo / "scripts/ci/profile_scope_patterns.json"
        data = json.loads(policy.read_text(encoding="utf-8"))
        for item in data["patterns"]:
            if item.get("id") == "P05":
                item["path_regex"] = r"^never-match-this-probe$"
        policy.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # Subject tree is byte-identical; only unstaged policy differs.
        assert git(repo, "write-tree") == tree
        code_b, out_b = verdict(repo, base, tree)
        stable = (code_a, "PS-P05" in out_a) == (code_b, "PS-P05" in out_b)
        record(
            "artifact_identity",
            "same_subject_tree_unstaged_policy_change",
            True,
            stable,
            f"before=({code_a}, PS-P05={'PS-P05' in out_a}); after=({code_b}, PS-P05={'PS-P05' in out_b}); tree={tree}",
        )
    finally:
        td.cleanup()


def experiment_measurement_failure() -> None:
    code, out = eval_pair(
        {"pkg/a.py": "def ok():\n    return 1\n"},
        {"pkg/a.py": "def broken(:\n    pass\n"},
    )
    record("measurement", "python_syntax_error_blocks", 1, code, "MEASURE=" + str("MEASURE" in out))


def experiment_debt_conservation() -> None:
    swallow = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        pass\n"
    )
    base = {"pkg/a.py": swallow}

    cases = {
        "comment_only_preserves": ({"pkg/a.py": swallow.replace("except Exception:", "except Exception:  # note")}, 0),
        "file_rename_preserves": ({"pkg/a.py": None, "pkg/b.py": swallow}, 0),
        "copy_is_new_debt": ({"pkg/a.py": swallow + "\n" + swallow.replace("def f", "def g")}, 1),
        "relocate_identical_hit_is_new": ({
            "pkg/a.py": (
                "def f():\n"
                "    x = 1\n"
                "    y = 2\n"
                "    try:\n"
                "        pass\n"
                "    except Exception:\n"
                "        pass\n"
            )
        }, 1),
    }
    for name, (head, expected) in cases.items():
        code, out = eval_pair(base, head)
        record("debt_conservation", name, expected, code, out.splitlines()[-1] if out else "")


def semantic_case(source: str) -> tuple[int, str]:
    return eval_pair({"pkg/a.py": "def baseline():\n    return 1\n"}, {"pkg/a.py": source})


def experiment_semantic_equivalence() -> None:
    cases: dict[str, tuple[str, int]] = {
        "subprocess_canonical": (
            "import subprocess\n\ndef f(cmd):\n    return subprocess.run(cmd)\n", 1
        ),
        "subprocess_alias": (
            "from subprocess import run as execute\n\ndef f(cmd):\n    return execute(cmd)\n", 1
        ),
        "subprocess_alias_unrelated_param": (
            "from subprocess import run as execute\n\n"
            "def identity(execute):\n    return execute\n\n"
            "def launch(cmd):\n    return execute(cmd)\n", 1
        ),
        "local_helper_not_subprocess": (
            "def execute(cmd):\n    return cmd\n\ndef f(cmd):\n    return execute(cmd)\n", 0
        ),
        "asyncio_alias_event_loop": (
            "import asyncio as aio\n\ndef f():\n    return aio.get_event_loop()\n", 1
        ),
        "local_wait_for_does_not_grant_deadline": (
            "import asyncio\n\n"
            "async def wait_for(aw, timeout):\n    return await aw\n\n"
            "async def f(cmd):\n"
            "    proc = await asyncio.create_subprocess_exec(*cmd)\n"
            "    return await wait_for(proc.communicate(), 1)\n", 1
        ),
        "real_wait_for_grants_deadline": (
            "import asyncio\n\n"
            "async def f(cmd):\n"
            "    proc = await asyncio.create_subprocess_exec(*cmd)\n"
            "    return await asyncio.wait_for(proc.communicate(), timeout=1)\n", 0
        ),
        "process_bindings_are_lexically_independent": (
            "import asyncio\nimport subprocess\n\n"
            "def sync(cmd):\n"
            "    proc = subprocess.Popen(cmd)\n"
            "    return proc.communicate(timeout=1)\n\n"
            "async def asynchronous(cmd):\n"
            "    proc = await asyncio.create_subprocess_exec(*cmd)\n"
            "    return await asyncio.wait_for(proc.communicate(), timeout=1)\n", 0
        ),
        "annotated_gather_results_are_checked": (
            "import asyncio\n\n"
            "async def f(tasks):\n"
            "    results: list[object] = await asyncio.gather(*tasks, return_exceptions=True)\n"
            "    for result in results:\n"
            "        if isinstance(result, Exception):\n"
            "            raise result\n"
            "    return results\n", 1
        ),
    }
    for name, (source, expected) in cases.items():
        code, out = semantic_case(source)
        record("semantic_equivalence", name, expected, code, out.splitlines()[-1] if out else "")


def experiment_sabotage_sensitivity() -> None:
    source = "import subprocess\n\ndef f(cmd):\n    return subprocess.run(cmd)\n"
    code_before, _ = semantic_case(source)
    original = py_rules.CHECKERS["HX006"]
    try:
        py_rules.CHECKERS["HX006"] = lambda tree, ctx: ()
        code_after, _ = semantic_case(source)
    finally:
        py_rules.CHECKERS["HX006"] = original
    record(
        "sabotage",
        "hx006_probe_detects_disabled_enforcement",
        True,
        code_before == 1 and code_after == 0,
        f"normal={code_before}, disabled={code_after}",
    )


def main() -> int:
    experiment_artifact_identity()
    experiment_measurement_failure()
    experiment_debt_conservation()
    experiment_semantic_equivalence()
    experiment_sabotage_sensitivity()

    total = failed = 0
    for group in RESULTS["experiments"].values():
        for item in group.values():
            total += 1
            failed += 0 if item["pass"] else 1

    RESULTS["summary"] = {"total": total, "matched_expected_contract": total - failed, "mismatches": failed}
    out = ROOT / "architecture-evidence.json"
    out.write_text(json.dumps(RESULTS, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"\narchitecture evidence: {total - failed}/{total} expectations matched; {failed} mismatches")
    # Evidence workflow itself succeeds even when current architecture violates a hypothesis.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
