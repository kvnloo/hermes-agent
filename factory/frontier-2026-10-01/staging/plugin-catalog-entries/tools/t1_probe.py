"""T1 ($0, no egress) probes for the paw-pii catalog entry. Run inside tools/sandbox.sh.

capability  Calls hermes's production capability probe (hermes_cli.plugin_validate._run_capability_probe)
            as a library call against a plugin directory, then applies the same declared-vs-registered
            rule as _check_capabilities. This is NOT `hermes plugins validate` (no CLI, no --install-deps);
            the E52 gate stays queued.
failopen    Imports the plugin the way the loader does (spec_from_file_location, package path = plugin dir)
            in one child process per install layout, and drives its middleware through the real
            hermes_cli.middleware chain (apply_llm_request_middleware / run_tool_execution_middleware),
            with only the plugin registry stubbed (a real PluginManager holding the plugin's callbacks).
            Layouts: full-clone (what admission CI validates) and catalog-install (subdir-only copy, what
            `hermes plugins install paw-pii` publishes into $HERMES_HOME/plugins/paw-pii).

Every child installs a loopback-only socket guard and an exec/subprocess audit hook; blocked attempts are
counted and reported (a blocked attempt is INFRA, never silent).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CANARY = "Contact Ada Lovelace at ada.lovelace@example.com or +1 415 555 0100."
CANARY_MARKERS = ("ada.lovelace@example.com", "415 555 0100", "Ada Lovelace")

GUARD = r'''
import socket as _s, sys as _sys
_BLOCKED = []
_orig_connect = _s.socket.connect
def _guarded(self, addr):
    host = addr[0] if isinstance(addr, tuple) else str(addr)
    if host not in ("127.0.0.1", "::1", "localhost") and not str(host).startswith("/"):
        _BLOCKED.append(("connect", str(host)))
        raise OSError("egress blocked by t1 guard: %s" % (host,))
    return _orig_connect(self, addr)
_s.socket.connect = _guarded
_ALLOWED = []
def _allowlisted(event, args):
    # read-only `git rev-parse` (hermes bundled-provider discovery) and, in capability mode, the
    # production probe's own child interpreter; everything else is blocked and counted.
    if event != "subprocess.Popen":
        return False
    argv = list(args[1]) if len(args) > 1 and isinstance(args[1], (list, tuple)) else []
    # (the hermes tree is on the read-only root inside bwrap, so git cannot write it either way)
    if argv and str(argv[0]).endswith("git") and len(argv) > 1 and (
            argv[1] in ("rev-parse", "describe", "log", "rev-list", "show", "cat-file", "ls-files",
                        "symbolic-ref", "status")
            or argv[1:3] in (["branch", "--show-current"], ["config", "--get"])
            or (argv[1] == "tag" and "--list" in argv)):
        return True
    return bool(_ALLOW_EXEC[0]) and bool(argv) and str(argv[0]) == _sys.executable
def _audit(event, args):
    if event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn"):
        if _allowlisted(event, args):
            _ALLOWED.append((event, str(args[1])[:120]))
            return
        _BLOCKED.append((event, str(args)[:120]))
        raise RuntimeError("exec blocked by t1 guard: %s" % event)
_ALLOW_EXEC = [False]
_sys.addaudithook(_audit)
'''


def leaked(value) -> list[str]:
    text = json.dumps(value, default=str)
    return [m for m in CANARY_MARKERS if m in text]


def child_failopen(plugin_dir: Path, hermes_tree: Path, layout: str) -> dict:
    exec(GUARD, globals())
    sys.path.insert(0, str(hermes_tree))
    import importlib.util
    import logging

    records: list[str] = []

    class _Grab(logging.Handler):
        def emit(self, rec):
            records.append(f"{rec.levelname} {rec.name}: {rec.getMessage()}")

    logging.getLogger().addHandler(_Grab())
    logging.getLogger().setLevel(logging.INFO)

    from hermes_cli import middleware as mw
    from hermes_cli import plugins as hp
    origin = Path(mw.__file__).resolve()
    assert hermes_tree.resolve() in origin.parents, origin

    spec = importlib.util.spec_from_file_location(
        f"hermes_plugins.paw_pii_{layout.replace('-', '_')}", str(plugin_dir / "__init__.py"),
        submodule_search_locations=[str(plugin_dir)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    mgr = hp.PluginManager()
    mgr._middleware = {"llm_request": [mod._on_llm_request], "tool_execution": [mod._on_tool_execution]}
    hp._delivery_manager = lambda: mgr  # registry stub only; chain code below is production

    request = {"model": "m", "messages": [{"role": "user", "content": CANARY}]}
    raw_llm = mod._on_llm_request(request=dict(request))
    res = mw.apply_llm_request_middleware(request)
    tool_out = mw.run_tool_execution_middleware(
        "read_file", {"path": "notes.txt"}, next_call=lambda args: {"output": CANARY})

    def call(fn):
        try:
            return {"ok": True, "value": fn(text=CANARY)}
        except Exception as exc:
            return {"ok": False, "exception": f"{type(exc).__name__}: {exc}"}

    detect = call(mod._handle_detect_pii)
    redact = call(mod._handle_redact_pii)
    return {
        "layout": layout,
        "plugin_dir_files": sorted(p.name for p in plugin_dir.iterdir()),
        "hermes_cli_origin": str(origin.parent),
        "paw_pii_importable": importlib.util.find_spec("paw_pii") is not None,
        "programasweights_importable": importlib.util.find_spec("programasweights") is not None,
        "plugin_on_llm_request_return": raw_llm,
        "llm_request_chain": {"changed": res.changed, "trace": res.trace,
                              "payload_leaks_canary": leaked(res.payload),
                              "payload_equals_original": res.payload == res.original_payload},
        "tool_execution_chain": {"result": tool_out, "leaks_canary": leaked(tool_out)},
        "tool_detect_pii": detect,
        "tool_redact_pii": redact,
        "tool_redact_leaks_canary": leaked(redact),
        "log_records": records[-12:],
        "guard_blocked": list(_BLOCKED),  # noqa: F821 (defined by GUARD)
        "guard_allowed": list(_ALLOWED),  # noqa: F821
    }


def child_capability(plugin_dir: Path, hermes_tree: Path, manifest_json: str) -> dict:
    exec(GUARD, globals())
    _ALLOW_EXEC[0] = True  # noqa: F821  the production probe itself spawns one child interpreter
    sys.path.insert(0, str(hermes_tree))
    import hermes_cli.plugin_validate as pv
    origin = Path(pv.__file__).resolve()
    assert hermes_tree.resolve() in origin.parents, origin
    manifest = json.loads(manifest_json)
    recorded, error = pv._run_capability_probe(plugin_dir, manifest)
    verdict = []
    if recorded is not None:
        for kind, key in (("tools", "provides_tools"), ("hooks", "provides_hooks"),
                          ("middleware", "provides_middleware")):
            declared = set(pv._declared_list(manifest, key))
            actual = set(recorded.get(kind) or [])
            verdict.append({"check": f"declared {kind}", "ok": not (actual - declared),
                            "undeclared": sorted(actual - declared), "unregistered": sorted(declared - actual)})
    probe_src = pv._PROBE_SCRIPT
    return {"hermes_cli_origin": str(origin.parent),
            "probe_script_sha256": hashlib.sha256(probe_src.encode()).hexdigest(),
            "recorded": recorded, "error": error, "checks": verdict,
            "result": "PASS" if recorded is not None and all(v["ok"] for v in verdict) else "FAIL",
            "guard_blocked": list(_BLOCKED), "guard_allowed": list(_ALLOWED)}  # noqa: F821


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["capability", "failopen"])
    ap.add_argument("--hermes-tree", type=Path, required=True)
    ap.add_argument("--plugin-dir", type=Path, required=True)
    ap.add_argument("--manifest-json", default="{}")
    ap.add_argument("--layout", default="full-clone")
    ap.add_argument("--child", action="store_true")
    a = ap.parse_args()
    if a.child:
        out = (child_capability(a.plugin_dir, a.hermes_tree, a.manifest_json) if a.mode == "capability"
               else child_failopen(a.plugin_dir, a.hermes_tree, a.layout))
        print("T1_JSON:" + json.dumps(out, default=str))
        return 0

    results = []
    layouts = ["full-clone"] if a.mode == "capability" else ["full-clone", "catalog-install"]
    for layout in layouts:
        pdir = a.plugin_dir
        if layout == "catalog-install":
            sim = Path(os.environ.get("HERMES_HOME", "/tmp/hh")) / "plugins" / "paw-pii"
            shutil.rmtree(sim, ignore_errors=True)
            shutil.copytree(a.plugin_dir, sim, ignore=shutil.ignore_patterns("__pycache__"))
            pdir = sim
        cmd = [sys.executable, "-I", __file__, a.mode, "--child", "--hermes-tree", str(a.hermes_tree),
               "--plugin-dir", str(pdir), "--manifest-json", a.manifest_json, "--layout", layout]
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(a.hermes_tree), timeout=300)
        line = next((l for l in p.stdout.splitlines() if l.startswith("T1_JSON:")), None)
        results.append(json.loads(line[8:]) if line else
                       {"layout": layout, "INFRA": True, "rc": p.returncode, "stderr": p.stderr[-2000:]})
    print(json.dumps({"schema": "t1.probe.v1", "mode": a.mode,
                      "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      "canary": CANARY, "results": results}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
