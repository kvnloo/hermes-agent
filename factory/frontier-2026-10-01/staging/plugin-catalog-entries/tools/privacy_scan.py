#!/usr/bin/env python3
"""Privacy scan of the publishable part of this staging directory (round 2).

Checks every publishable file for:
  abs_path   absolute paths under /mnt /tmp /home /workspace /root /var /srv /opt (the token is printed so a
             reviewer can see it is generic; a real host path must be fixed before publishing, never published)
  hostname   this machine's hostname, read at run time (never printed)
  terms      a local list of private terms from env XF_PRIVATE_TERMS, comma-separated (never printed; only the
             number of terms and the hit counts are reported)

Publishable set: STAGING.md, body.md, *.patch, receipts/*.json, raw/r1_*, raw/r2_*, tools/* except
tools/sandbox.sh (local-only, public: false). raw/ outputs from r01 and run/ are local-only and not scanned.
Usage: XF_PRIVATE_TERMS=... python3 tools/privacy_scan.py   (exit 1 on any hostname/terms hit or unreviewed path)
"""
from __future__ import annotations

import os
import re
import socket
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LOCAL_ONLY = {"tools/sandbox.sh"}
ABS = re.compile(r"(?<![\w<$])/(?:mnt|tmp|home|workspace|root|var|srv|opt)/[^\s\"'`),\]]*")
# Generic tokens reviewed in round 2; none names this machine.
REVIEWED = {"/tmp/hh"}  # tools/t1_probe.py: HERMES_HOME fallback inside the sandbox (file pinned by sha256)


def publishable() -> list[Path]:
    files = [HERE / "STAGING.md", HERE / "body.md", *sorted(HERE.glob("*.patch")), *sorted((HERE / "receipts").glob("*.json")),
             *sorted((HERE / "raw").glob("r1_*")), *sorted((HERE / "raw").glob("r2_*")), *sorted((HERE / "tools").iterdir())]
    return [p for p in files if p.is_file() and str(p.relative_to(HERE)) not in LOCAL_ONLY]


def main() -> int:
    hostname = socket.gethostname()
    terms = [t.strip().lower() for t in os.environ.get("XF_PRIVATE_TERMS", "").split(",") if t.strip()]
    bad = 0
    print(f"terms from local list: {len(terms)}; hostname check: {'on' if len(hostname) >= 3 else 'off'}")
    for p in publishable():
        text = p.read_text(errors="replace")
        low = text.lower()
        paths = ABS.findall(text)
        unreviewed = [t for t in paths if t not in REVIEWED]
        host_hits = low.count(hostname.lower()) if len(hostname) >= 3 else 0
        term_hits = sum(low.count(t) for t in terms)
        reviewed = sorted(set(paths) - set(unreviewed))
        print(f"{p.relative_to(HERE)}\tabs_path={len(unreviewed)}\thostname={host_hits}\tterms={term_hits}"
              + (f"\treviewed_generic={','.join(reviewed)}" if reviewed else ""))
        if unreviewed or host_hits or term_hits:
            bad += 1
    print(f"files flagged: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
