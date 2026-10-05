from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.code_health.cli import run
from scripts.code_health.py_rules import Ctx, canonical_tree, gather_exception_check, import_time_capture, missing_timeout
from scripts.code_health.py_structure import nesting_depth

ROOT = Path(__file__).resolve().parents[2]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
        encoding="utf-8", timeout=60,
    ).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "scripts" / "ci").mkdir(parents=True)
    shutil.copy(ROOT / "pyproject.toml", repo / "pyproject.toml")
    shutil.copy(ROOT / "package-lock.json", repo / "package-lock.json")
    shutil.copy(ROOT / "scripts/ci/profile_scope_patterns.json", repo / "scripts/ci/")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    return repo


def _commit(repo: Path, files: dict[str, str]) -> str:
    for rel, content in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "step")
    return _git(repo, "rev-parse", "HEAD")


def _verdict(tmp_path: Path, source: str, suffix: str = ".py") -> tuple[int, str]:
    repo = _repo(tmp_path)
    base = _commit(repo, {f"pkg/a{suffix}": "export const ok = 1\n" if suffix != ".py" else "def ok():\n    return 1\n"})
    head = _commit(repo, {f"pkg/a{suffix}": source})
    code = run(repo, base, head)
    return code, ""


def test_import_alias_is_scoped_to_the_use(tmp_path):
    source = """from subprocess import run as execute

def identity(execute):
    return execute

def launch(cmd):
    return execute(cmd)
"""
    code, _ = _verdict(tmp_path, source)
    assert code == 1


def test_process_handles_do_not_collide_across_functions(tmp_path):
    source = """import asyncio
import subprocess

def sync(cmd):
    proc = subprocess.Popen(cmd)
    return proc.communicate(timeout=1)

async def asynchronous(cmd):
    proc = await asyncio.create_subprocess_exec(*cmd)
    return await asyncio.wait_for(proc.communicate(), timeout=1)
"""
    code, _ = _verdict(tmp_path, source)
    assert code == 0


def test_annotated_gather_results_keep_hx009():
    tree = canonical_tree(ast.parse("""import asyncio

async def f(tasks):
    results: list[object] = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            raise result
"""))
    assert list(gather_exception_check(tree, Ctx())) == [6]


def test_all_eager_captures_are_emitted():
    tree = canonical_tree(ast.parse("""import os
CACHE = {
    "new": os.getenv("HOME"),
    "old": os.getenv("PATH"),
}
"""))
    assert sorted(import_time_capture(tree, Ctx())) == [3, 4]


@pytest.mark.parametrize("tail", [
    "    return proc.wait()\n",
    "    rc: int = proc.wait()\n    return rc\n",
])
def test_post_kill_wait_is_bounded_for_return_and_annotation(tail):
    source = """import subprocess

def reap(cmd):
    proc = subprocess.Popen(cmd)
    proc.kill()
""" + tail
    tree = canonical_tree(ast.parse(source))
    assert list(missing_timeout(tree, Ctx())) == []


def test_typescript_parse_error_is_measurement_failure(tmp_path, capsys):
    repo = _repo(tmp_path)
    base = _commit(repo, {"pkg/a.ts": "export const ok = 1\n"})
    head = _commit(repo, {"pkg/a.ts": "export function broken(: {\n"})
    code = run(repo, base, head)
    out = capsys.readouterr().out
    assert code == 1
    assert "MEASURE" in out


def test_nested_else_if_is_not_flat_elif():
    src = """def f(a, b, c, d, e, f_, g):
    if a:
        pass
    else:
        if b:
            pass
        else:
            if c:
                pass
            else:
                if d:
                    pass
                else:
                    if e:
                        pass
                    else:
                        if f_:
                            pass
                        else:
                            if g:
                                pass
"""
    fn = ast.parse(src).body[0]
    assert nesting_depth(fn.body) == 7


def test_json_success_path_is_json():
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.code_health", "--base", "HEAD", "--head", "HEAD", "--json"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == []


def test_unknown_only_selector_is_usage_error():
    proc = subprocess.run(
        [sys.executable, "scripts/check", "--only", "nonexistent"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )
    assert proc.returncode != 0


def _checker_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "checker"
    (repo / "scripts" / "ci").mkdir(parents=True)
    shutil.copy(ROOT / "pyproject.toml", repo / "pyproject.toml")
    shutil.copy(ROOT / "package-lock.json", repo / "package-lock.json")
    shutil.copy(ROOT / "scripts/check", repo / "scripts/check")
    shutil.copytree(ROOT / "scripts/code_health", repo / "scripts/code_health")
    shutil.copy(ROOT / "scripts/ci/profile_scope_patterns.json", repo / "scripts/ci/")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _commit(repo, {"pkg/a.py": "def ok():\n    return 1\n"})
    return repo


def test_staged_health_uses_staged_policy_not_unstaged_policy(tmp_path):
    repo = _checker_repo(tmp_path)
    source = """import os
import subprocess

def f(cmd):
    env = os.environ.copy()
    return subprocess.run(cmd, env=env, timeout=1)
"""
    path = repo / "pkg/a.py"
    path.write_text(source, encoding="utf-8")
    _git(repo, "add", "pkg/a.py")
    tree = _git(repo, "write-tree")

    def check() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/check", "--staged", "--only", "health", "--base", "HEAD"],
            cwd=repo, capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
        )

    before = check()
    assert before.returncode == 1
    assert "PS-P05" in before.stdout

    policy = repo / "scripts/ci/profile_scope_patterns.json"
    data = json.loads(policy.read_text(encoding="utf-8"))
    for pattern in data["patterns"]:
        if pattern["id"] == "P05":
            pattern["path_regex"] = r"^never-match-this-probe$"
    policy.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    assert _git(repo, "write-tree") == tree
    after = check()
    assert after.returncode == 1
    assert "PS-P05" in after.stdout


def test_profile_regex_rules_ignore_prose(tmp_path):
    source = """def f():
    # Avoid env = os.environ.copy(); use the scoped builder.
    return 1
"""
    code, _ = _verdict(tmp_path, source)
    assert code == 0
