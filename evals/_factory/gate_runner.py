#!/usr/bin/env python3
"""Promotion-gate runner: RED on base, GREEN on head, a negative control and adjacent tests, in guarded cells.

    python -m evals._factory.gate_runner run --work-order wo.json --repo <git dir> --scratch <dir> --out receipt.json
    python -m evals._factory.gate_runner validate receipt.json [--max-age-hours 24]

Downstream factory tooling (kvnloo/hermes-agent#322), never an upstream PR on its own. One invocation
executes exactly one work order that was already claimed through the oss-factory envelopes. The
runner has no queue, loop, timer or GitHub access, and it never selects or claims work.

What one run does:

1. Checks the ``work_order`` envelope and the sha256 of the TOML spec it names, then lints the spec:
   full-SHA pins, at least one RED marker, a sabotage mode, and no denylisted test files (updaters,
   re-exec, live suites).
2. Materializes two detached worktrees from ``--repo``: base (``base.pin``) and head
   (``head.commit``, or ``git merge-tree`` of it onto base). A conflict stops the run as BLOCKED.
3. Runs every probe as a fresh process (a "cell") with an empty environment, its own HOME and
   HERMES_HOME under the run directory, and an in-process guard (``sitecustomize``) that allows
   loopback connects only, refuses name lookups of other hosts, refuses opens under the live Hermes
   home (only the interpreter's own prefix is readable, never writable), and refuses an exec whose
   argv, or the text a shell is handed (``shell=True``, ``bash -c``, ``os.system``), has ``hermes``
   or ``hermes_cli.main`` as a word (limits below). The cell PATH is a ``python``/``python3`` shim
   plus ``/usr/bin:/bin``, so the interpreter's bin directory and its ``hermes*`` console scripts
   are not on it.
   ``scripts/run_tests.sh`` drops PYTHONPATH, so pytest cells carry the guard through that script's
   own ``$HOME/.hermes/pytest_live_guard.py`` plugin hook; the HOME is the cell's scratch home, so
   nothing from the real home is loaded. A canary cell proves the guard blocks each class (the argv,
   ``shell=True``, ``bash -c`` and PATH forms of a hermes exec included) before any probe runs. Every
   blocked attempt is logged and makes its cell INFRA, and so does a pytest cell whose guard never
   logged from inside pytest. Any INFRA cell (the Relay pin cell included; the canary's expected
   blocks aside) makes the whole run INFRA, never KEEP.
4. Asserts all four columns: RED on base (head's tests injected, every rep fails with every marker
   matched), GREEN on head (every rep passes; tests taken from a later ``inject.tests_from`` commit,
   such as a reviewer's, are injected into head too), a negative control (each non-test hunk reverted alone,
   or a recorded sabotage patch; at least one must re-RED, the others are listed as unpinned), and
   ADJACENT (no adjacent file that passes on base fails on head). The recorded ownership result is
   a fifth gate: an open external owner forces the salvage or support route.
5. Writes an ``xf.receipt.v1`` receipt: a superset of the verified-oss-loop SPEC section 4 evidence
   receipt with OBSERVED labels, pinned SHAs, Relay pins (resolved only from the head arm's own
   ``agent/relay_runtime.py``) and no absolute paths, and validates it (the validator refuses any
   absolute path). ``outcome.verified_success`` stays null: a self-run is never independent
   verification.

Not a sandbox: the guard is in-process and Python-level. It sees only what a Python process does: a
shell script file that runs ``hermes``, a child started with a cleared environment (no guard on its
PYTHONPATH), C-extension sockets and ``ctypes`` are not inspected. The exec check is a word match,
not a shell parser: shell text is split on metacharacters, so quoting (``her''mes``), globbing
(``herme?``), backslash escapes and variable expansion that builds the name (``${X}mes``) all run
``hermes`` unblocked, given its absolute path (it is not on the cell PATH). Code that imports
``hermes_cli`` (``python -c 'import hermes_cli.main'``) and the other console scripts
(``hermes-agent``, ``hermes-acp``, by absolute path) are not refused either. Run it inside a kernel
sandbox (bwrap with ``--unshare-net``) for a hard boundary. Lifts the loopback-only connect guard and
``os.environ`` reset from ``evals/provider_fallback/probe_104260.py``.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import ipaddress
import json
import os
import pwd
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "xf.receipt.v1"
LABELS = {"OBSERVED", "MODELED", "PRIOR", "NOT_MEASURED"}
VERDICTS = {"KEEP", "PARTIAL", "DISCARD", "FLAKY", "INFRA", "BLOCKED"}
FOUR_COLUMNS = ("red", "green", "sabotage", "adjacent")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TEST_PATH_RE = re.compile(r"(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.py$|\.test\.[cm]?[jt]sx?$")
DENY_GLOBS = ("tests/e2e/core/upgrade/*", "tests/e2e/core/windows_update/*", "evals/update_*",
              "tests/computer_use/live_*", "*tool_search_livetest*")
DENY_CALL = re.compile(r"\bos\.exec\w*\s*\(|\bexecvpe?\s*\(|\b_reexec\w*\s*\(")  # a test that re-execs (self-update paths)
GUARD_MISSING = "factory cell guard is not active"
INFO_EVENTS = {"open-write-interpreter", "pytest-guard-active"}  # logged by the guard, not blocked attempts
_FILE_LINE = re.compile(r"\]\s+([✓✗])\s+(\S+?)\s+\(")
_PRIVATE = re.compile(r"/home/|/Users/|[A-Za-z]:\\\\Users|[\w.+-]+@[\w-]+\.[\w.]+|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN")
_ABS_PATH = re.compile(r"""(?:^|[\s"'(\[=:,<])/[\w.~-]""")  # a POSIX absolute path; URLs ('://') do not match
SHELLS = ("ash", "bash", "busybox", "dash", "ksh", "mksh", "sh", "zsh")
SHELL_META = " \t\n;&|()<>`$'\"{}=\\"  # split shell text into words on these, so 'x&&hermes' still names hermes

GUARD = '''\
"""Cell guard written by evals/_factory/gate_runner.py: loopback-only network, no live-home access, no hermes exec."""
import errno, ipaddress, json, os, socket, sys

FACTORY_GUARD_ACTIVE = True
_DENY = {deny!r}
_ALLOW = {allow!r}
_SHELLS = {shells!r}
_WORDS = str.maketrans(dict.fromkeys({meta!r}, " "))
_WRITE = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_fd = os.open({log!r}, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)


def _record(event, detail):
    os.write(_fd, (json.dumps({{"event": event, "detail": str(detail)[:300], "pid": os.getpid()}}) + "\\n").encode())


def _loopback(host):
    if host is None:
        return True
    host = os.fsdecode(host) if isinstance(host, bytes) else str(host)
    if host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    mapped = getattr(ip, "ipv4_mapped", None)
    return ip.is_loopback or ip.is_unspecified or bool(mapped and mapped.is_loopback)


def _under(path, roots):
    return any(path == r or path.startswith(r + os.sep) for r in roots)


def _words(text):
    return text.translate(_WORDS).split()


def _tokens(args):
    out = []
    for a in args:
        if isinstance(a, (str, bytes, os.PathLike)):  # os.system's command line, or a program path
            out.extend(_words(os.fsdecode(a)))
        elif isinstance(a, (list, tuple)):
            argv = [os.fsdecode(x) for x in a if isinstance(x, (str, bytes, os.PathLike))]
            shell = next((i for i, x in enumerate(argv) if os.path.basename(x) in _SHELLS), len(argv))
            out.extend(argv[:shell + 1])
            for x in argv[shell + 1:]:  # what a shell is handed (shell=True, bash -c, env sh -c) is shell text
                out.extend(_words(x))
    return out


def _forbidden_exec(tokens):
    for t in tokens:
        if os.path.basename(t) in ("hermes", "hermes.exe") or t.startswith("hermes_cli.main"):
            return True
        if os.sep in t:
            real = os.path.realpath(t)
            if _under(real, _DENY) and not _under(real, _ALLOW):
                return True
    return False


def _hook(event, args):
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple) and address and isinstance(address[0], (str, bytes)) and not _loopback(address[0]):
            _record(event, address)
            raise OSError(errno.ENETUNREACH, "factory guard: non-loopback connect blocked")
    elif event in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex", "socket.gethostbyaddr"):
        if not _loopback(args[0]):
            _record(event, args[0])
            raise socket.gaierror(socket.EAI_NONAME, "factory guard: name lookup blocked")
    elif event == "open":
        path = args[0]
        if isinstance(path, (str, bytes)):
            path = os.path.abspath(os.fsdecode(path))
            if _under(path, _DENY):
                flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
                if not _under(path, _ALLOW):
                    _record(event, path)
                    raise PermissionError(errno.EACCES, "factory guard: live Hermes home is off limits", path)
                if flags & _WRITE:
                    _record("open-write-interpreter", path)
                    raise PermissionError(errno.EACCES, "factory guard: interpreter prefix is read-only", path)
    elif event in ("subprocess.Popen", "os.exec", "os.posix_spawn", "os.spawn", "os.system"):
        if _forbidden_exec(_tokens(args[:2] if event != "os.spawn" else args[1:3])):
            _record(event, args[:2])
            raise PermissionError(errno.EPERM, "factory guard: exec of a Hermes entrypoint blocked")


sys.addaudithook(_hook)
'''

PYTEST_PLUGIN = f'''\
"""Fails a pytest run closed when the factory cell guard did not load, and logs that it did (see sitecustomize.py)."""
import os
import sys


def pytest_configure(config):
    guard = sys.modules.get("sitecustomize")
    if not getattr(guard, "FACTORY_GUARD_ACTIVE", False):
        raise RuntimeError("{GUARD_MISSING}")
    guard._record("pytest-guard-active", os.getpid())
'''

CANARY = r'''
import json, os, shutil, socket, subprocess, sys
cfg = json.loads(sys.argv[1])
out = {}
srv = socket.socket(); srv.bind(("0.0.0.0", 0)); srv.listen(4); port = srv.getsockname()[1]

def attempt(fn):
    try:
        fn(); return "allowed"
    except OSError as e:
        return "blocked" if "factory guard" in str(e) else "error:" + type(e).__name__

def connect(host):
    s = socket.socket(); s.settimeout(2)
    try:
        s.connect((host, port))
    finally:
        s.close()

out["loopback_connect"] = attempt(lambda: connect("127.0.0.1"))
out["nonloopback_connect"] = attempt(lambda: connect(cfg["target"]))
out["name_lookup"] = attempt(lambda: socket.getaddrinfo(cfg["target"], 443))
out["live_home_open"] = attempt(lambda: open(cfg["decoy_file"]).read())
decoy, decoy_dir = cfg["decoy_hermes"], os.path.dirname(cfg["decoy_hermes"])
out["hermes_exec"] = attempt(lambda: subprocess.run([decoy, "update"], timeout=10))
out["hermes_exec_shell"] = attempt(lambda: subprocess.run(decoy + " update", shell=True, timeout=10))
out["hermes_exec_bash_c"] = attempt(lambda: subprocess.run(["bash", "-c", "true && " + decoy + " update"], timeout=10))
out["hermes_exec_path"] = attempt(lambda: subprocess.run("hermes update", shell=True, timeout=10,
                                                         env={**os.environ, "PATH": decoy_dir + os.pathsep + os.environ["PATH"]}))
out["hermes_exec_ran"] = os.path.exists(os.path.join(decoy_dir, "EXECUTED"))
out["hermes_on_path"] = shutil.which("hermes")
out["home"] = os.path.realpath(os.environ["HOME"])
out["hermes_home"] = os.path.realpath(os.environ["HERMES_HOME"])
out["python"] = sys.version.split()[0]
out["guard"] = bool(getattr(sys.modules.get("sitecustomize"), "FACTORY_GUARD_ACTIVE", False))
print("CANARY " + json.dumps(out))
'''
CANARY_EXPECT = {"loopback_connect": "allowed", "nonloopback_connect": "blocked", "name_lookup": "blocked",
                 "live_home_open": "blocked", "hermes_exec": "blocked", "hermes_exec_shell": "blocked",
                 "hermes_exec_bash_c": "blocked", "hermes_exec_path": "blocked", "hermes_exec_ran": False,
                 "hermes_on_path": None, "guard": True}

RELAY_PIN = r'''
import hashlib, importlib.util, json, os, re, sys
from pathlib import Path
src = Path("agent/relay_runtime.py")
m = re.search(r'RUNTIME_SCHEMA_VERSION\s*=\s*"([^"]+)"', src.read_text(encoding="utf-8")) if src.exists() else None
tomls = sorted(Path(os.environ["HERMES_HOME"]).rglob("*plugins*.toml"))
out = {"present": importlib.util.find_spec("nemo_relay") is not None, "runtime_schema": m.group(1) if m else None,
       "plugins_toml_sha256": hashlib.sha256(b"".join(p.read_bytes() for p in tomls)).hexdigest() if tomls else None,
       "config_paths": []}
ROOTS = [(os.getcwd(), "."), (os.environ["HERMES_HOME"], "$HERMES_HOME"), (os.environ["HOME"], "~"), (sys.prefix, "<python>")]
ABS = re.compile(r"""(^|[\s"'(\[=:,<])(/[^\s"'(),\]]+)""")

def rel(text):  # receipts never carry absolute local paths: known roots get a tag, any other keeps its basename
    for root, tag in ROOTS:
        text = text.replace(root, tag)
    return ABS.sub(lambda m: m.group(1) + "<abs>/" + os.path.basename(m.group(2)), text)

if out["present"] and src.exists():  # only the arm's own runtime, never one an editable install resolves elsewhere
    try:
        import nemo_relay
        out["version"] = getattr(nemo_relay, "__version__", None)
        sys.path.insert(0, os.getcwd())
        from agent.relay_runtime import resolve_plugin_sources
        out["config_paths"] = [rel(str(p)) for p in resolve_plugin_sources().config_paths]
    except Exception as exc:  # an installed Relay this tree cannot drive is a pin, not a crash
        out["error"] = rel(type(exc).__name__ + ": " + str(exc))[:200]
print("RELAY_PIN " + json.dumps(out))
'''


class Refused(Exception):
    """The work order or spec is not runnable; nothing was executed."""


def _git(repo, *args, input=None, check=True):
    """stdout (stripped) when check, else the CompletedProcess."""
    p = subprocess.run(["git", "-C", str(repo), *args], input=input, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} failed: {p.stderr.strip()[:300]}")
    return p.stdout.strip() if check else p


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _real_live_paths(extra=()) -> list[str]:
    """The live Hermes home of the invoking user, from the password database, not $HOME."""
    paths = set()
    for raw in (os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".hermes"), *extra):
        paths.update({os.path.abspath(raw), os.path.realpath(raw)})
    return sorted(paths)


def _under(path: str, roots) -> bool:
    return any(path == r or path.startswith(r.rstrip(os.sep) + os.sep) for r in roots)


def load_work_order(path) -> tuple[dict, dict, str]:
    wo = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [k for k in ("id", "kind", "project", "from", "to", "status", "spec", "spec_sha256") if k not in wo]
    if missing or not (wo.get("civ") or {}).get("city_id"):
        raise Refused(f"work order is missing {missing or ['civ.city_id']}")
    if wo["kind"] != "work_order" or wo["project"] != "hermes-agent":
        raise Refused(f"not a hermes-agent work_order: kind={wo['kind']!r} project={wo['project']!r}")
    spec_path = (Path(path).parent / wo["spec"]).resolve()
    raw = spec_path.read_bytes()
    if _sha256(raw) != wo["spec_sha256"]:
        raise Refused("spec sha256 does not match the work order")
    return wo, tomllib.loads(raw.decode("utf-8")), _sha256(raw)


def lint_spec(spec: dict) -> list[str]:
    problems = []
    if spec.get("xf_spec") != 1 or spec.get("kind") != "redgreen" or not spec.get("id"):
        problems.append("need xf_spec = 1, kind = 'redgreen' and an id")
    for key, sha in (("base.pin", spec.get("base", {}).get("pin")), ("head.commit", spec.get("head", {}).get("commit"))):
        if not isinstance(sha, str) or not SHA_RE.match(sha):
            problems.append(f"{key} must be a full 40-hex SHA")
    probe, oracle = spec.get("probe", {}), spec.get("oracle", {})
    reps = probe.get("reps", 3)
    if type(reps) is not int or reps < 1:
        problems.append("probe.reps must be a positive integer")
    if probe.get("kind") not in ("pytest", "script") or not probe.get("files"):
        problems.append("probe.kind must be pytest or script, with probe.files")
    if not oracle.get("red_markers") or not all(isinstance(m, str) and m for m in oracle["red_markers"]):
        problems.append("oracle.red_markers must list the failure text RED has to show")
    sabotage = oracle.get("sabotage", "per_hunk")
    if sabotage != "per_hunk" and not oracle.get("sabotage_sha256"):
        problems.append("a recorded sabotage patch needs oracle.sabotage_sha256")
    for f in [*probe.get("files", []), *oracle.get("adjacent", [])]:
        if any(fnmatch.fnmatch(f, g) for g in DENY_GLOBS):
            problems.append(f"{f} is denylisted (updater, re-exec or live suite)")
    return problems


@dataclass
class Run:
    dir: Path
    python: str
    deny: list
    allow: list
    decoy_file: Path
    decoy_hermes: Path


def new_run(scratch, run_id: str, python: str, extra_deny=()) -> Run:
    deny = _real_live_paths(extra_deny)
    root = Path(scratch).resolve()
    if _under(str(root), deny):
        raise Refused("scratch must not live under the live Hermes home")
    d = root / run_id
    d.mkdir(parents=True, exist_ok=False)
    decoy = d / "decoy-live-home"
    decoy.mkdir()
    (decoy / "state.db").write_text("decoy\n", encoding="utf-8")
    bin_dir = d / "decoy-bin"
    bin_dir.mkdir()
    hermes = bin_dir / "hermes"
    hermes.write_text('#!/bin/sh\ntouch "$(dirname "$0")/EXECUTED"\n', encoding="utf-8")
    hermes.chmod(0o755)
    shim = d / "bin"  # the cell PATH: python, never the interpreter's bin dir with its hermes console scripts
    shim.mkdir()
    for name in ("python", "python3"):
        (shim / name).write_text(f'#!/bin/sh\nexec {shlex.quote(python)} "$@"\n', encoding="utf-8")
        (shim / name).chmod(0o755)
    prefix = subprocess.run([python, "-c", "import sys; print(sys.prefix)"], capture_output=True, text=True,
                            env={"PATH": "/usr/bin:/bin"}, timeout=60).stdout.strip()
    allow = sorted({os.path.abspath(prefix), os.path.realpath(prefix)}) if prefix else []
    return Run(d, python, [*deny, str(decoy)], allow, decoy / "state.db", hermes)


def run_cell(run: Run, name: str, argv: list, cwd, timeout: int = 900, pytest_guard: bool = False) -> dict:
    """Run one probe in a fresh process with a scratch HOME/HERMES_HOME, an empty env and the guard.

    ``pytest_guard``: the cell runs pytest, so the guard must also prove it reached a pytest process.
    """
    cell = run.dir / "cells" / name
    cell.mkdir(parents=True, exist_ok=False)
    home, tmp, log = cell / "home", cell / "tmp", cell / "guard.jsonl"
    hermes_home = home / ".hermes"
    hermes_home.mkdir(parents=True)
    tmp.mkdir()
    real_home = os.path.realpath(hermes_home)
    if not _under(real_home, [str(run.dir.resolve())]) or _under(real_home, run.deny):
        raise Refused(f"cell HERMES_HOME escaped the run directory: {real_home}")
    (hermes_home / "sitecustomize.py").write_text(
        GUARD.format(deny=run.deny, allow=run.allow, log=str(log), shells=SHELLS, meta=SHELL_META), encoding="utf-8")
    (hermes_home / "pytest_live_guard.py").write_text(PYTEST_PLUGIN, encoding="utf-8")
    env = {"HOME": str(home), "HERMES_HOME": str(hermes_home), "TMPDIR": str(tmp),
           "PYTHONPATH": f"{hermes_home}{os.pathsep}{os.path.abspath(cwd)}",
           "PATH": f"{run.dir / 'bin'}:/usr/bin:/bin", "HERMES_PYTHON": run.python,
           "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC",
           "HERMES_TEST_FILE_RETRIES": "0"}
    t0 = time.monotonic()
    proc = subprocess.Popen(["nice", "-n", "10", *argv], cwd=str(cwd), env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                            start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, rc = (proc.communicate()[0] or "") + "\nTIMEOUT", 124
    (cell / "output.txt").write_text(out, encoding="utf-8")
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()] if log.exists() else []
    blocked = [e for e in events if e["event"] not in INFO_EVENTS]
    guard_reached_pytest = any(e["event"] == "pytest-guard-active" for e in events)
    infra = rc == 124 or GUARD_MISSING in out or bool(blocked) or (pytest_guard and not guard_reached_pytest)
    return {"name": name, "rc": rc, "wall_s": round(time.monotonic() - t0, 2), "blocked": blocked, "infra": infra,
            "interpreter_writes_refused": sum(e["event"] == "open-write-interpreter" for e in events),
            "output": out, "output_sha256": _sha256(out.encode("utf-8"))}


def _local_nonloopback_ip() -> str:
    """A local address that is not loopback; a UDP connect only picks a route, it sends nothing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))
        ip = s.getsockname()[0]
    except OSError:
        return "192.0.2.1"  # no route at all, so nothing can leave either
    finally:
        s.close()
    return "192.0.2.1" if ipaddress.ip_address(ip).is_loopback else ip


def canary(run: Run) -> dict:
    """Prove inside a real cell that each guard class blocks and loopback still works."""
    cfg = {"target": _local_nonloopback_ip(), "decoy_file": str(run.decoy_file), "decoy_hermes": str(run.decoy_hermes)}
    cell = run_cell(run, "canary", [run.python, "-c", CANARY, json.dumps(cfg)], run.dir, timeout=60)
    line = next((ln for ln in cell["output"].splitlines() if ln.startswith("CANARY ")), None)
    seen = json.loads(line[7:]) if line else {}
    checks = {k: seen.get(k) == v for k, v in CANARY_EXPECT.items()}
    run_dir = str(run.dir.resolve())
    checks["home_isolated"] = bool(seen) and _under(seen["home"], [run_dir]) and _under(seen["hermes_home"], [run_dir])
    events = sorted({b["event"] for b in cell["blocked"]})
    checks["logged"] = {"socket.connect", "socket.getaddrinfo", "open", "subprocess.Popen"} <= set(events)
    return {"passed": all(checks.values()), "checks": checks, "blocked_events": events,
            "python": seen.get("python"), "rc": cell["rc"]}


def _probe_argv(spec: dict, files: list, python: str) -> list:
    probe = spec["probe"]
    if probe["kind"] == "pytest":
        return ["bash", "scripts/run_tests.sh", "-j", str(probe.get("jobs", 2)), *files, "-q",
                "-m", "not live and not integration"]
    return [python, *(f.replace("{repo}", ".") for f in files)]  # script: probe.files is the argv after the interpreter


def _pytest_status(output: str) -> dict:
    return {f: mark == "✓" for mark, f in _FILE_LINE.findall(output)}


def _hunks(diff: str) -> list:
    out = []
    for block in re.split(r"(?m)^(?=diff --git )", diff):
        if not block.startswith("diff --git"):
            continue
        header, *hunks = re.split(r"(?m)^(?=@@ )", block)
        path = re.search(r"(?m)^diff --git a/(\S+) b/", header).group(1)
        if not hunks or "new file mode" in header or "deleted file mode" in header:
            out.append((f"{path}@whole-file", block))
            continue
        out.extend((f"{path}{h.splitlines()[0].split('@@')[1].rstrip()}", header + h) for h in hunks)
    return out


def _gate(result: str, **detail) -> dict:
    return {"result": result, **detail}


def _reps_gate(cells: list, want_fail: bool, markers=()) -> dict:
    ok = [((c["rc"] != 0) if want_fail else (c["rc"] == 0)) and all(m in c["output"] for m in markers) for c in cells]
    agree = f"{sum(ok)}/{len(ok)}"
    if all(ok):
        result = _gate("PASS", reps_agree=agree)
    elif any(ok):
        result = _gate("FLAKY", reps_agree=agree)
    elif want_fail and all(c["rc"] != 0 for c in cells):
        result = _gate("FAIL", reps_agree=agree, reason="failed, but not with the expected marker",
                       missing_markers=sorted({m for c in cells for m in markers if m not in c["output"]}))
    else:
        result = _gate("FAIL", reps_agree=agree, reason="no_repro_on_base" if want_fail else "not_fixed")
    if any(c["infra"] for c in cells):  # an untrustworthy cell never counts, but what it showed stays on record
        return _gate("INFRA", reason="guard blocked an attempt, never reached pytest, or the cell timed out", underlying=result)
    return result


def run_gate(work_order, repo, scratch, python: str, extra_deny=()) -> dict:
    t0 = time.monotonic()
    wo, spec, spec_sha = load_work_order(work_order)
    problems = lint_spec(spec)
    if problems:
        raise Refused("; ".join(problems))
    repo = Path(repo).resolve()
    base = _git(repo, "rev-parse", "--verify", spec["base"]["pin"] + "^{commit}")
    head = _git(repo, "rev-parse", "--verify", spec["head"]["commit"] + "^{commit}")
    tests_from = _git(repo, "rev-parse", "--verify", spec.get("inject", {}).get("tests_from", head) + "^{commit}")
    stamp = datetime.now(timezone.utc).strftime("r%Y%m%dT%H%M%SZ")
    run = new_run(scratch, f"{spec['id']}-{stamp}", python, extra_deny)
    gates, cells, worktrees = {}, [], []
    arms = {"base": {"commit": base, "tree": _git(repo, "rev-parse", base + "^{tree}")}}
    probe, oracle = spec["probe"], spec["oracle"]
    reps, timeout = int(probe.get("reps", 3)), int(probe.get("timeout_s", 900))
    files, adjacent = list(probe["files"]), list(oracle.get("adjacent", []))
    receipt_tests, changed, unpinned, relay = {}, [], [], {}

    def cell(name, argv, cwd):
        c = run_cell(run, name, argv, cwd, timeout, pytest_guard=probe["kind"] == "pytest")
        cells.append(c)
        return c

    def worktree(name, commit):
        path = run.dir / "arms" / name
        _git(repo, "worktree", "add", "--detach", "-q", str(path), commit)
        worktrees.append(path)
        return path

    try:
        head_arm = head
        if spec["head"].get("merge_onto_base"):
            merged = _git(repo, "merge-tree", "--write-tree", "--name-only", base, head, check=False)
            if merged.returncode != 0:
                gates["validity"] = _gate("FAIL", reason="conflicting", files=merged.stdout.split("\n\n")[0].splitlines()[1:])
            else:
                tree = merged.stdout.splitlines()[0]
                ident = {"GIT_AUTHOR_NAME": "gate-runner", "GIT_AUTHOR_EMAIL": "gate-runner@invalid",
                         "GIT_COMMITTER_NAME": "gate-runner", "GIT_COMMITTER_EMAIL": "gate-runner@invalid",
                         "GIT_AUTHOR_DATE": "@0 +0000", "GIT_COMMITTER_DATE": "@0 +0000",
                         "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/")}
                head_arm = subprocess.run(["git", "-C", str(repo), "commit-tree", tree, "-p", base, "-p", head, "-m", "gate-runner arm"],
                                          capture_output=True, text=True, env=ident, check=True).stdout.strip()
        arms["head"] = {"commit": head, "merge": "merge-tree" if head_arm != head else "direct", "arm_commit": head_arm,
                        "tree": _git(repo, "rev-parse", head_arm + "^{tree}")}
        if "validity" not in gates:
            changed = _git(repo, "diff", "--name-only", base, head_arm).splitlines()
            # A merged arm carries base's own newer edits, so its tests come from the arm, never the stale branch.
            source = head_arm if tests_from == head else tests_from
            inject_list = spec.get("inject", {}).get("files") or [
                f for f in _git(repo, "diff", "--name-only", "--diff-filter=AM", base, source).splitlines() if TEST_PATH_RE.search(f)]
            arms["base"]["inject"] = {"from": tests_from, "source_commit": source, "files": inject_list}
            denied = [f for f in [*files, *adjacent] for c in (base, tests_from)
                      if DENY_CALL.search(_git(repo, "show", f"{c}:{f}", check=False).stdout)]
            if not changed:
                gates["validity"] = _gate("FAIL", reason="empty_diff")
            elif not inject_list:
                gates["validity"] = _gate("FAIL", reason="no test files to inject into base")
            elif denied:
                gates["validity"] = _gate("FAIL", reason="selected file references exec/re-exec", files=sorted(set(denied)))
            else:
                gates["validity"] = _gate("PASS")
        if gates["validity"]["result"] != "PASS":
            verdict = "DISCARD" if gates["validity"]["reason"] == "empty_diff" else "BLOCKED"  # the rest say nothing about the patch
            return _receipt(wo, spec, spec_sha, run, arms, changed, gates, cells, receipt_tests, {}, relay, verdict, t0, None)

        safety_canary = canary(run)
        if not safety_canary["passed"]:
            gates["validity"] = _gate("INFRA", reason="guard canary failed")
            return _receipt(wo, spec, spec_sha, run, arms, changed, gates, cells, receipt_tests, safety_canary, relay, "INFRA", t0, None)

        base_wt, head_wt = worktree("base", base), worktree("head", head_arm)
        inject_files = arms["base"]["inject"]["files"]

        def inject(wt):
            _git(wt, "checkout", arms["base"]["inject"]["source_commit"], "--", *inject_files)

        # Tests taken from a later commit (a reviewer's) must also be what head is graded on.
        inject_head = arms["base"]["inject"]["source_commit"] != head_arm
        if inject_head:
            inject(head_wt)
        arms["head"]["inject"] = inject_files if inject_head else []
        pin = run_cell(run, "relay-pin", [python, "-c", RELAY_PIN], head_wt, timeout=120)
        cells.append(pin)  # it runs head code: its blocked attempts count like any probe's and taint the run
        line = next((ln for ln in pin["output"].splitlines() if ln.startswith("RELAY_PIN ")), None)
        relay = json.loads(line[10:]) if line else {"error": "relay pin probe failed"}

        def adjacent_cells(arm, wt):
            groups = [adj_files] if probe["kind"] == "pytest" else [[f] for f in adj_files]
            return [cell(f"adjacent-{arm}-{i}", _probe_argv(spec, g, python), wt) for i, g in enumerate(groups)]

        adj_files = [f for f in adjacent if (base_wt / f).exists() and (head_wt / f).exists()]
        inject(base_wt)
        red_cells = [cell(f"red-{i}", _probe_argv(spec, files, python), base_wt) for i in range(reps)]
        gates["red"] = _reps_gate(red_cells, want_fail=True, markers=oracle["red_markers"])
        green_cells = [cell(f"green-{i}", _probe_argv(spec, files, python), head_wt) for i in range(reps)]
        gates["green"] = _reps_gate(green_cells, want_fail=False, markers=oracle.get("green_markers", []))
        cmd = " ".join(shlex.quote(a) for a in _probe_argv(spec, files, "{python}"))
        receipt_tests["red"] = {"command": cmd, "arm": "base + injected tests", "expected_failure": oracle["red_markers"],
                                "observed": gates["red"].get("reps_agree")}
        receipt_tests["green"] = {"command": cmd, "arm": "head + injected tests" if inject_head else "head",
                                  "observed": gates["green"].get("reps_agree")}

        if gates["red"]["result"] == "PASS" and gates["green"]["result"] == "PASS":
            sabotage = oracle.get("sabotage", "per_hunk")
            if sabotage == "per_hunk":
                code = [f for f in changed if not TEST_PATH_RE.search(f)]
                diff = _git(repo, "diff", base, head_arm, "--", *code, check=False).stdout  # unstripped: hunks need their last newline
                variants = [(name, patch, True) for name, patch in _hunks(diff)] if code else []
            else:  # a recorded patch path is relative to the spec, like the work order's own spec path
                raw = ((Path(work_order).parent / wo["spec"]).resolve().parent / sabotage).read_bytes()
                if _sha256(raw) != oracle["sabotage_sha256"]:
                    raise Refused("sabotage patch sha256 does not match the spec")
                variants = [(Path(sabotage).name, raw.decode("utf-8"), False)]
            per = []
            for i, (name, patch, reverse) in enumerate(variants):
                applied = _git(head_wt, "apply", *(["-R"] if reverse else []), "-", input=patch, check=False)
                if applied.returncode != 0:
                    per.append({"hunk": name, "red_again": None, "reason": "patch did not apply"})
                    continue
                c = cell(f"sabotage-{i}", _probe_argv(spec, files, python), head_wt)
                per.append({"hunk": name, "red_again": None if c["infra"] else c["rc"] != 0})
                _git(head_wt, "reset", "-q", "--hard")
                _git(head_wt, "clean", "-fdq")
                if inject_head:
                    inject(head_wt)
            unpinned = [p["hunk"] for p in per if p["red_again"] is False]
            if any(p["red_again"] is None and p.get("reason") is None for p in per):
                gates["sabotage"] = _gate("INFRA", per_hunk=per)
            elif any(p["red_again"] for p in per):
                gates["sabotage"] = _gate("PASS", per_hunk=per, unpinned_hunks=unpinned)
            else:
                gates["sabotage"] = _gate("FAIL", per_hunk=per, reason="no sabotage re-REDs: the test does not pin the change")
            receipt_tests["sabotage"] = {"command": cmd, "mode": "per-hunk revert" if sabotage == "per_hunk" else "recorded patch",
                                         "expected_failure": "rc != 0", "observed": f"{sum(bool(p['red_again']) for p in per)}/{len(per)} re-RED"}
            if adj_files:
                _git(base_wt, "reset", "-q", "--hard")  # drop the injected tests: adjacent compares base as it is
                _git(base_wt, "clean", "-fdq")
                gates["adjacent"] = _adjacent(probe["kind"], adj_files, adjacent_cells("base", base_wt),
                                              adjacent_cells("head", head_wt))
            else:
                gates["adjacent"] = _gate("N_A", reason="no adjacent files present on both arms")
        else:
            gates["sabotage"] = _gate("N_A", reason="skipped: RED or GREEN did not pass")
            gates["adjacent"] = _gate("N_A", reason="skipped: RED or GREEN did not pass")
        return _receipt(wo, spec, spec_sha, run, arms, changed, gates, cells, receipt_tests, safety_canary, relay, None, t0, unpinned)
    finally:
        for path in worktrees:
            _git(repo, "worktree", "remove", "--force", str(path), check=False)


def _adjacent(kind: str, files: list, base_cells: list, head_cells: list) -> dict:
    if any(c["infra"] for c in [*base_cells, *head_cells]):
        return _gate("INFRA", reason="guard blocked an attempt or never loaded in an adjacent cell")
    if kind == "pytest":
        base, head = _pytest_status(base_cells[0]["output"]), _pytest_status(head_cells[0]["output"])
        if set(files) - set(base) or set(files) - set(head):
            return _gate("INFRA", reason="could not read a per-file result", files=sorted(set(files) - set(base) - set(head)))
    else:
        base = {f: c["rc"] == 0 for f, c in zip(files, base_cells)}
        head = {f: c["rc"] == 0 for f, c in zip(files, head_cells)}
    regressions = sorted(f for f in files if base[f] and not head[f])
    pre_existing = sorted(f for f in files if not base[f] and not head[f])
    detail = {"files": files, "base_failing": sorted(f for f in files if not base[f]),
              "head_failing": sorted(f for f in files if not head[f]), "pre_existing_failures": pre_existing}
    return _gate("FAIL", regressions=regressions, **detail) if regressions else _gate("PASS", **detail)


def _receipt(wo, spec, spec_sha, run, arms, changed, gates, cells, tests, safety_canary, relay, verdict, t0, unpinned) -> dict:
    own = spec.get("ownership", {})
    ownership = own.get("verdict", "unknown")
    gates["ownership"] = _gate({"clear": "PASS", "ours": "PASS", "coordinated": "PASS", "external": "FAIL"}.get(ownership, "PENDING"),
                               recorded=ownership, searched_at=own.get("searched_at"), queries=own.get("queries", []))
    results = {k: gates.get(k, {}).get("result") for k in FOUR_COLUMNS}
    flaky = any(g.get("result") == "FLAKY" for g in gates.values())
    infra_cells = [c["name"] for c in cells if c["infra"]]
    if verdict is None:
        if infra_cells or any(r == "INFRA" for r in results.values()):
            verdict = "INFRA"
        elif flaky:
            verdict = "FLAKY"
        elif any(r == "FAIL" for r in results.values()):
            verdict = "DISCARD"
        elif all(r == "PASS" for r in results.values()) and gates["ownership"]["result"] == "PASS":
            verdict = "KEEP"
        else:
            verdict = "PARTIAL"
    blocked = [b for c in cells for b in c["blocked"]]
    count = lambda events: sum(1 for b in blocked if b["event"] in events)  # noqa: E731
    reasons = [f"{k}: {g.get('reason') or g['result']}" for k, g in gates.items() if g["result"] not in ("PASS", "N_A")]
    reasons += [f"infra cells: {', '.join(infra_cells)}"] if infra_cells else []
    measurements = [{"name": f"{c['name']}_exit", "value": c["rc"], "unit": "exit code", "label": "OBSERVED", "source": "probe"}
                    for c in cells]
    red = gates.get("red", {})
    measurements.insert(0, {"name": "red_reps_failing_with_marker", "value": red.get("reps_agree"), "unit": "reps",
                            "label": "OBSERVED", "source": "probe", "primary": True})
    return {
        "schema": SCHEMA,
        "id": f"{spec['id']}/{run.dir.name.rsplit('-', 1)[-1]}",
        "generated_at": _now(),
        "spec": {"id": spec["id"], "rev": spec.get("rev", 1), "sha256": spec_sha, "kind": spec["kind"]},
        "work_order": {"id": wo["id"], "from": wo["from"], "status": wo["status"]},
        "runner_revision": "evals/_factory/gate_runner.py@" + _sha256(Path(__file__).read_bytes())[:12],
        "issue": spec.get("issue"),
        "origin_refs": spec.get("origin_refs", []),
        "base_revision": arms["base"]["commit"],
        "head_revision": arms.get("head", {}).get("commit") or spec["head"]["commit"],
        "arms": arms,
        "changed_files": changed,
        "tests": tests,
        "gates": {**gates, "flaky": flaky},
        "measurements": measurements,
        "denominators": {"cells": len(cells), "infra": sum(c["infra"] for c in cells),
                         "completeness": round(1 - sum(c["infra"] for c in cells) / len(cells), 3) if cells else None},
        "env": {"python": safety_canary.get("python") if safety_canary else None,
                "sandbox": "in-process guard per cell (loopback-only connect, name lookups, live-home opens, hermes exec); "
                           "fresh HOME/HERMES_HOME per cell; empty env; no kernel network namespace",
                "relay": relay},
        "safety": {"canary": safety_canary or None, "egress_blocked": count({"socket.connect", "socket.getaddrinfo",
                   "socket.gethostbyname", "socket.gethostbyname_ex", "socket.gethostbyaddr"}),
                   "home_blocked": count({"open"}), "exec_blocked": count({"subprocess.Popen", "os.exec", "os.posix_spawn",
                   "os.spawn", "os.system"}), "interpreter_writes_refused": sum(c["interpreter_writes_refused"] for c in cells),
                   "hermes_home_isolated": bool(safety_canary and safety_canary["checks"].get("home_isolated"))},
        "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
        "builds": [], "runtime_evidence": [], "security_checks": [],
        "resource_usage": {"wall_s": round(time.monotonic() - t0, 1), "cpu_core_s": None, "tokens": 0, "api_cost_usd": 0.0},
        "outcome": {"execution_completed": verdict not in ("INFRA", "BLOCKED"), "verified_success": None,
                    "verification_source": "self-run gate runner (not independent)"},
        "provenance": "self",
        "verdict": verdict,
        "refused": verdict not in ("KEEP", "PARTIAL"),
        "refusal_reasons": reasons if verdict not in ("KEEP",) else [],
        "unpinned_hunks": unpinned or [],
        "limitations": ["in-process guard only; pair with a kernel network namespace for a hard boundary",
                        *spec.get("outputs", {}).get("limitations", [])],
        "not_tested": spec.get("outputs", {}).get("not_tested", []),
        "ai_assistance": spec.get("ai_assistance", "Runner and spec written with an AI assistant; disclosed per repository policy"),
        "privacy": "public-aggregate",
    }


def validate_receipt(receipt: dict, now: datetime | None = None, max_age_hours: float | None = None) -> list[str]:
    """Return every reason the receipt cannot back a staging claim (empty list = valid)."""
    problems = []
    if receipt.get("schema") != SCHEMA:
        return [f"schema must be {SCHEMA}"]
    required = ("id", "generated_at", "spec", "work_order", "base_revision", "head_revision", "arms", "gates",
                "measurements", "safety", "outcome", "verdict", "evidence_class", "resource_usage", "ai_assistance")
    problems += [f"missing {k}" for k in required if k not in receipt]
    if problems:
        return problems
    for key in ("base_revision", "head_revision"):
        if not SHA_RE.match(str(receipt[key])):
            problems.append(f"{key} is not pinned to a full SHA")
    measurements = receipt["measurements"]
    if not isinstance(measurements, list) or not all(isinstance(m, dict) for m in measurements):
        return [*problems, "measurements must be a list of objects"]
    if any(not isinstance(m.get("label"), str) or m["label"] not in LABELS for m in measurements):
        problems.append("every measurement needs an OBSERVED/MODELED/PRIOR/NOT_MEASURED label")
    primary = [m for m in measurements if m.get("primary")]
    if not primary or any(m.get("label") != "OBSERVED" for m in primary):
        problems.append("the headline measurement must be OBSERVED")
    outcome = receipt["outcome"]
    if outcome.get("verified_success") is not None:
        problems.append("verified_success must stay null: a self-run gate is not independent verification")
    if not isinstance(outcome.get("execution_completed"), bool):
        problems.append("execution_completed must be a boolean")
    verdict, gates, safety = receipt["verdict"], receipt["gates"], receipt["safety"]
    if verdict not in VERDICTS:
        problems.append(f"unknown verdict {verdict!r}")
    if not isinstance(gates, dict):
        return [*problems, "gates must be an object"]
    if verdict == "KEEP":
        for gate in (*FOUR_COLUMNS, "ownership"):
            if not isinstance(gates.get(gate), dict) or gates[gate].get("result") != "PASS":
                problems.append(f"KEEP needs {gate} PASS")
        # PASS flags alone cannot establish that any base/head probes ran.
        # Bind their existing repetition summaries to numbered exit observations.
        counts = {}
        for gate, want_fail in (("red", True), ("green", False)):
            detail = gates.get(gate) if isinstance(gates.get(gate), dict) else {}
            observed = [m for m in measurements if isinstance(m.get("name"), str)
                        and re.fullmatch(rf"{gate}-[0-9]+_exit", m["name"])]
            count = counts[gate] = len(observed)
            if (not count or detail.get("reps_agree") != f"{count}/{count}"
                    or {m["name"] for m in observed} != {f"{gate}-{i}_exit" for i in range(count)}
                    or any(type(m.get("value")) is not int or (m["value"] != 0) != want_fail
                           or m.get("label") != "OBSERVED" for m in observed)):
                problems.append(f"KEEP needs nonempty unanimous {gate} repetitions matching exit observations")
        if counts["red"] != counts["green"]:
            problems.append("KEEP needs equal RED and GREEN repetition counts")
        headline = [m for m in measurements if m.get("name") == "red_reps_failing_with_marker"]
        if (len(headline) != 1 or headline[0].get("value") != f"{counts['red']}/{counts['red']}"
                or headline[0].get("primary") is not True or headline[0].get("label") != "OBSERVED"):
            problems.append("KEEP needs one observed RED repetition headline matching its proof")
        if gates.get("flaky"):
            problems.append("KEEP cannot be flaky")
        if (receipt.get("denominators") or {}).get("infra"):
            problems.append("KEEP cannot include infra cells")
        if safety.get("egress_blocked") or safety.get("home_blocked") or safety.get("exec_blocked"):
            problems.append("KEEP cannot include blocked egress, live-home or exec attempts")
        if not safety.get("hermes_home_isolated") or not (safety.get("canary") or {}).get("passed"):
            problems.append("KEEP needs a passing guard canary with an isolated HERMES_HOME")
    if receipt["evidence_class"].get("local") is not True or "ci" not in receipt["evidence_class"]:
        problems.append("evidence_class must separate local and CI evidence")
    if _PRIVATE.search(json.dumps(receipt)):
        problems.append("receipt contains a home path, email, token or key")
    if _ABS_PATH.search(json.dumps(receipt)):
        problems.append("receipt contains an absolute local path")
    if max_age_hours is not None:
        made = datetime.strptime(receipt["generated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if ((now or datetime.now(timezone.utc)) - made).total_seconds() > max_age_hours * 3600:
            problems.append(f"receipt is older than {max_age_hours} h; re-run on a fresh base")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="execute one claimed work order")
    r.add_argument("--work-order", required=True)
    r.add_argument("--repo", required=True, help="git repository (bare is fine) holding base and head")
    r.add_argument("--scratch", required=True, help="run directory parent; never under the live Hermes home")
    r.add_argument("--python", default=os.environ.get("HERMES_PYTHON") or sys.executable)
    r.add_argument("--out", required=True)
    v = sub.add_parser("validate", help="check a receipt")
    v.add_argument("receipt")
    v.add_argument("--max-age-hours", type=float, default=None)
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        problems = validate_receipt(json.loads(Path(a.receipt).read_text(encoding="utf-8")), max_age_hours=a.max_age_hours)
        print("\n".join(problems) or "valid")
        return 1 if problems else 0
    try:
        receipt = run_gate(a.work_order, a.repo, a.scratch, a.python)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    problems = validate_receipt(receipt)
    Path(a.out).write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(f"{receipt['id']}: {receipt['verdict']}" + "".join(f"\n  {g}: {receipt['gates'][g].get('result')}"
          for g in ("validity", *FOUR_COLUMNS, "ownership") if g in receipt["gates"]))
    print("receipt: " + ("valid" if not problems else "INVALID: " + "; ".join(problems)))
    return 0 if receipt["verdict"] in ("KEEP", "PARTIAL") and not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
