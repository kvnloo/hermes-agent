"""Replace local absolute paths and the local user name in run outputs with placeholders (stdlib only).

Raw logs are kept for reading, never for re-hashing (no receipt pins a raw file), so this rewrites them in place.
Usage: sanitize_raw.py <dir>...   Prints one line per changed file and exits 1 if any path-like residue remains.
"""
from __future__ import annotations

import pathlib
import re
import sys

RULES = [
    (re.compile(r"/[^\s\"']*?/wt/(?:staging|stfix)/cu-capture-mode-projection"), "<worktree>"),
    (re.compile(r"/[^\s\"']*?/venv/bin/python[0-9.]*"), "<HERMES_PYTHON>"),
    (re.compile(r"/tmp/claude-\d+/[^\s\"']*?/scratchpad"), "<scratch>"),
    (re.compile(r"/var/tmp/hermes-pytest-\d+"), "<pytest-tmp>"),
    (re.compile(r"pytest-of-[A-Za-z0-9_.-]+"), "pytest-of-<user>"),
    (re.compile(r"/home/[A-Za-z0-9_.-]+"), "~"),
]
RESIDUE = re.compile(r"(?:/home/|/mnt/|/workspace/|/tmp/claude-|pytest-of-(?!<user>))")


def main() -> int:
    residue = []
    for root in map(pathlib.Path, sys.argv[1:]):
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            text = path.read_text(encoding="utf-8", errors="surrogateescape")
            new = text
            for rx, repl in RULES:
                new = rx.sub(repl, new)
            if new != text:
                path.write_text(new, encoding="utf-8", errors="surrogateescape")
                print(f"sanitized {path}")
            residue += [f"{path}: {m.group(0)}" for m in RESIDUE.finditer(new)]
    for line in residue:
        print(f"RESIDUE {line}")
    return 1 if residue else 0


if __name__ == "__main__":
    sys.exit(main())
