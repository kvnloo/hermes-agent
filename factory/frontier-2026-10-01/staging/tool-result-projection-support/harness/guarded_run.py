"""Run an in-tree eval script under the $0 guard: cleared environment with a fresh HOME and
HERMES_HOME, loopback-only socket.connect / getaddrinfo (pattern of
evals/provider_fallback/probe_104260.py:11-39), blocked attempts written to <script>.egress.json.

Usage: env -i PATH=/usr/bin:/bin PYTHONHASHSEED=0 GUARD_SCRATCH=<dir> [GUARD_PROJECTION=auto] \
           <venv python> guarded_run.py <repo> <script.py> [script args...]

GUARD_PROJECTION=auto turns the opt-in tool-result projection on for every ContextCompressor the
script builds (the same value ``compression.tool_result_projection: auto`` in config.yaml passes to
the constructor); it is a no-op on a tree without the projection.
"""

import json
import os
import runpy
import socket
import sys
import tempfile
from pathlib import Path

REPO, SCRIPT, ARGS = sys.argv[1], sys.argv[2], sys.argv[3:]
SCRATCH = os.environ.get("GUARD_SCRATCH") or "/tmp"
PROJECTION = os.environ.get("GUARD_PROJECTION", "")
sys.dont_write_bytecode = True
sandbox = Path(tempfile.mkdtemp(prefix="guard-", dir=SCRATCH))
os.environ.clear()
os.environ.update(HOME=str(sandbox / "home"), HERMES_HOME=str(sandbox / "hermes"), TMPDIR=str(sandbox / "tmp"),
                  PATH="/usr/bin:/bin", TZ="UTC", LANG="C.UTF-8", PYTHONHASHSEED="0",
                  PYTHONDONTWRITEBYTECODE="1", HERMES_DISABLE_MODEL_METADATA_FETCH="1")
for d in ("home", "hermes", "tmp"):
    (sandbox / d).mkdir()
os.chdir(REPO)
sys.path.insert(0, REPO)

_LOOPBACK = ("127.0.0.1", "::1", "localhost")
_connect, _gai = socket.socket.connect, socket.getaddrinfo
blocked: list[str] = []


def _guard_connect(self, address):
    if isinstance(address, tuple) and address[0] not in _LOOPBACK:
        blocked.append(f"connect {address!r}")
        raise RuntimeError("guard blocks non-loopback network")
    return _connect(self, address)


def _guard_gai(host, *a, **k):
    if host is not None and host not in _LOOPBACK:
        blocked.append(f"getaddrinfo {host!r}")
        raise socket.gaierror("guard blocks non-loopback name resolution")
    return _gai(host, *a, **k)


socket.socket.connect, socket.getaddrinfo = _guard_connect, _guard_gai

if PROJECTION:
    from agent.context_compressor import ContextCompressor

    _init = ContextCompressor.__init__

    def _init_with_projection(self, *a, **k):
        _init(self, *a, **k)
        if hasattr(self, "tool_result_projection"):
            self.tool_result_projection = PROJECTION

    ContextCompressor.__init__ = _init_with_projection

rc = 0
sys.argv = [SCRIPT, *ARGS]
try:
    runpy.run_path(SCRIPT, run_name="__main__")
except SystemExit as exc:
    rc = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
finally:
    Path(str(sandbox) + ".egress.json").write_text(json.dumps({"blocked": blocked, "rc": rc}), encoding="utf-8")
    print(f"[guard] rc={rc} egress_blocked={len(blocked)} sandbox={sandbox}", file=sys.stderr)
sys.exit(rc)
