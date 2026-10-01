#!/usr/bin/env python3
"""Run one upstream eval harness (E12 guards) under the loopback guard, with an optional
non-invasive counter for the compaction observer.

usage: chs_guard_wrap.py <repo_root> <harness.py> <counts.json> [harness args...]

The counter wraps hermes_cli.lifecycle.has_hook/invoke_hook (so a fold-in that gates on has_hook()
still dispatches) and agent.conversation_compression._commit_compaction (to count durable commits).
It never changes a return value. On main there is no fire site, so fires stay 0 by construction.
"""

from __future__ import annotations

import json
import os
import runpy
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import chs_loopback_guard  # noqa: E402,F401

repo, harness, counts_path, *rest = sys.argv[1:]
sys.path.insert(0, repo)
os.chdir(repo)

counts = {"hook_fires": [], "commits": []}

import hermes_cli.lifecycle as lc  # noqa: E402
import agent.conversation_compression as cc  # noqa: E402

_has, _inv, _commit = lc.has_hook, lc.invoke_hook, cc._commit_compaction


def has_hook(name):
    return True if name == "on_compression_complete" else _has(name)


def invoke_hook(name, **kw):
    if name == "on_compression_complete":
        counts["hook_fires"].append({"in_place": kw.get("in_place"), "same_ids": kw.get("session_id") == kw.get("old_session_id")})
    return _inv(name, **kw)


def commit(*a, **k):
    out = _commit(*a, **k)
    counts["commits"].append({"split_status": out.split_status, "succeeded": out.session_commit_succeeded})
    return out


lc.has_hook, lc.invoke_hook, cc._commit_compaction = has_hook, invoke_hook, commit
sys.argv = [harness, *rest]
rc = 0
try:
    runpy.run_path(harness, run_name="__main__")
except SystemExit as exc:
    rc = int(exc.code or 0)
finally:
    with open(counts_path, "w", encoding="utf-8") as fh:
        json.dump({"rc": rc, "hook_fires": len(counts["hook_fires"]),
                   "commits_total": len(counts["commits"]),
                   "commits_succeeded": sum(1 for c in counts["commits"] if c["succeeded"]),
                   "detail": counts}, fh, indent=1)
sys.exit(rc)
