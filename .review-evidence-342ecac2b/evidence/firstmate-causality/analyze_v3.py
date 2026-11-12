#!/usr/bin/env python3
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
raw_root = ROOT / "evidence/firstmate-causality/v3/raw"
out = []
for path in sorted(raw_root.glob("*.json")):
    raw = json.loads(path.read_text())
    text = raw.get("stdout", "") + " " + json.dumps(raw.get("sessions", []))
    out.append({
        "runId": raw["runId"],
        "kanbanCreateMentions": len(re.findall(r"kanban_create", text)),
        "taskIds": sorted(set(re.findall(r"t_[0-9a-f]{8}", text))),
        "stdout": raw.get("stdout", ""),
    })
print(json.dumps({
    "runs": out,
}, indent=2))
