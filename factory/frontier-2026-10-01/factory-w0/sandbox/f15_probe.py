"""F15-full probe: runs INSIDE xf-sandbox.sh and prints one JSON line.

    python f15_probe.py net <addr> <port>    TCP connect to a non-loopback address (a decoy listener on this host)
    python f15_probe.py write <decoy-dir>    create one marker file in a decoy dir outside the run dir
    python f15_probe.py hermes_home          os.path.exists of one public source file in the live install
    python f15_probe.py home                 os.path.isdir of the real ~/.hermes (nothing is opened or listed)
    python f15_probe.py exec                 resolve `hermes`; execute it ONLY if it is the sandbox stub
    python f15_probe.py imports              where hermes_cli is imported from

"blocked" is true when the guard held. Each probe touches only what its docstring line says.
"""
import json, os, pwd, shutil, socket, subprocess, sys

LIVE_INSTALL = os.environ.get("XF_LIVE_INSTALL", "<hermes-home>")


def out(probe, blocked, **detail):
    print(json.dumps({"probe": probe, "blocked": blocked, **detail}))


def main(argv):
    probe = argv[1]
    if probe == "net":
        try:
            socket.create_connection((argv[2], int(argv[3])), timeout=3).close()
            out(probe, False, connected=True)
        except OSError as exc:
            out(probe, True, errno=exc.errno, error=type(exc).__name__)
    elif probe == "write":
        marker = os.path.join(argv[2], "MARKER-" + os.path.basename(os.environ["XF_RUN"]))
        try:
            with open(marker, "w") as fh:
                fh.write("written from inside the sandbox\n")
            out(probe, False, wrote=True)
        except OSError as exc:
            out(probe, True, errno=exc.errno, error=type(exc).__name__)
    elif probe == "hermes_home":
        seen = os.path.exists(os.path.join(LIVE_INSTALL, "hermes-agent", "pyproject.toml"))
        detail = {"public_source_file_visible": seen}
        if not seen:  # list only the mask's own tmpfs, never the real install
            detail["mask_view"] = {"<live-install>": sorted(os.listdir(LIVE_INSTALL)),
                                   "<live-install>/hermes-agent": sorted(os.listdir(os.path.join(LIVE_INSTALL, "hermes-agent")))}
        out(probe, not seen, **detail)
    elif probe == "home":
        seen = os.path.isdir(os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".hermes"))
        out(probe, not seen, real_dot_hermes_isdir=seen)
    elif probe == "exec":
        stub = os.path.join(os.environ["XF_RUN"], ".xf", "hermes-stub")
        log = os.path.join(os.environ["XF_RUN"], "blocked-exec.log")
        resolved = shutil.which("hermes")
        is_stub = bool(resolved) and os.path.samefile(resolved, stub)
        if not is_stub:  # never execute anything that is not the stub
            out(probe, resolved is None, resolved="found" if resolved else None, is_stub=False, executed=False)
            return
        before = os.path.getsize(log)
        rc = subprocess.run([resolved, "update"], capture_output=True).returncode
        logged = os.path.getsize(log) > before
        others = {}
        for name in ("hermes-agent", "hermes-acp"):
            p = shutil.which(name)
            others[name] = None if p is None else os.path.samefile(p, stub)
        out(probe, rc == 126 and logged, resolved="found", is_stub=True, executed=True, rc=rc, logged=logged,
            other_console_scripts_are_stub=others)
    elif probe == "imports":
        # The way the test runner imports: cwd (the worktree) first. And without the cwd on sys.path
        # (script mode, as now) nothing may resolve, i.e. no editable install into the live home leaks in.
        import importlib.util
        wt = os.getcwd()
        leak = importlib.util.find_spec("hermes_cli")
        r = subprocess.run([sys.executable, "-c", "import hermes_cli; print(hermes_cli.__file__)"], cwd=wt,
                           capture_output=True, text=True)
        f = os.path.realpath(r.stdout.strip()) if r.returncode == 0 else ""
        out(probe, f.startswith(wt + os.sep) and leak is None, hermes_cli_file=f.replace(wt, "<worktree>", 1),
            resolvable_without_worktree=leak is not None)
    else:
        raise SystemExit(f"unknown probe {probe}")


if __name__ == "__main__":
    main(sys.argv)
