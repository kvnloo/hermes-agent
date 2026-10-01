"""Seam coverage for the wire test (T1, $0): which production lines of the fix the two scenarios
actually execute. The venv has no ``coverage`` package, so this is a minimal line tracer
(``sys.settrace`` + ``threading.settrace``) restricted to the files a diff touches.

It runs tests/e2e/core/history/test_tool_result_projection_wire.py in-process under the same
isolation as f04_probe.py (cleared environment, fresh HOME/HERMES_HOME, loopback-only socket guard),
then maps the executed lines onto every hunk of the given diff: added lines, executable added lines
(from the compiled code objects' line tables), executed added lines. For a new module (one hunk) it
also lists each top-level function / method and whether any of its lines ran.

Usage: env -i PATH=/usr/bin:/bin PYTHONHASHSEED=0 <venv python> seam_trace.py <repo> <out.json> <diff>
"""

import ast
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
from collections import defaultdict
from pathlib import Path

REPO, OUT, DIFF = sys.argv[1], sys.argv[2], sys.argv[3]
SCRATCH = os.environ.get("F04_SCRATCH") or "/tmp"
sys.dont_write_bytecode = True
sandbox = tempfile.mkdtemp(prefix="seam-", dir=SCRATCH)
os.environ.clear()
os.environ.update(HOME=sandbox + "/home", HERMES_HOME=sandbox + "/hermes", TMPDIR=sandbox + "/tmp",
                  PATH="/usr/bin:/bin", TZ="UTC", LANG="C.UTF-8", PYTHONHASHSEED="0",
                  PYTHONDONTWRITEBYTECODE="1", HERMES_DISABLE_MODEL_METADATA_FETCH="1")
for d in ("home", "hermes", "tmp"):
    Path(sandbox, d).mkdir()
os.chdir(REPO)
sys.path.insert(0, REPO)

_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_connect, _gai = socket.socket.connect, socket.getaddrinfo
blocked: list = []


def loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in _LOOPBACK:
        blocked.append(f"connect {address!r}")
        raise RuntimeError("seam trace blocks non-loopback network")
    return _connect(self, address)


def loopback_getaddrinfo(host, *args, **kwargs):
    if host not in _LOOPBACK and host is not None:
        blocked.append(f"getaddrinfo {host!r}")
        raise socket.gaierror("seam trace blocks non-loopback name resolution")
    return _gai(host, *args, **kwargs)


socket.socket.connect, socket.getaddrinfo = loopback_only, loopback_getaddrinfo

# ---- parse the diff: per file, per hunk, the added line numbers in the new file -------------------
hunks = []
current = None
for line in Path(DIFF).read_text(encoding="utf-8").splitlines():
    if line.startswith("+++ "):
        current = line[4:].split("/", 1)[1] if line[4:] != "/dev/null" else None
        continue
    m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@(.*)$", line)
    if m and current:
        hunks.append({"file": current, "new_start": int(m[1]), "context": m[3].strip()[:80], "added": []})
        lineno = int(m[1])
        continue
    if hunks and current and not line.startswith("diff ") and not line.startswith("index ") and not line.startswith("--- "):
        if line.startswith("+"):
            hunks[-1]["added"].append(lineno)
            lineno += 1
        elif line.startswith(" "):
            lineno += 1
py_files = sorted({h["file"] for h in hunks if h["file"].endswith(".py") and not h["file"].startswith("tests/")})
targets = {str(Path(REPO, f).resolve()): f for f in py_files}

executed = defaultdict(set)


def tracer(frame, event, arg):
    path = targets.get(frame.f_code.co_filename)
    if path is None:
        return None

    def local(frame, event, arg):
        if event == "line":
            executed[path].add(frame.f_lineno)
        return local

    executed[path].add(frame.f_code.co_firstlineno)
    return local


import pytest  # noqa: E402


class Outcomes:
    def __init__(self):
        self.results = {}

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            self.results[report.nodeid.split("::")[-1]] = report.outcome


plugin = Outcomes()
test_file = str(Path(REPO, "tests/e2e/core/history/test_tool_result_projection_wire.py"))
t0 = time.monotonic()
threading.settrace(tracer)
sys.settrace(tracer)
rc = pytest.main([test_file, "-q", "-p", "no:cacheprovider", "-p", "no:randomly"], plugins=[plugin])
sys.settrace(None)
threading.settrace(None)
wall = time.monotonic() - t0


def executable_lines(path: str) -> set:
    lines = set()
    stack = [compile(Path(REPO, path).read_text(encoding="utf-8"), path, "exec")]
    while stack:
        code = stack.pop()
        lines.update(ln for _, _, ln in code.co_lines() if ln is not None)
        stack.extend(c for c in code.co_consts if hasattr(c, "co_lines"))
    return lines


def functions(path: str):
    tree = ast.parse(Path(REPO, path).read_text(encoding="utf-8"))
    out = []
    for node in tree.body:
        nodes = [node] + ([n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                          if isinstance(node, ast.ClassDef) else [])
        for n in nodes:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = n.name if n is node else f"{node.name}.{n.name}"
                body = set(range(n.body[0].lineno, n.end_lineno + 1))
                out.append({"name": qual, "lines": [n.lineno, n.end_lineno],
                            "body_executed": bool(body & executed.get(path, set()))})
    return out


report_hunks = []
for h in hunks:
    entry = {"file": h["file"], "new_start": h["new_start"], "context": h["context"], "added_lines": len(h["added"])}
    if h["file"] in py_files:
        exe = executable_lines(h["file"]) & set(h["added"])
        ran = exe & executed.get(h["file"], set())
        entry.update(executable_added=len(exe), executed_added=len(ran),
                     executed=bool(ran), not_executed_lines=sorted(exe - ran)[:60])
        if len(h["added"]) > 200:  # a new module: per-function view
            entry["functions"] = functions(h["file"])
    else:
        entry.update(executable_added=0, executed_added=0, executed=None, note="not Python (docs/config example)")
    report_hunks.append(entry)

out = {"label": "OBSERVED (line tracer over the wire test)", "python": sys.version.split()[0],
       "pytest_rc": int(rc), "outcomes": plugin.results, "hunks": report_hunks,
       "egress_blocked": blocked, "wall_s": round(wall, 2)}
Path(OUT).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({"outcomes": plugin.results, "hunks": [
    {k: h[k] for k in ("file", "new_start", "added_lines", "executable_added", "executed_added")} for h in report_hunks]},
    indent=1))
