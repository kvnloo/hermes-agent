#!/usr/bin/env python3
"""Round-6 privacy scan: everything outside private/ is publishable and is scanned; nothing else is skipped.

Why: the round-6 verifier found local-only material (the r20261001-01 raw outputs, tools/sandbox.sh and run/) sitting in
publishable locations. A publisher that applies the rule "publish everything outside private/" would have published it,
and tools/privacy_scan_r4.py never walked run/, so the host name in the pinned clone's git reflogs was never checked.
Round 6 moved all of it, byte-identical, to private/<same path> (list: private/MOVED-r6.tsv).

What this does:
  1. Never writes bytecode (sys.dont_write_bytecode is set before anything is imported; run it with python3 -B too).
  2. Walks every file under the staging directory (os.walk, symlinks not followed). Only the top-level private/ tree is
     left out of the publishable walk. Each other file must match a publishable rule:
       STAGING.md, body.md, *.patch (top level), receipts/*.json, raw/r<round>_*, tools/*.py (direct children only)
     Any other file outside private/ (a symlink, a dotfile, a subdirectory of tools/ or raw/, tools/sandbox.sh, a
     leftover run/ tree) is "unclassified" and fails the scan.
  3. Runs tools/privacy_scan.py's checks unchanged (absolute paths, this machine's host name, a local list of private
     terms from XF_PRIVATE_TERMS; the name and the terms are never printed) over the publishable and unclassified files.
  4. Adds a local-login check (the account name as a whole word, so a longer public handle that starts with the same
     letters is not counted; never printed), a binary check (NUL byte or invalid UTF-8) and a bytecode check
     (__pycache__, *.pyc, *.pyo anywhere outside private/).
  5. Counts files under private/ and how many of them hold an absolute path, the host name or the login, for the record
     only (local-only, never published; not a failure).
Exit 1 on any privacy_scan.py flag, any login hit, any unclassified file, any binary file or any bytecode outside private/.

--out raw/r6_<name>.txt writes the report there too (that path is left out of the walk while it is rewritten), then reads
the written file back and appends a self-check line with the same checks.
Usage: XF_PRIVATE_TERMS=... PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r6.py [--out raw/r6_x.txt]
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # first statement after the docstring: no __pycache__ in tools/, ever

import contextlib
import getpass
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
PRIVATE = "private"

RAW_ROUND = re.compile(r"r[1-9][0-9]*_")
ABS_BYTES = re.compile(rb"/(?:mnt|tmp|home|workspace|root|var|srv|opt)/[^\s\"'`),\]\x00-\x1f]*")


def login_re() -> re.Pattern[bytes] | None:
    name = getpass.getuser().lower()
    if len(name) < 2:
        return None
    return re.compile(rb"(?<![a-z0-9])" + re.escape(name.encode()) + rb"(?![a-z0-9])")


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
        return "publishable" if RAW_ROUND.match(name) else "unclassified"
    if top == "tools":
        return "publishable" if name.endswith(".py") else "unclassified"
    return "unclassified"


def walk(skip: str | None):
    pub, unc, bytecode, private = [], [], [], []
    for root, dirs, files in os.walk(HERE, followlinks=False):
        rroot = Path(root).relative_to(HERE).as_posix()
        in_private = rroot == PRIVATE or rroot.startswith(PRIVATE + "/")
        for d in list(dirs):
            rel = (Path(rroot) / d).as_posix() if rroot != "." else d
            if (Path(root) / d).is_symlink():
                (private if in_private or rel == PRIVATE else unc).append(rel + " (symlink to a directory, not followed)")
            if d == "__pycache__" and not in_private:
                bytecode.append(rel + "/")
        for f in sorted(files):
            rel = (Path(rroot) / f).as_posix() if rroot != "." else f
            if rel == skip:
                continue
            if in_private:
                private.append(rel)
                continue
            if f.endswith((".pyc", ".pyo")):
                bytecode.append(rel)
            if (Path(root) / f).is_symlink():
                unc.append(rel + " (symlink)")
                continue
            {"publishable": pub, "unclassified": unc}[classify(rel)].append(rel)
    return sorted(pub), sorted(unc), sorted(bytecode), sorted(private)


def is_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def counts(data: bytes, host: str, login: re.Pattern[bytes] | None) -> tuple[int, int, int]:
    low = data.lower()
    host_hits = low.count(host.lower().encode()) if len(host) >= 3 else 0
    login_hits = len(login.findall(low)) if login else 0
    return len(ABS_BYTES.findall(data)), host_hits, login_hits


def self_check(path: Path, login: re.Pattern[bytes] | None) -> tuple[str, bool]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    low = text.lower()
    host = socket.gethostname()
    terms = [t.strip().lower() for t in os.environ.get("XF_PRIVATE_TERMS", "").split(",") if t.strip()]
    paths = [t for t in ps.ABS.findall(text) if t not in ps.REVIEWED]
    host_hits = low.count(host.lower()) if len(host) >= 3 else 0
    term_hits = sum(low.count(t) for t in terms)
    login_hits = len(login.findall(data.lower())) if login else 0
    binary = int(is_binary(data))
    bad = bool(paths or host_hits or term_hits or login_hits or binary)
    line = (f"self-check of this output file ({path.relative_to(HERE).as_posix()}, everything above this line): "
            f"abs_path={len(paths)}\thostname={host_hits}\tterms={term_hits}\tlogin={login_hits}\tbinary={binary}")
    return line, bad


def main(argv: list[str]) -> int:
    out = None
    if len(argv) == 2 and argv[0] == "--out" and re.fullmatch(r"raw/r6_[\w.-]+\.txt", argv[1]):
        out = argv[1]
    elif argv:
        print("usage: privacy_scan_r6.py [--out raw/r6_<name>.txt]", file=sys.stderr)
        return 2
    login = login_re()
    host = socket.gethostname()
    pub, unc, bytecode, private = walk(out)
    scanned = [HERE / p for p in pub] + [HERE / p.split(" (")[0] for p in unc if "(symlink" not in p]
    ps.publishable = lambda: scanned
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print("# r6 privacy scan: XF_PRIVATE_TERMS=<local list> PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r6.py"
              + (f" --out {out}" if out else ""))
        print(f"bytecode writing: {'off' if sys.dont_write_bytecode else 'ON'} (sys.dont_write_bytecode={sys.dont_write_bytecode})")
        print(f"login check: {'on (whole word)' if login else 'off'}")
        rc_ps = ps.main()
        login_files, binaries = [], []
        for p in scanned:
            data = p.read_bytes()
            rel = p.relative_to(HERE).as_posix()
            n_login = len(login.findall(data.lower())) if login else 0
            if n_login:
                login_files.append((rel, n_login))
            if is_binary(data):
                binaries.append((rel, len(ABS_BYTES.findall(data))))
        n_pub = len(pub) + (1 if out else 0)
        print("completeness (round 6): every file under the staging directory walked; only private/ is outside the publishable set")
        print(f"publishable by rule: {n_pub}" + (" (including this output file, checked after writing)" if out else ""))
        print(f"unclassified (outside private/ and matching no publishable rule): {len(unc)}")
        for u in unc:
            print(f"unclassified\t{u}")
        print(f"login hits among publishable and unclassified: {len(login_files)} files")
        for rel, n in login_files:
            print(f"login\t{rel}\thits={n}")
        print(f"binary (NUL byte or invalid UTF-8) among publishable and unclassified: {len(binaries)}")
        for rel, n in binaries:
            print(f"binary\t{rel}\tabs_path_bytes={n}")
        print(f"bytecode outside private/ (__pycache__ or *.pyc/*.pyo): {len(bytecode)}")
        for b in bytecode:
            print(f"bytecode\t{b}")
        p_abs = p_host = p_login = p_bin = 0
        for rel in private:
            fp = HERE / rel.split(" (")[0]
            if "(symlink" in rel or not fp.is_file():
                continue
            data = fp.read_bytes()
            a, h, lg = counts(data, host, login)
            p_abs += bool(a)
            p_host += bool(h)
            p_login += bool(lg)
            p_bin += is_binary(data)
        print(f"private/ (local-only, never published; for the record, not a failure): {len(private)} files; "
              f"with an absolute path {p_abs}, with the host name {p_host}, with the login {p_login}, binary {p_bin}")
        print(f"scanned by the privacy_scan.py checks: {len(scanned)} ({len(pub)} publishable + {len(scanned) - len(pub)} unclassified)"
              + ("; the output file is checked on the last line" if out else ""))
        fail = bool(rc_ps or login_files or unc or binaries or bytecode)
        print(f"result: {'FAIL' if fail else 'PASS'}")
    report = buf.getvalue()
    if out:
        target = HERE / out
        target.write_text(report)
        line, bad = self_check(target, login)
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
