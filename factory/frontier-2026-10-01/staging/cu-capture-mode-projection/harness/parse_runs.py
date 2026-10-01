"""Parse run_tests.sh logs from X2 / X2b into per-file pass/fail counts (stdlib only). Prints JSON.

Usage: parse_runs.py <run dir>
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

FILE_LINE = re.compile(r"[✓✗] (tests/\S+\.py) \((?:(\d+)✓)? ?(?:(\d+)✗)?")
SUMMARY = re.compile(r"=== Summary: (\d+) files, (\d+) tests passed, (\d+) failed")
FAILED = re.compile(r"^FAILED (tests/\S+)")


def parse(log: pathlib.Path) -> dict:
    text = log.read_text(encoding="utf-8", errors="replace")
    files = {}
    for m in FILE_LINE.finditer(text):
        files[m.group(1)] = {"passed": int(m.group(2) or 0), "failed": int(m.group(3) or 0)}
    failed = sorted({m.group(1) for line in text.splitlines() if (m := FAILED.match(line.strip()))})
    s = SUMMARY.search(text)
    total = ({"files": int(s.group(1)), "passed": int(s.group(2)), "failed": int(s.group(3))} if s else
             {"passed": sum(f["passed"] for f in files.values()), "failed": sum(f["failed"] for f in files.values())})
    return {"files": files, "total": total, "failed_tests": failed}


def main() -> int:
    run = pathlib.Path(sys.argv[1])
    out = {log.stem: parse(log) for log in sorted(run.glob("*.log")) if log.name != "runner.log"}
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
