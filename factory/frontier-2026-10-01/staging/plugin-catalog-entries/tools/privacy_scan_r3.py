#!/usr/bin/env python3
"""Round-3 privacy scan: tools/privacy_scan.py unchanged, with raw/r3_* added to the publishable set.

privacy_scan.py is pinned by sha256 in RECHECK/r20261001-03, so it is loaded as is rather than edited.
Same checks, same output format, same exit code (1 on any hostname/terms hit or unreviewed path).
Usage: XF_PRIVATE_TERMS=... python3 tools/privacy_scan_r3.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("privacy_scan", Path(__file__).resolve().parent / "privacy_scan.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)
_base = ps.publishable


def publishable() -> list[Path]:
    extra = [p for p in sorted((ps.HERE / "raw").glob("r3_*")) if p.is_file()]
    return _base() + extra


ps.publishable = publishable

if __name__ == "__main__":
    raise SystemExit(ps.main())
