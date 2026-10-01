#!/usr/bin/env python3
"""Redact local paths, the host name and pytest temp roots from work/ in place (manifest r7).

Fixes the fresh verifier's BLOCKING privacy finding: the publishable set is everything
outside private/, and files under work/ printed absolute local paths and the host name.

Every needle comes from the command line, so this file names none of them.

Step 1 uses the same four replacements as the owner's claude/ledger copy (a3e1aa4878):
  <scratchpad dir> -> $S, <artifacts root> -> $ARTIFACTS, <live install root> -> <hermes-home>,
  <host name> -> <local-host>.
Step 2 also replaces pytest temp roots, which the ledger copy kept:
  <pytest base>/r-<random>/pytest-of-<user>/pytest-<n> -> <pytest-tmp>.

Before a file is rewritten, its original bytes are copied to private/as-written/<same path>
(never published), so the sha256 values the receipts cite stay checkable. Writes
work/r7/path_redaction_r7.json with sha256_as_written and sha256 for every rewritten file,
then scans the whole publishable set (everything outside private/) again.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def git_blob(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


ap = argparse.ArgumentParser()
ap.add_argument("staging")
ap.add_argument("--scratch", required=True)
ap.add_argument("--artifacts", required=True)
ap.add_argument("--hermes-home", required=True)
ap.add_argument("--host", required=True)
ap.add_argument("--pytest-base", required=True)
ap.add_argument("--user", required=True)
ap.add_argument("--ledger-tsv", required=True, help="<git blob sha>\\t<repo path> rows of claude/ledger a3e1aa4878")
ap.add_argument("--ledger-prefix", required=True)
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

os.chdir(a.staging)
OUT = "work/r7/path_redaction_r7.json"

step1 = [
    (a.scratch.encode(), b"$S", "<scratchpad dir>"),
    (a.artifacts.encode(), b"$ARTIFACTS", "<artifacts root>"),
    (a.hermes_home.encode(), b"<hermes-home>", "<live install root>"),
    (a.host.encode(), b"<local-host>", "<host name>"),
]
pytest_re = re.compile(
    re.escape(a.pytest_base.encode()) + rb"/r-[A-Za-z0-9_]+/pytest-of-" + re.escape(a.user.encode()) + rb"/pytest-[0-9]+"
)

ledger = {}
for line in open(a.ledger_tsv, encoding="utf-8").read().splitlines():
    parts = line.split("\t")
    if len(parts) == 2 and parts[1].startswith(a.ledger_prefix):
        ledger[parts[1][len(a.ledger_prefix):]] = parts[0]

cite_text = {}
for r in sorted(glob.glob("receipts/*.json")):
    cite_text[r] = open(r, encoding="utf-8").read()
for extra in ("work/r3/prove/prove_results.json", "work/r5/prove/prove_results.json", "work/r2/prove/prove_results.json"):
    if os.path.exists(extra):
        cite_text[extra] = open(extra, encoding="utf-8").read()

files = []
for dp, dn, fn in os.walk("work"):
    dn.sort()
    if dp.startswith("work/r7"):
        continue
    for f in sorted(fn):
        p = os.path.join(dp, f)
        orig = open(p, "rb").read()
        b = orig
        counts = {}
        for needle, repl, label in step1:
            n = b.count(needle)
            if n:
                counts[label] = n
                b = b.replace(needle, repl)
        s1 = b
        b, n = pytest_re.subn(b"<pytest-tmp>", b)
        if n:
            counts["<pytest base>/r-*/pytest-of-<user>/pytest-N"] = n
        if b == orig:
            continue
        if p.endswith(".json"):
            json.loads(b.decode("utf-8"))  # still valid JSON
        h0 = sha256(orig)
        rec = {
            "path": p,
            "sha256_as_written": h0,
            "sha256": sha256(b),
            "git_blob": git_blob(b),
            "bytes_as_written": len(orig),
            "bytes": len(b),
            "replacements": counts,
            "original_copy": "private/as-written/" + p,
            "ledger_a3e1aa4878_blob": ledger.get(p),
            "step1_equals_ledger": ledger.get(p) == git_blob(s1),
            "final_equals_ledger": ledger.get(p) == git_blob(b),
            "as_written_hash_cited_in": sorted(k for k, t in cite_text.items() if h0 in t),
        }
        files.append(rec)
        if not a.dry_run:
            dst = os.path.join("private", "as-written", p)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                assert sha256(open(dst, "rb").read()) == h0, dst
            else:
                with open(dst, "wb") as fh:
                    fh.write(orig)
            assert sha256(open(dst, "rb").read()) == h0, dst
            with open(p, "wb") as fh:
                fh.write(b)

# Re-scan the publishable set (everything outside private/).
generic = [
    ("abs mount path", re.compile(rb"/" + rb"mnt/")),
    ("abs workspace path", re.compile(rb"/" + rb"workspace/")),
    ("abs home path", re.compile(rb"/" + rb"home/[A-Za-z0-9_]")),
    ("claude scratch path", re.compile(rb"/" + rb"tmp/claude-")),
    ("var tmp path", re.compile(rb"/" + rb"var/tmp/")),
    ("pytest user dir", re.compile(rb"pytest-of-")),
    ("host name", re.compile(re.escape(a.host.encode()), re.I)),
    ("local user", re.compile(rb"(?<![A-Za-z0-9])" + re.escape(a.user.encode()) + rb"(?![A-Za-z0-9])")),
    ("artifacts root", re.compile(re.escape(a.artifacts.encode()))),
    ("scratchpad dir", re.compile(re.escape(a.scratch.encode()))),
    ("live install root", re.compile(re.escape(a.hermes_home.encode()))),
    ("private IPv4", re.compile(rb"(?<![0-9.])(?:10\.[0-9]{1,3}|192\.168|172\.(?:1[6-9]|2[0-9]|3[01])|100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7]))\.[0-9]{1,3}\.[0-9]{1,3}(?![0-9])")),
    ("email", re.compile(rb"(?<![A-Za-z0-9._%+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
]
# Known matches that are not local data: upstream #124151's own runbook text and scanner needle tuples.
allow = {
    ("work/pr124151.diff", "abs home path"): "upstream #124151 diff text (a container path in its runbook), not a local path",
    ("work/r2/pr124151.diff", "abs home path"): "upstream #124151 diff text (a container path in its runbook), not a local path",
    ("work/r2/make_receipts_r2.py", "abs mount path"): "scanner needle tuple (generic directory names only)",
    ("work/r2/make_receipts_r2.py", "abs workspace path"): "scanner needle tuple (generic directory names only)",
    ("work/r3/make_receipts_r3.py", "abs mount path"): "scanner needle assert (generic directory names only)",
    ("work/r3/make_receipts_r3.py", "abs workspace path"): "scanner needle assert (generic directory names only)",
    ("work/r4/make_receipts_r4.py", "abs mount path"): "scanner needle tuple (generic directory names only)",
    ("work/r4/make_receipts_r4.py", "abs workspace path"): "scanner needle tuple (generic directory names only)",
    ("work/r5/make_receipts_r5.py", "abs mount path"): "scanner needle tuple (generic directory names only)",
    ("work/r5/make_receipts_r5.py", "abs workspace path"): "scanner needle tuple (generic directory names only)",
    ("work/r7/redact_r7.py", "pytest user dir"): "this script's docstring and regex fragment (no user name)",
}
noreply = re.compile(rb"@(users\.noreply\.github\.com|anthropic\.com)$|^noreply@|^git@github\.com$")
hits, allowed, scanned = [], [], 0
for dp, dn, fn in os.walk("."):
    if dp == "./private" or dp.startswith("./private/"):
        dn[:] = []
        continue
    for f in fn:
        p = os.path.relpath(os.path.join(dp, f), ".")
        if p == OUT:
            continue
        scanned += 1
        b = open(p, "rb").read()
        for label, rx in generic:
            for m in rx.finditer(b):
                tok = m.group(0)
                if label == "email" and (noreply.search(tok) or tok.endswith(b"@users.noreply.github.com")):
                    continue
                line = b.count(b"\n", 0, m.start()) + 1
                if (p, label) in allow:
                    allowed.append({"path": p, "line": line, "class": label, "why": allow[(p, label)]})
                else:
                    hits.append({"path": p, "line": line, "class": label})

summary = {
    "files_rewritten": len(files),
    "step1_equals_ledger": sum(r["step1_equals_ledger"] for r in files),
    "final_equals_ledger": sum(r["final_equals_ledger"] for r in files),
    "files_with_pytest_tmp": sum(1 for r in files if any(k.startswith("<pytest base>") for k in r["replacements"])),
    "as_written_hash_cited": sum(1 for r in files if r["as_written_hash_cited_in"]),
    "publishable_files_scanned": scanned,
    "scan_hits": len(hits),
    "scan_allowed": len(allowed),
}
out = {
    "id": "path-redaction-r7",
    "item": "memory-prefetch-metric",
    "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "label": "OBSERVED",
    "why": "fresh verifier BLOCKING privacy finding (check c): files under work/ printed absolute local paths and the host name",
    "command": "cd <staging>/work/r7 && PYTHONDONTWRITEBYTECODE=1 python3 -B redact_r7.py <staging> --scratch <scratchpad dir> "
    "--artifacts <artifacts root> --hermes-home <live install root> --host <host name> --pytest-base <pytest base> "
    "--user <local user> --ledger-tsv <run>/ledger_tree.tsv --ledger-prefix factory/frontier-2026-10-01/staging/memory-prefetch-metric/",
    "rules": [
        {"step": 1, "from": "<scratchpad dir>", "to": "$S"},
        {"step": 1, "from": "<artifacts root>", "to": "$ARTIFACTS"},
        {"step": 1, "from": "<live install root>", "to": "<hermes-home>"},
        {"step": 1, "from": "<host name>", "to": "<local-host>"},
        {"step": 2, "from": "<pytest base>/r-<random>/pytest-of-<local user>/pytest-<n>", "to": "<pytest-tmp>"},
    ],
    "step1_note": "step 1 is the owner's claude/ledger a3e1aa4878 scrub; step1_equals_ledger says it reproduces that copy's blob byte for byte",
    "originals": "private/as-written/<path>: byte-identical to the file as written (sha256_as_written), kept for checking the receipts' cited hashes; private/ is never published",
    "receipts_unchanged": True,
    "summary": summary,
    "files": files,
    "scan": {"hits": hits, "allowed": allowed},
    "dry_run": a.dry_run,
}
if not a.dry_run:
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")
print(json.dumps(summary, indent=1))
for h in hits[:40]:
    print("HIT", h)
sys.exit(1 if hits else 0)
