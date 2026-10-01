#!/usr/bin/env python3
"""Round-4 privacy scan: tools/privacy_scan.py unchanged, plus a completeness check over the whole directory.

Why: the round-3 scan (tools/privacy_scan_r3.py) loaded privacy_scan.py with importlib, which wrote
tools/__pycache__/privacy_scan.cpython-314.pyc. That file embedded an absolute host path, and the scan never
saw it, because privacy_scan.publishable() lists tools/ with iterdir() + is_file() and skips subdirectories.

What this adds:
  1. Never writes bytecode (sys.dont_write_bytecode is set before anything is imported; run it with python3 -B too).
  2. Walks every file under the staging directory (os.walk, symlinks not followed), except run/, which is
     local-only as a whole and is not walked. Each file must match a publishable rule or a local-only rule:
       publishable  STAGING.md, body.md, *.patch, receipts/*.json, raw/r<round>_*, tools/*.py (direct children only)
       local-only   run/ (whole tree), other direct children of raw/ (r20261001-01 outputs), tools/sandbox.sh
     Any other file (for example anything inside tools/__pycache__/, a dotfile or a symlink) is "unclassified".
  3. Runs privacy_scan.py's checks (absolute paths, hostname, local private terms; never printed) over the
     publishable AND the unclassified files.
  4. Flags binary files (a NUL byte or invalid UTF-8) among them, and counts absolute-path tokens in their raw bytes
     (privacy_scan.ABS cannot see a path that follows a marshal length byte, because of its look-behind).
  5. Flags any __pycache__ directory or *.pyc / *.pyo file outside run/.
Exit 1 on any privacy_scan.py flag, any unclassified file, any binary file or any bytecode.

--out raw/r4_<name>.txt writes the report there as well (that one path is left out of the walk because it is being
rewritten), then reads the written file back and appends a self-check line with the same checks.
Usage: XF_PRIVATE_TERMS=... PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r4.py [--out raw/r4_x.txt]
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # first statement after the docstring: no __pycache__ in tools/, ever

import contextlib
import importlib.util
import io
import os
import re
import socket
from pathlib import Path

_spec = importlib.util.spec_from_file_location("privacy_scan", Path(__file__).resolve().parent / "privacy_scan.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)
HERE = ps.HERE

RAW_ROUND = re.compile(r"r[1-9][0-9]*_")
ABS_BYTES = re.compile(rb"/(?:mnt|tmp|home|workspace|root|var|srv|opt)/[^\s\"'`),\]\x00-\x1f]*")


def classify(rel: str) -> str:
    parts = rel.split("/")
    if len(parts) == 1:
        return "publishable" if rel in ("STAGING.md", "body.md") or rel.endswith(".patch") else "unclassified"
    if len(parts) != 2:
        return "unclassified"
    top, name = parts
    if top == "receipts":
        return "publishable" if name.endswith(".json") else "unclassified"
    if top == "raw":
        return "publishable" if RAW_ROUND.match(name) else "local-only"
    if top == "tools":
        if name == "sandbox.sh":
            return "local-only"
        return "publishable" if name.endswith(".py") else "unclassified"
    return "unclassified"


def walk(skip: str | None):
    pub, local, unc, bytecode = [], [], [], []
    for root, dirs, files in os.walk(HERE, followlinks=False):
        rroot = Path(root).relative_to(HERE).as_posix()
        if rroot == ".":
            dirs[:] = [d for d in dirs if d != "run"]
        for d in list(dirs):
            rel = (Path(rroot) / d).as_posix() if rroot != "." else d
            if d == "__pycache__":
                bytecode.append(rel + "/")
            if (Path(root) / d).is_symlink():
                unc.append(rel + " (symlink to a directory, not followed)")
        for f in sorted(files):
            rel = (Path(rroot) / f).as_posix() if rroot != "." else f
            if rel == skip:
                continue
            if f.endswith((".pyc", ".pyo")):
                bytecode.append(rel)
            if (Path(root) / f).is_symlink():
                unc.append(rel + " (symlink)")
                continue
            {"publishable": pub, "local-only": local, "unclassified": unc}[classify(rel)].append(rel)
    return sorted(pub), sorted(local), sorted(unc), sorted(bytecode)


def is_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def self_check(path: Path) -> tuple[str, bool]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    low = text.lower()
    host = socket.gethostname()
    terms = [t.strip().lower() for t in os.environ.get("XF_PRIVATE_TERMS", "").split(",") if t.strip()]
    paths = [t for t in ps.ABS.findall(text) if t not in ps.REVIEWED]
    host_hits = low.count(host.lower()) if len(host) >= 3 else 0
    term_hits = sum(low.count(t) for t in terms)
    binary = int(is_binary(data))
    bad = bool(paths or host_hits or term_hits or binary)
    line = (f"self-check of this output file ({path.relative_to(HERE).as_posix()}, everything above this line): "
            f"abs_path={len(paths)}\thostname={host_hits}\tterms={term_hits}\tbinary={binary}")
    return line, bad


def main(argv: list[str]) -> int:
    out = None
    if len(argv) == 2 and argv[0] == "--out" and re.fullmatch(r"raw/r4_[\w.-]+\.txt", argv[1]):
        out = argv[1]
    elif argv:
        print("usage: privacy_scan_r4.py [--out raw/r4_<name>.txt]", file=sys.stderr)
        return 2
    pub, local, unc, bytecode = walk(out)
    scanned = [HERE / p for p in pub] + [HERE / p.split(" (")[0] for p in unc if "(symlink" not in p]
    ps.publishable = lambda: scanned
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print("# r4 privacy scan: XF_PRIVATE_TERMS=<local list> PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r4.py"
              + (f" --out {out}" if out else ""))
        print(f"bytecode writing: {'off' if sys.dont_write_bytecode else 'ON'} (sys.dont_write_bytecode={sys.dont_write_bytecode})")
        rc_ps = ps.main()
        binaries = []
        for p in scanned:
            data = p.read_bytes()
            if is_binary(data):
                binaries.append((p.relative_to(HERE).as_posix(), len(ABS_BYTES.findall(data))))
        n_pub = len(pub) + (1 if out else 0)
        print("completeness (round 4): every file under the staging directory walked, except run/ (local-only, not walked)")
        print(f"publishable by rule: {n_pub}" + (" (including this output file, checked after writing)" if out else ""))
        print(f"local-only by rule: {len(local)} (raw/ r20261001-01 outputs and tools/sandbox.sh; run/ not walked)")
        print(f"unclassified: {len(unc)}")
        for u in unc:
            print(f"unclassified\t{u}")
        print(f"binary (NUL byte or invalid UTF-8) among publishable and unclassified: {len(binaries)}")
        for rel, n in binaries:
            print(f"binary\t{rel}\tabs_path_bytes={n}")
        print(f"bytecode outside run/ (__pycache__ or *.pyc/*.pyo): {len(bytecode)}")
        for b in bytecode:
            print(f"bytecode\t{b}")
        print(f"scanned by the privacy_scan.py checks: {len(scanned)} ({len(pub)} publishable + {len(scanned) - len(pub)} unclassified)"
              + ("; the output file is checked on the last line" if out else ""))
        fail = bool(rc_ps or unc or binaries or bytecode)
        print(f"result: {'FAIL' if fail else 'PASS'}")
    report = buf.getvalue()
    if out:
        target = HERE / out
        target.write_text(report)
        line, bad = self_check(target)
        fail = fail or bad
        with target.open("a") as fh:
            fh.write(line + "\n" + f"rc={1 if fail else 0}\n")
        report = target.read_text()
    else:
        report += f"rc={1 if fail else 0}\n"
    sys.stdout.write(report)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
