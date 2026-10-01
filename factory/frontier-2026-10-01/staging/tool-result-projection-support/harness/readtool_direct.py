"""readtool guard, $0 portion only: build evals/readtool's deterministic hostile workspace and call
the real ``read_file`` tool directly (no model, no AIAgent) on each fixture; print a digest per
call so two trees can be compared. Run under guarded_run.py.

Usage: guarded_run.py <repo> readtool_direct.py <out.json>
"""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

OUT = sys.argv[1]
from evals.readtool.fixtures import build_workspace  # noqa: E402
from tools.file_tools import read_file_tool  # noqa: E402

root = build_workspace(Path(tempfile.mkdtemp(prefix="readtool-", dir=os.environ["TMPDIR"])) / "ws")
calls = [
    ("package-lock.json", {}), ("package-lock.json", {"offset": 40000, "limit": 50}),
    ("src/app.min.js", {}), ("logs/server.log", {"offset": 149900, "limit": 200}),
    ("data/report.txt", {"offset": 500}), ("config/overrides.yaml", {}),
    ("AGENT.md", {}), ("AGENTS.md", {}), ("data/data.txt", {}), ("logs/live.pipe", {}),
]
notes = next((p for p in (root / "notes").iterdir()), None) if (root / "notes").is_dir() else None
if notes is not None:
    calls.append((str(notes.relative_to(root)), {}))
results = []
for rel, kw in calls:
    out = read_file_tool(str(root / rel), task_id="readtool-direct", **kw)
    text = out.replace(str(root), "<ROOT>")
    results.append({"path": rel, "kwargs": kw, "chars": len(text),
                    "sha256": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16],
                    "head": text[:120]})
Path(OUT).write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps([(r["path"], r["chars"], r["sha256"]) for r in results]))
