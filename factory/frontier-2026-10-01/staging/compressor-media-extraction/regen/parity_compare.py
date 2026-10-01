#!/usr/bin/env python3
"""Compare two scripts/run_tests.sh logs (base vs head) as pass/fail sets.

    python3 parity_compare.py base.log head.log [--json OUT]

Parses the per-file status lines ("[..] ✓|✗ tests/x.py (N✓ M✗, t)") and the per-test
"FAILED|ERROR tests/x.py::id" lines. Identical means: same file set, same per-file status,
same failing test-id set. Exit 0 only when identical.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FILE_RE = re.compile(r"\] ([✓✗]) (tests/\S+\.py) \(([^)]*)\)")
FAIL_RE = re.compile(r"\b(FAILED|ERROR) (tests/\S+?\.py(?:::\S+)?)(?:\s|$)")
SUMMARY_RE = re.compile(r"=== Summary: .* ===")


def parse(path: Path) -> dict:
    files: dict[str, dict] = {}
    failing: set[str] = set()
    summary = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = FILE_RE.search(line)
        if m:
            files[m.group(2)] = {"status": m.group(1), "counts": m.group(3).rsplit(",", 1)[0].strip()}
            continue
        m = FAIL_RE.search(line)
        if m:
            failing.add(m.group(2))
        m = SUMMARY_RE.search(line)
        if m:
            summary = m.group(0)
    return {"files": files, "failing": failing, "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path)
    ap.add_argument("head", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    b, h = parse(a.base), parse(a.head)
    only_base = sorted(set(b["files"]) - set(h["files"]))
    only_head = sorted(set(h["files"]) - set(b["files"]))
    status_diff = sorted(
        f for f in set(b["files"]) & set(h["files"]) if b["files"][f]["status"] != h["files"][f]["status"]
    )
    count_diff = sorted(
        f for f in set(b["files"]) & set(h["files"]) if b["files"][f]["counts"] != h["files"][f]["counts"]
    )
    fail_only_base = sorted(b["failing"] - h["failing"])
    fail_only_head = sorted(h["failing"] - b["failing"])
    identical = not (only_base or only_head or status_diff or fail_only_base or fail_only_head)
    report = {
        "identical": identical,
        "files_base": len(b["files"]),
        "files_head": len(h["files"]),
        "failing_files_base": sorted(f for f, v in b["files"].items() if v["status"] == "✗"),
        "failing_files_head": sorted(f for f, v in h["files"].items() if v["status"] == "✗"),
        "failing_ids_base": sorted(b["failing"]),
        "failing_ids_head": sorted(h["failing"]),
        "files_only_base": only_base,
        "files_only_head": only_head,
        "status_differs": status_diff,
        "per_file_counts_differ": count_diff,
        "failing_only_base": fail_only_base,
        "failing_only_head": fail_only_head,
        "summary_base": b["summary"],
        "summary_head": h["summary"],
    }
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if a.json:
        a.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
