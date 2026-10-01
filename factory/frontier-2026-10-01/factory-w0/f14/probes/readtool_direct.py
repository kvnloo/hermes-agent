"""F14 readtool guard: the evals/readtool hostile-workspace fixtures driven by direct read_file calls.

No model, no network. Builds the fixture workspace with the worktree's own evals/readtool/fixtures.py,
then calls the worktree's tools.file_tools.read_file_tool once per fixture shape and checks the behaviour
the readtool README and results/SUMMARY.md say Hermes ships (line clamp, did-you-mean, stat guard for a
FIFO, binary sniffing, pagination). Writes <out>/readtool.json: {case: {verdict, marker, fingerprint, obs}}.

    python readtool_direct.py <worktree> <out-dir>
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
from pathlib import Path

WT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(WT))
sys.path.insert(0, str(WT / "evals" / "readtool"))
OUT.mkdir(parents=True, exist_ok=True)
WS = OUT / "ws"
WS.mkdir(exist_ok=False)
os.environ["TERMINAL_CWD"] = str(WS)
os.chdir(WS)

import fixtures as fx  # noqa: E402  (the worktree's evals/readtool/fixtures.py)

fx.build_workspace(WS)
from tools import file_tools  # noqa: E402

assert Path(file_tools.__file__).resolve().is_relative_to(WT), file_tools.__file__


def call(case: str, path: str, **kw):
    box: dict = {}

    def target():
        try:
            box["raw"] = file_tools.read_file_tool(path, task_id=f"f14-{case}", **kw)
        except BaseException as exc:  # recorded, never raised
            box["exc"] = f"{type(exc).__name__}: {exc}"

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(20)
    if t.is_alive():
        return None, "TIMEOUT(20s)"
    if "exc" in box:
        return None, box["exc"]
    raw = box["raw"]
    try:
        return json.loads(raw), None
    except Exception:
        return {"_raw": raw}, None


def norm(obj) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return s.replace(str(WS), "<ws>")


def text(d) -> str:
    return norm(d) if d is not None else ""


cases = {}


def record(case: str, d, err, checks: list[tuple[str, bool]]):
    failed = [name for name, ok in checks if not ok]
    if err:
        verdict, marker = "ERROR", err
    elif failed:
        verdict, marker = "FAIL", "failed: " + ", ".join(failed)
    else:
        verdict, marker = "PASS", ""
    obs = None
    if isinstance(d, dict):
        obs = {k: d.get(k) for k in ("success", "total_lines", "truncated", "next_offset", "is_binary",
                                     "file_size", "similar_files", "hint") if k in d}
        for k in ("error", "note"):
            if k in d:
                obs[k] = str(d[k]).replace(str(WS), "<ws>")[:300]
        if "content" in d:
            obs["content_chars"] = len(d.get("content") or "")
        obs = json.loads(norm(obs))
    cases[case] = {"verdict": verdict, "marker": marker,
                   "fingerprint": hashlib.sha256(text(d).encode()).hexdigest()[:16] if d is not None else None,
                   "obs": obs}


content = lambda d: (d or {}).get("content") or ""  # noqa: E731
blob = lambda d: text(d).lower()  # noqa: E731

# 1. 80K-line lockfile: paginated, not dumped whole.
d, e = call("lockfile_version", str(WS / "package-lock.json"))
record("lockfile_version", d, e, [
    ("lockfileVersion in first page", '"lockfileVersion": 3' in content(d)),
    ("paginated (truncated or next_offset)", bool((d or {}).get("truncated") or (d or {}).get("next_offset"))),
    ("first page under 2.7MB file size", len(content(d)) < 1_000_000),
])
# 2. one 600KB line: per-line clamp keeps the result far below the line length.
d, e = call("minified_backoff", str(WS / "src" / "app.min.js"))
record("minified_backoff", d, e, [
    ("read returned content", bool(content(d))),
    ("line clamped (< 600000 chars)", len(content(d)) < 600_000),
])
# 3. 150K-line log, ERROR near the tail: offset read lands on it.
d, e = call("log_error_hunt", str(WS / "logs" / "server.log"), offset=149_690, limit=20)
record("log_error_hunt", d, e, [
    ("error line at offset", fx.LOG_ERROR_REQ_ID in content(d)),
    ("total_lines 150000", (d or {}).get("total_lines") == 150_000),
])
# 4. past-EOF offset on a 412-line file.
d, e = call("past_eof", str(WS / "data" / "report.txt"), offset=500, limit=50)
record("past_eof", d, e, [
    ("no file content past EOF", "metric_0" not in content(d)),
    ("reports the 412-line length", "412" in text(d)),
])
# 5. empty file.
d, e = call("empty_config", str(WS / "config" / "overrides.yaml"))
record("empty_config", d, e, [
    ("not an error", not (d or {}).get("error")),
    ("no content lines", not re.search(r"\d+\|.", content(d))),
])
# 6. NFC/space-normalised spelling of an NFD + U+202F filename.
d, e = call("unicode_filename", str(WS / "notes" / fx.NOTES_NAME_CLEAN))
record("unicode_filename", d, e, [
    ("reaches the hostile-spelled file or suggests it",
     fx.NOTES_BULLET_3 in content(d) or any("Meeting" in str(s) for s in (d or {}).get("similar_files") or [])),
])
# 7. near-miss filename.
d, e = call("near_miss_filename", str(WS / "AGENT.md"))
record("near_miss_filename", d, e, [
    ("did-you-mean lists AGENTS.md", "agents.md" in blob(d)),
    ("does not silently read AGENTS.md", fx.AGENTS_BUILD_CMD not in content(d)),
])
# 8. FIFO: refused by the stat guard instead of blocking.
d, e = call("fifo_hang", str(WS / "logs" / "live.pipe"))
record("fifo_hang", d, e, [
    ("returned (no hang)", d is not None),
    ("refused as a special file", (d or {}).get("success") is False and "fifo" in blob(d)),
])
# 9. PNG bytes behind a .txt name.
d, e = call("lying_extension", str(WS / "data" / "data.txt"))
record("lying_extension", d, e, [
    ("flagged binary", (d or {}).get("is_binary") is True
     or "binary" in (str((d or {}).get("error") or "") + str((d or {}).get("note") or "")).lower()),
    ("no raw bytes returned", "\x89png" not in content(d).lower()),
])

(OUT / "readtool.json").write_text(json.dumps(cases, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: (v["verdict"], v["marker"]) for k, v in cases.items()}, indent=2, ensure_ascii=False))
print("READTOOL_DONE", flush=True)
