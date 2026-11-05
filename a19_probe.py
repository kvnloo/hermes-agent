#!/usr/bin/env python3
"""Tiny groot-only A19 probe. No live profiles, sockets, credentials, or config.
Run each invocation under 10 seconds. Not a real-agent throughput benchmark.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import resource
import statistics
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--native", action="store_true", help="also try the isolated installed Hermes LocalEnvironment")
    args = parser.parse_args()
    if platform.node() != "groot":
        parser.error("this fixture measures groot only")
    rows = []
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="a19-probe-") as root:
        root = Path(root)
        work = root / "work"
        work.mkdir()
        canary = root / "outside.txt"
        canary.write_text("owned synthetic canary\n")
        (work / "outside-link").symlink_to(canary)
        (work / "input.txt").write_text("A19 owned fixture\n" * 256)
        task = work / "task.py"
        task.write_text('''import hashlib, json, pathlib, subprocess, sys, time
work = pathlib.Path(sys.argv[1])
start = time.perf_counter_ns()
data = (work / "input.txt").read_bytes()
(work / "output.txt").write_bytes(data.upper())
print(json.dumps({"sha256": hashlib.sha256(data.upper()).hexdigest(),
                  "logical_read_bytes": len(data), "logical_write_bytes": len(data),
                  "inner_ms": (time.perf_counter_ns() - start) / 1e6}))
''')
        escape = work / "escape.py"
        escape.write_text('''import json, pathlib, sys
work, outside = map(pathlib.Path, sys.argv[1:])
results = {}
for name, path in [("absolute_read", outside), ("symlink_read", work / "outside-link"),
                   ("proc_root_read", pathlib.Path("/proc/self/root") / str(outside).lstrip("/"))]:
    try:
        path.read_bytes()
        results[name] = "ALLOWED"
    except OSError as exc:
        results[name] = type(exc).__name__
try:
    with outside.open("r+b") as handle:
        handle.write(b"owned")
    results["outside_write"] = "ALLOWED"
except OSError as exc:
    results["outside_write"] = type(exc).__name__
(work / "inside.txt").write_text("allowed")
results["inside_write"] = "ALLOWED"
print(json.dumps(results))
''')
        bwrap = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session",
                 "--cap-drop", "ALL", "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
                 "--setenv", "HOME", str(work), "--setenv", "LC_ALL", "C",
                 "--ro-bind", "/usr", "/usr", "--ro-bind", "/etc", "/etc",
                 "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
                 "--symlink", "usr/lib", "/lib64", "--proc", "/proc", "--dev", "/dev",
                 "--tmpfs", "/tmp", "--bind", str(work), str(work), "--chdir", str(work), "--"]
        rights = "execute,read-file,read-dir"
        landlock = ["/usr/bin/setpriv", "--no-new-privs", "--landlock-access", "fs"]
        for path in ("/usr", "/etc", "/proc"):
            landlock += ["--landlock-rule", f"path-beneath:{rights}:{path}"]
        landlock += ["--landlock-rule", "path-beneath:read-file,write-file:/dev/null",
                     "--landlock-rule", f"path-beneath:{rights},write-file,remove-file,remove-dir,make-dir,make-reg,make-sym,refer,truncate:{work}", "--"]
        wrappers = {"bare": [], "bubblewrap": bwrap, "landlock-setpriv": landlock}
        env = {"PATH": "/usr/bin:/bin", "HOME": str(work), "LC_ALL": "C"}

        def run(strategy, kind, command):
            argv = wrappers[strategy] + command
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            tick = time.perf_counter_ns()
            proc = subprocess.run(argv, cwd=work, env=env, capture_output=True, text=True, timeout=2)
            elapsed = (time.perf_counter_ns() - tick) / 1e6
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            row = {"strategy": strategy, "kind": kind, "argv": argv, "exit": proc.returncode,
                   "wall_ms": elapsed, "stdout": proc.stdout, "stderr": proc.stderr,
                   "user_cpu_ms": (after.ru_utime - before.ru_utime) * 1000,
                   "system_cpu_ms": (after.ru_stime - before.ru_stime) * 1000,
                   "block_in": after.ru_inblock - before.ru_inblock,
                   "block_out": after.ru_oublock - before.ru_oublock}
            rows.append(row)
            return row

        available = []
        for strategy in wrappers:
            if run(strategy, "availability", ["/usr/bin/true"])["exit"] == 0:
                available.append(strategy)
        rng = random.Random(19)
        for repetition in range(5):
            order = available.copy()
            rng.shuffle(order)
            for strategy in order:
                run(strategy, "startup_exit", ["/usr/bin/true"])
                argv = wrappers[strategy] + ["/usr/bin/printf", "A19-READY\\n"]
                tick = time.perf_counter_ns()
                with subprocess.Popen(argv, cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
                    marker = proc.stdout.readline()
                    ready = time.perf_counter_ns()
                    stdout, stderr = proc.communicate(timeout=2)
                reaped = time.perf_counter_ns()
                rows.append({"strategy": strategy, "kind": "marker_lifecycle", "argv": argv,
                             "exit": proc.returncode, "stdout": (marker + stdout).decode(), "stderr": stderr.decode(),
                             "startup_to_marker_ms": (ready - tick) / 1e6,
                             "marker_to_reap_ms": (reaped - ready) / 1e6,
                             "wall_ms": (reaped - tick) / 1e6})
                run(strategy, "shell_tool", ["/bin/bash", "--noprofile", "--norc", "-c", "printf A19; /usr/bin/stat -c %s input.txt"])
                run(strategy, "file_task", ["/usr/bin/python3", str(task), str(work)])
        for strategy in available:
            canary.write_text("owned synthetic canary\n")
            run(strategy, "escape", ["/usr/bin/python3", str(escape), str(work), str(canary)])
        if args.native:
            source = "/workspace/hermes-home/hermes-agent"
            packages = source + "/venv/lib/python3.11/site-packages"
            env.update({"HERMES_HOME": str(work / "hermes"), "TMPDIR": str(work),
                        "TERMINAL_TEMP_DIR": str(work), "PYTHONDONTWRITEBYTECODE": "1",
                        "PYTHONPATH": source + ":" + packages})
            code = "\n".join([
                "import json, pathlib, os",
                "from tools.environments.local import LocalEnvironment",
                "env = LocalEnvironment(cwd=os.getcwd(), timeout=1)",
                "try:",
                "    first = env.execute('export A19_TEST=preserved; mkdir -p child; cd child; printf first')",
                "    second = env.execute('printf \\\"%s:%s\\\\n\\\" \\\"$A19_TEST\\\" \\\"${PWD##*/}\\\"')",
                "    print(json.dumps({'first': first, 'second': second}))",
                "    assert first['returncode'] == second['returncode'] == 0",
                "    assert second['output'].strip() == 'preserved:child', second",
                "finally:",
                "    env.cleanup()",
            ])
            for strategy in ("bubblewrap", "landlock-setpriv"):
                if strategy not in available:
                    continue
                wrappers[strategy] = wrappers[strategy][:-1]
                for path in (source, packages):
                    if strategy == "bubblewrap":
                        wrappers[strategy] += ["--ro-bind", path, path]
                    else:
                        wrappers[strategy] += ["--landlock-rule", f"path-beneath:{rights}:{path}"]
                if strategy == "bubblewrap":
                    for key in ("HERMES_HOME", "TMPDIR", "TERMINAL_TEMP_DIR", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH"):
                        wrappers[strategy] += ["--setenv", key, env[key]]
                wrappers[strategy] += ["--"]
                run(strategy, "hermes_native", [source + "/venv/bin/python", "-c", code])
        expected_hash = hashlib.sha256((work / "input.txt").read_bytes().upper()).hexdigest()
        failures = []
        for row in rows:
            if row["kind"] != "availability" and row["exit"] != 0:
                failures.append(f"{row['strategy']} {row['kind']} exit {row['exit']}")
            if row["kind"] == "shell_tool" and row["stdout"] != "A19" + str((work / "input.txt").stat().st_size) + "\n":
                failures.append(f"{row['strategy']} shell output mismatch")
            if row["kind"] == "marker_lifecycle" and row["stdout"] != "A19-READY\n":
                failures.append(f"{row['strategy']} lifecycle marker mismatch")
            if row["kind"] == "file_task" and row["exit"] == 0:
                if json.loads(row["stdout"])["sha256"] != expected_hash:
                    failures.append("file task output mismatch")
            if row["kind"] == "escape" and row["exit"] == 0:
                probes = json.loads(row["stdout"])
                for name, result in probes.items():
                    allowed = row["strategy"] == "bare" or name == "inside_write"
                    if (result == "ALLOWED") != allowed:
                        failures.append(f"{row['strategy']} {name}: {result}")
        summary = {}
        for strategy in available:
            summary[strategy] = {}
            for kind in ("startup_exit", "shell_tool", "file_task"):
                values = [r["wall_ms"] for r in rows if r["strategy"] == strategy and r["kind"] == kind and r["exit"] == 0]
                summary[strategy][kind] = {"n": len(values), "median_ms": statistics.median(values), "min_ms": min(values), "max_ms": max(values)}
        report = {"host": platform.node(), "kernel": platform.release(), "elapsed_s": time.perf_counter() - start,
                  "scope": "tiny synthetic probes; not real Hermes E2E; startup_exit includes teardown",
                  "summary": summary, "rows": rows, "failures": failures}
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"summary": summary, "failures": failures, "elapsed_s": report["elapsed_s"]}, indent=2))
        if failures:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
