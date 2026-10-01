#!/usr/bin/env python3
"""Static parity / no-shim gates for the compressor media extraction.

    python3 verify_media.py <base-checkout> <head-checkout> [--python PY] [--json OUT]

<base> is the untouched main checkout; <head> is the same main after extract_media.py.
Gates (each PASS/FAIL, all must PASS):

  verbatim      every moved statement's source text and AST are identical base->head
  facade_rest   every other top-level facade statement is AST-identical, in order
  no_shim       the facade imports from the sibling only names it reads itself;
                the sibling never imports the facade (module level or function-local)
  old_path_zero no import, dotted text, module-alias, getattr/setattr/patch string or doc
                mention reaches a moved name through agent.context_compressor
  native_coupling agent/native_compaction.py byte-identical; is_compaction_summary_message
                still defined in the facade
  imports       fresh interpreters (loopback-only socket guard) import the sibling alone,
                the facade, native_compaction and both send-path callers

Stdlib only. Exit 0 only when every gate passes.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_media import FACADE, MOVED, SIBLING, _bound_name, _segment  # noqa: E402

FACADE_MOD = "agent.context_compressor"
SIBLING_MOD = "agent.context_compressor_media"


def _top(tree: ast.Module) -> dict[str, ast.stmt]:
    out: dict[str, ast.stmt] = {}
    for n in tree.body:
        name = _bound_name(n)
        if name:
            out.setdefault(name, n)
    return out


def gate_verbatim(base_src: str, head_sib: str) -> dict:
    bl, sl = base_src.splitlines(keepends=True), head_sib.splitlines(keepends=True)
    bt, st = _top(ast.parse(base_src)), _top(ast.parse(head_sib))
    bad = []
    for name in MOVED:
        if name not in bt or name not in st:
            bad.append(f"{name}: missing")
            continue
        bs, be = _segment(bl, bt[name])
        ss, se = _segment(sl, st[name])
        if "".join(bl[bs : be + 1]) != "".join(sl[ss : se + 1]):
            bad.append(f"{name}: source text differs")
        if ast.dump(bt[name]) != ast.dump(st[name]):
            bad.append(f"{name}: AST differs")
    return {"result": "FAIL" if bad else "PASS", "moved": len(MOVED), "problems": bad}


def gate_facade_rest(base_src: str, head_src: str) -> dict:
    def rest(src: str) -> list[str]:
        return [
            ast.dump(n) for n in ast.parse(src).body
            if not isinstance(n, (ast.Import, ast.ImportFrom)) and _bound_name(n) not in MOVED
        ]
    b, h = rest(base_src), rest(head_src)
    head_defs = {_bound_name(n) for n in ast.parse(head_src).body} & set(MOVED)
    ok = b == h and not head_defs
    return {
        "result": "PASS" if ok else "FAIL",
        "statements_compared": len(b),
        "head_still_defines_moved": sorted(head_defs),
        "first_mismatch": next((i for i, (x, y) in enumerate(zip(b, h)) if x != y), None) if b != h else None,
    }


def gate_no_shim(head_src: str, head_sib: str) -> dict:
    tree = ast.parse(head_src)
    imported = [
        (a.asname or a.name) for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module == SIBLING_MOD for a in n.names
    ]
    reads = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    unused = sorted(set(imported) - reads)
    has_all = any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets) for n in tree.body)
    sib_tree = ast.parse(head_sib)
    back = [
        n.lineno for n in ast.walk(sib_tree)
        if (isinstance(n, ast.ImportFrom) and n.module == FACADE_MOD)
        or (isinstance(n, ast.Import) and any(a.name == FACADE_MOD for a in n.names))
    ]
    ok = not unused and not back and not has_all
    return {
        "result": "PASS" if ok else "FAIL",
        "facade_imports_from_sibling": imported,
        "imported_but_unread": unused,
        "sibling_imports_facade_at_lines": back,
        "facade_defines___all__": has_all,
    }


def gate_old_path_zero(head: Path) -> dict:
    files = subprocess.run(["git", "-C", str(head), "ls-files"], check=True, capture_output=True, text=True).stdout.split()
    files.append(SIBLING)
    moved_alt = "|".join(MOVED)
    dotted = re.compile(rf"\bcontext_compressor\.({moved_alt})\b")
    quoted = re.compile(rf"[\"']({moved_alt})[\"']")
    path_mention = re.compile(r"context_compressor\.py")
    word = re.compile(rf"\b({moved_alt})\b")
    hits: dict[str, list[str]] = {"import": [], "dotted": [], "alias_attr": [], "quoted_with_facade": [], "doc_path_mention": []}
    for rel in files:
        p = head / rel
        if not p.is_file() or rel == FACADE or rel == SIBLING:
            continue
        try:
            src = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "context_compressor" not in src:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            if dotted.search(line):
                hits["dotted"].append(f"{rel}:{i}")
            if "context_compressor" in line and quoted.search(line):
                hits["quoted_with_facade"].append(f"{rel}:{i}")
            if not rel.endswith(".py") and path_mention.search(line) and word.search(line):
                hits["doc_path_mention"].append(f"{rel}:{i}")
        if rel.endswith(".py"):
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.module == FACADE_MOD and n.level == 0:
                    bad = [a.name for a in n.names if a.name in MOVED or a.name == "*"]
                    if bad:
                        hits["import"].append(f"{rel}:{n.lineno}:{','.join(bad)}")
                elif isinstance(n, ast.Import):
                    for a in n.names:
                        if a.name == FACADE_MOD:
                            alias = a.asname or a.name
                            if re.search(rf"\b{re.escape(alias)}\.({moved_alt})\b", src):
                                hits["alias_attr"].append(f"{rel}:{n.lineno}:{alias}")
                elif isinstance(n, ast.ImportFrom) and n.module == "agent" and any(a.name == "context_compressor" for a in n.names):
                    alias = next(a.asname or a.name for a in n.names if a.name == "context_compressor")
                    if re.search(rf"\b{re.escape(alias)}\.({moved_alt})\b", src):
                        hits["alias_attr"].append(f"{rel}:{n.lineno}:{alias}")
    total = sum(len(v) for v in hits.values())
    return {"result": "PASS" if total == 0 else "FAIL", "references": total, "hits": hits}


def gate_native_coupling(base: Path, head: Path, head_src: str) -> dict:
    nb = (base / "agent/native_compaction.py").read_bytes()
    nh = (head / "agent/native_compaction.py").read_bytes()
    defined = "is_compaction_summary_message" in _top(ast.parse(head_src))
    uses = "is_compaction_summary_message" in nh.decode("utf-8")
    ok = nb == nh and defined
    return {"result": "PASS" if ok else "FAIL", "native_compaction_identical": nb == nh,
            "facade_defines_is_compaction_summary_message": defined, "native_compaction_references_it": uses}


_PROBE = r"""
import socket, sys, json
_real = socket.socket.connect
def _guard(self, addr):
    host = addr[0] if isinstance(addr, tuple) else addr
    if host not in ("127.0.0.1", "::1", "localhost") and not str(host).startswith("/"):
        raise OSError(f"egress blocked by probe guard: {addr!r}")
    return _real(self, addr)
socket.socket.connect = _guard
import importlib
mod = sys.argv[1]
importlib.import_module(mod)
print(json.dumps({"module": mod, "facade_loaded": "agent.context_compressor" in sys.modules}))
"""


def gate_imports(head: Path, python: str) -> dict:
    results = []
    with tempfile.TemporaryDirectory(prefix="cme-probe-") as tmp:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": tmp,
            "HERMES_HOME": os.path.join(tmp, ".hermes"),
            "PYTHONPATH": str(head),
            "PYTHONDONTWRITEBYTECODE": "1",
            "LANG": "C.UTF-8",
        }
        os.makedirs(env["HERMES_HOME"])
        for mod in (SIBLING_MOD, FACADE_MOD, "agent.native_compaction", "agent.chat_completion_helpers", "agent.turn_request_assembly"):
            p = subprocess.run([python, "-c", _PROBE, mod], cwd=str(head), env=env, capture_output=True, text=True, timeout=300)
            line = (p.stdout.strip().splitlines() or [""])[-1]
            try:
                info = json.loads(line)
            except json.JSONDecodeError:
                info = {"module": mod}
            info["rc"] = p.returncode
            if p.returncode:
                info["stderr_tail"] = p.stderr.strip().splitlines()[-3:]
            results.append(info)
    ok = all(r["rc"] == 0 for r in results)
    return {"result": "PASS" if ok else "FAIL", "probes": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path)
    ap.add_argument("head", type=Path)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    base_src = (a.base / FACADE).read_text(encoding="utf-8")
    head_src = (a.head / FACADE).read_text(encoding="utf-8")
    head_sib = (a.head / SIBLING).read_text(encoding="utf-8")
    gates = {
        "verbatim": gate_verbatim(base_src, head_sib),
        "facade_rest": gate_facade_rest(base_src, head_src),
        "no_shim": gate_no_shim(head_src, head_sib),
        "old_path_zero": gate_old_path_zero(a.head),
        "native_coupling": gate_native_coupling(a.base, a.head, head_src),
        "imports": gate_imports(a.head, a.python),
    }
    sizes = {
        "facade_lines_base": len(base_src.splitlines()),
        "facade_lines_head": len(head_src.splitlines()),
        "sibling_lines_head": len(head_sib.splitlines()),
    }
    overall = "PASS" if all(g["result"] == "PASS" for g in gates.values()) else "FAIL"
    report = {"overall": overall, "gates": gates, "sizes": sizes}
    text = json.dumps(report, indent=2)
    if a.json:
        a.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
