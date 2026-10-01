"""F15-full (T0, $0): kernel sandbox canary. Runs on the host and drives xf-sandbox.sh.

    PYTHONDONTWRITEBYTECODE=1 python3 -B f15_full.py <worktree> <run-id>

For each of 6 guards: the probe runs in the intact sandbox and must be BLOCKED; then it runs in a copy
of the wrapper with exactly ONE guard removed and must ESCAPE. Sabotage targets are decoys only:
  net          a TCP listener on this host's own LAN address (never the internet)
  write        one extra rw bind of factory/w0/sandbox/decoy-outside, one marker file
  hermes_home  os.path.exists of a public source file only
  home         os.path.isdir of the real ~/.hermes only
  exec         shutil.which + samefile against the stub; never executed
  denylist     pytest --collect-only of one denylisted test id (collection, never run)
The receipt has placeholders instead of local paths and no host name.
"""
import hashlib, json, os, re, shutil, socket, subprocess, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent             # <xf-root>/factory/w0/sandbox
XF_ROOT = HERE.parents[2]
WRAPPER = HERE / "xf-sandbox.sh"
PROBE = HERE / "f15_probe.py"
DECOY = HERE / "decoy-outside"
VENV_PY = os.path.join(os.environ.get("XF_LIVE_INSTALL", "<hermes-home>"), "hermes-agent/venv/bin/python")
DENY_FILE = "tests/hermes_cli/test_update_command.py"
DENY_RC = 97

wt = Path(sys.argv[1]).resolve()
run_id = sys.argv[2]
base = XF_ROOT / "factory/w0/runs" / f"F15-full-{run_id}"
base.mkdir(parents=True, exist_ok=False)
DECOY.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
started = now()


def scrub(text):
    for real, ph in ((str(base), "<run-base>"), (str(wt), "<worktree>"), (str(XF_ROOT), "<xf-root>"),
                     (os.path.dirname(os.path.dirname(VENV_PY)), "<venv>"), (str(Path.home()), "<home>")):
        text = text.replace(real, ph)
    return text.replace(socket.gethostname(), "<host>")


# ── decoy listener on this host's non-loopback address ──
route = subprocess.run(["ip", "-4", "route", "get", "192.0.2.1"], capture_output=True, text=True).stdout
lan = re.search(r"\bsrc (\d+\.\d+\.\d+\.\d+)", route).group(1)
assert not lan.startswith("127."), "need a non-loopback address"
srv = socket.socket(); srv.bind((lan, 0)); srv.listen(8); port = srv.getsockname()[1]
accepted = []
def accept_loop():
    while True:
        try:
            c, _ = srv.accept(); accepted.append(time.time()); c.close()
        except OSError:
            return
threading.Thread(target=accept_loop, daemon=True).start()


# ── sabotage copies: exactly one guard removed ──
src = WRAPPER.read_text()
def sabotaged(guard):
    lines = src.splitlines(keepends=True)
    if guard == "write":
        tag = "# XF-SABOTAGE-HOOK:write"
        hits = [i for i, l in enumerate(lines) if tag in l]
        assert len(hits) == 1
        lines[hits[0]] = f'EXTRA_RW=(--bind "{DECOY}" "{DECOY}")  # SABOTAGE: one extra rw bind of a decoy dir\n'
    else:
        tag = f"# XF-GUARD:{guard}"
        hits = [i for i, l in enumerate(lines) if l.rstrip().endswith(tag)]
        assert len(hits) == 1, (guard, hits)
        lines[hits[0]] = f"# SABOTAGE: guard {guard} removed\n"
    p = base / "sabotage" / f"xf-sandbox-no-{guard}.sh"
    p.parent.mkdir(exist_ok=True)
    p.write_text("".join(lines)); p.chmod(0o755)
    changed = sum(a != b for a, b in zip(src.splitlines(), "".join(lines).splitlines()))
    assert changed == 1
    return p


def sandbox(wrapper, name, cmd, timeout=300):
    run = base / name
    r = subprocess.run([str(wrapper), str(run), str(wt), "--", *cmd], capture_output=True, text=True, timeout=timeout)
    return run, r


def probe(wrapper, name, *args):
    run, r = sandbox(wrapper, name, [VENV_PY, str(PROBE), *args])
    line = next((l for l in reversed(r.stdout.splitlines()) if l.startswith("{")), None)
    res = json.loads(line) if line else {"blocked": None, "error": "no probe output"}
    return run, r, res


rows = []
def record(guard, arm, ok, res, rc, extra):
    rows.append({"guard": guard, "arm": arm, "result": ("BLOCKED" if arm == "intact" else "ESCAPED") if ok else "FAIL",
                 "ok": ok, "rc": rc, "probe": res, **extra, "label": "OBSERVED", "at": now()})


# (a) network
for arm, w in (("intact", WRAPPER), ("sabotage", sabotaged("net"))):
    n0 = len(accepted)
    run, r, res = probe(w, f"net-{arm}", "net", lan, str(port))
    time.sleep(0.3)
    seen = len(accepted) - n0
    res = {**res}
    ok = (res["blocked"] is True and seen == 0) if arm == "intact" else (res["blocked"] is False and seen >= 1)
    record("net", arm, ok, res, r.returncode, {"listener_accepts": seen, "target": "<lan-addr>:<free-port> (decoy listener on this host)"})

# (b) write outside $RUN
for arm, w in (("intact", WRAPPER), ("sabotage", sabotaged("write"))):
    marker = DECOY / f"MARKER-write-{arm}"
    assert not marker.exists(), "stale decoy marker; move it aside first"
    run, r, res = probe(w, f"write-{arm}", "write", str(DECOY))
    on_host = marker.exists()
    ok = (res["blocked"] is True and not on_host) if arm == "intact" else (res["blocked"] is False and on_host)
    record("write", arm, ok, res, r.returncode, {"marker_on_host": on_host, "target": "<xf-root>/factory/w0/sandbox/decoy-outside"})

# (c) read of the live install
for arm, w in (("intact", WRAPPER), ("sabotage", sabotaged("hermes_home"))):
    run, r, res = probe(w, f"hermes_home-{arm}", "hermes_home")
    ok = res["blocked"] is (arm == "intact")
    if arm == "intact":
        ok = ok and res.get("mask_view") == {"<live-install>": ["hermes-agent"], "<live-install>/hermes-agent": ["venv"]}
    record("hermes_home", arm, ok, res, r.returncode, {})

# (d) existence of the real ~/.hermes
for arm, w in (("intact", WRAPPER), ("sabotage", sabotaged("home"))):
    run, r, res = probe(w, f"home-{arm}", "home")
    record("home", arm, res["blocked"] is (arm == "intact"), res, r.returncode, {})

# (e) exec of hermes
for arm, w in (("intact", WRAPPER), ("sabotage", sabotaged("exec"))):
    run, r, res = probe(w, f"exec-{arm}", "exec")
    log_lines = (run / "blocked-exec.log").read_text().splitlines()
    if arm == "intact":
        ok = res["blocked"] is True and res.get("is_stub") and res.get("rc") == 126 and len(log_lines) == 1 \
            and all(v is not False for v in res.get("other_console_scripts_are_stub", {}).values())
    else:
        ok = res["blocked"] is False and res.get("resolved") == "found" and res.get("is_stub") is False \
            and res.get("executed") is False and len(log_lines) == 0
    record("exec", arm, ok, res, r.returncode, {"blocked_exec_log_lines": len(log_lines)})

# (f) denylisted test selection
first = re.search(r"^def (test_\w+)", (wt / DENY_FILE).read_text(), re.M).group(1)
test_id = f"{DENY_FILE}::{first}"
collect = [VENV_PY, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", test_id]
for arm, w in (("intact", WRAPPER), ("sabotage", sabotaged("denylist"))):
    run, r = sandbox(w, f"denylist-{arm}", collect)
    collected = test_id in r.stdout
    if arm == "intact":
        ok = r.returncode == DENY_RC and not collected and not run.joinpath(".xf").exists()
    else:
        ok = r.returncode == 0 and collected
    record("denylist", arm, ok, {"blocked": arm == "intact" and ok, "collected": collected,
                                 "stderr_tail": scrub(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "")},
           r.returncode, {"selection": test_id, "mode": "pytest --collect-only (never run)"})

srv.close()

# ── side checks: imports resolve to the worktree; the documented usage runs one small test file ──
_, r, imports = probe(WRAPPER, "imports", "imports")
usage_cmd = ["scripts/run_tests.sh", "tests/test_hermes_constants.py", "-q"]
urun, ur = sandbox(WRAPPER, "usage", usage_cmd, timeout=900)
summary = next((l for l in reversed(ur.stdout.splitlines()) if re.search(r"\d+ (passed|failed)", l)), "")
blocked_ok = [x["ok"] for x in rows if x["arm"] == "intact"]
escaped_ok = [x["ok"] for x in rows if x["arm"] == "sabotage"]
passed = all(blocked_ok) and all(escaped_ok) and len(blocked_ok) == 6 and len(escaped_ok) == 6

head = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
bw = subprocess.run(["/usr/bin/bwrap", "--version"], capture_output=True, text=True).stdout.strip()
receipt = {
    "schema": "xf.receipt.v1",
    "id": f"F15-full/{run_id}",
    "experiment": "F15",
    "tier": "T0",
    "label_default": "OBSERVED",
    "cost_usd": 0,
    "question": "From inside the kernel sandbox, is each of 6 probes blocked, and does each escape when exactly one guard is removed?",
    "spec": {"path": "FACTORY.md section 13 row 1, section 6 layers 1, 4, 5", "rev": 1,
             "decision_rule": "PASS iff 6/6 probes BLOCKED in the intact sandbox and 6/6 ESCAPED in a wrapper copy with exactly one guard removed (one changed line each)"},
    "runner_revision": {
        "sandbox": {"path": "factory/w0/sandbox/xf-sandbox.sh", "sha256": sha(WRAPPER)},
        "probe": {"path": "factory/w0/sandbox/f15_probe.py", "sha256": sha(PROBE)},
        "driver": {"path": "factory/w0/sandbox/f15_full.py", "sha256": sha(__file__)},
        "sabotage_copies": {p.name: sha(p) for p in sorted((base / "sabotage").iterdir())},
    },
    "staging": "factory-replay-gate",
    "base_revision": head,
    "env": {"host": "<local-host>", "os": "Linux x86_64", "bwrap": bw, "interpreter": "<venv>/bin/python 3.11 (read-only, re-bound inside the mask)",
            "sandbox": "bwrap ro-root, rw <run> + <worktree> only, netns loopback-only, pidns, new session, die-with-parent, clearenv, real home tmpfs, /run tmpfs, live install tmpfs + venv ro, console scripts stubbed, H1 denylist pre-exec",
            "network": "loopback only inside; sabotage net arm reached a decoy listener on this host's LAN address"},
    "command": "PYTHONDONTWRITEBYTECODE=1 python3 -B factory/w0/sandbox/f15_full.py <worktree> <run-id>",
    "started_at": started,
    "finished_at": now(),
    "results": {"blocked": f"{sum(blocked_ok)}/6", "sabotage_escapes": f"{sum(escaped_ok)}/6", "label": "OBSERVED"},
    "probes": rows,
    "side_checks": {
        "imports_resolve_to_worktree": {"ok": imports.get("blocked") is True, "hermes_cli_file": imports.get("hermes_cli_file"), "label": "OBSERVED"},
        "usage_run_tests": {"command": "<xf-root>/factory/w0/sandbox/xf-sandbox.sh <run> <worktree> -- " + " ".join(usage_cmd),
                            "rc": ur.returncode, "summary": scrub(summary.strip()), "label": "OBSERVED"},
    },
    "verdict": "PASS" if passed else "FAIL",
    "not_tested": [
        "console scripts in the venv whose names are not in the worktree's pyproject [project.scripts] (the venv bin dir is not listed); any such script would still run worktree code under the isolated home with no network",
        "other paths outside the real home and the live install stay readable (read-only); only those two plus /run are masked",
        "the denylist parses argv words, not shell grammar; selections built at runtime inside the sandbox are contained by the kernel layer, not refused",
        "C-extension or ctypes egress is covered by the netns, but no such probe was run",
        "the 'not live and not integration' marker filter comes from the repo's pytest addopts, not from the wrapper",
    ],
    "privacy": "public-aggregate; paths are placeholders",
}
text = scrub(json.dumps(receipt, indent=1)) + "\n"
out = XF_ROOT / "factory/w0/receipts" / f"F15-full-{run_id}.json"
out.write_text(text)
print(receipt["verdict"], receipt["results"])
for x in rows:
    print(f"  {x['guard']:12s} {x['arm']:8s} {x['result']:8s} rc={x['rc']}")
print("imports:", receipt["side_checks"]["imports_resolve_to_worktree"])
print("usage:", receipt["side_checks"]["usage_run_tests"]["rc"], receipt["side_checks"]["usage_run_tests"]["summary"])
