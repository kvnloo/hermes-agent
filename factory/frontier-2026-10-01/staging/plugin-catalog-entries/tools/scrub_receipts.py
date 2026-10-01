#!/usr/bin/env python3
"""Replace host paths and the hostname in receipts/*.json with placeholders.

Round 1 added the path scrub; round 2 added the hostname placeholder, marked tools/sandbox.sh
local-only, and moved every host location out of this file.

Placeholders:
  <staging>   this staging directory, i.e. the parent of tools/ (artifact paths become relative: raw/..., tools/...)
  <worktree>  the disposable hermes worktree the slice ran in   (literal taken from env XF_WORKTREE)
  <venv>      the hermes venv prefix                            (literal taken from env XF_VENV)
  <testhome>  the isolated HOME for catalog commands and tests  (literal taken from env XF_TESTHOME)
  <host>      the value of every "host" key

Unset env variables are skipped; on receipts that are already scrubbed the run is a no-op.
Files under raw/ are not rewritten: they stay local-only (public: false) and are pinned by
sha256 in the receipts. tools/sandbox.sh is cited by sha256 as it ran; its bytes hold host
paths, so it is marked local-only (public: false) rather than edited.
"""
from __future__ import annotations

import json
import os
import re
import socket
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _env(name: str) -> str | None:
    value = os.environ.get(name, "").rstrip("/")
    return value or None


# Order matters: longest prefixes first.
LOCATIONS = [
    (str(HERE) + "/", "<staging>/"),
    (str(HERE), "<staging>"),
    (_env("XF_WORKTREE"), "<worktree>"),
    (_env("XF_TESTHOME"), "<testhome>"),
    (_env("XF_VENV"), "<venv>"),
]
REPLACEMENTS = [(re.compile(re.escape(p)), rep) for p, rep in LOCATIONS if p] + [
    (re.compile(r"--stars-file /nonexistent"), "--stars-file <missing-file>"),
    (re.compile(r"--plugin-dir <<staging>"), "--plugin-dir {<staging>"),
    (re.compile(r"fixed-manifest> --manifest-json"), "fixed-manifest} --manifest-json"),
    (re.compile(r"\[--plugin-dir-override <staging>/run/variants/<variant>\]"), "[--plugin-dir-override <staging>/run/variants/{variant}]"),
]
LOCAL_ONLY_TOOLS = {"tools/sandbox.sh"}
ABS = re.compile(r"(?<![\w<$])/(mnt|tmp|home|workspace|root|var|srv|opt)/")
PRIVACY_R1 = ("local aggregate (synthetic canary text only; no state.db, logs or credentials read). "
              "Host paths replaced by placeholders <staging>, <worktree>, <venv>, <testhome>; artifact paths "
              "are relative to the staging directory. raw/ outputs are local-only (public: false) and still "
              "carry host paths.")
PRIVACY = ("local aggregate (synthetic canary text only; no state.db, logs or credentials read). "
           "Host paths and the hostname replaced by placeholders <staging>, <worktree>, <venv>, <testhome>, "
           "<host>; artifact paths are relative to the staging directory. raw/ outputs and tools/sandbox.sh "
           "are local-only (public: false) and still carry host paths.")


def scrub(value):
    if isinstance(value, str):
        for pat, rep in REPLACEMENTS:
            value = pat.sub(rep, value)
        return value
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            v = scrub(v)
            if k == "path" and isinstance(v, str) and v.startswith("<staging>/"):
                v = v[len("<staging>/"):]
            if k == "host" and isinstance(v, str):
                v = "<host>"
            out[k] = v
        if out.get("path") in LOCAL_ONLY_TOOLS:
            out.setdefault("public", False)
        return out
    return value


def main() -> int:
    bad = 0
    hostname = socket.gethostname()
    for p in sorted((HERE / "receipts").glob("*.json")):
        data = json.loads(p.read_text())
        data = scrub(data)
        privacy = str(data.get("privacy", ""))
        legacy = "scrub paths before any public freeze" in privacy or privacy in (PRIVACY_R1, PRIVACY)
        if legacy:
            data["privacy"] = PRIVACY
            for art in data.get("artifacts", []):
                if isinstance(art, dict) and str(art.get("path", "")).startswith("raw/"):
                    art.setdefault("public", False)
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        left = ABS.findall(text)
        if left:
            bad += 1
            print(f"{p.name}: {len(left)} absolute path(s) left", file=sys.stderr)
        if len(hostname) >= 3 and hostname in text:
            bad += 1
            print(f"{p.name}: the hostname is still present", file=sys.stderr)
        p.write_text(text)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
