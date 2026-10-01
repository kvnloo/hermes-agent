#!/usr/bin/env python3
"""N02: which DEFAULT_CONFIG dotted keys does the `dotted keys` anchor row capture verbatim?

Flattens hermes_cli.config_defaults.DEFAULT_CONFIG the same way anchor_coverage.py does for N01
(every key path, intermediate dict nodes included), keeps the paths that contain a dot, and scans
each path alone with the production `dotted keys` row from agent/context_compressor.py. A path is
"fully matched" when one match equals the whole path. Misses are classified by why the row rejects
them. Leaf-only figures (paths whose value is not a dict) are reported beside the all-paths figures.

usage: config_key_coverage.py --checkout <tree at the head> --out <json>
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SEG = re.compile(r"[a-z][a-z0-9_]*\Z")          # a segment the row can match at all
SNAKE_LAST = re.compile(r"[a-z][a-z0-9]*_[a-z0-9_]*[a-z0-9]\Z")  # the row's last-segment rule
NAMED = ["terminal.backend", "compression.threshold", "compression.enabled", "browser.backend",
         "checkpoints.enabled", "compression.tail_mode", "plugins.stream_reasoning_deltas"]


def flat(d, pre=""):
    for k, v in d.items():
        key = f"{pre}{k}"
        yield key, isinstance(v, dict)
        if isinstance(v, dict):
            yield from flat(v, key + ".")


def why_missed(key: str) -> str:
    segs = key.split(".")
    if not all(SEG.match(s) for s in segs):
        return "a segment is not lowercase [a-z][a-z0-9_]* (uppercase, digit-first, hyphen, ...)"
    if "_" not in segs[-1]:
        return "last segment is one word (no underscore), e.g. terminal.backend"
    if not SNAKE_LAST.match(segs[-1]):
        return "last segment has an underscore but ends in _ or has no letter before it"
    return "other"


def tally(keys, row):
    full, partial, missed = [], [], []
    for k in keys:
        vals = [m.group(0) for m in row.finditer(k)]
        if k in vals:
            full.append(k)
        elif vals:
            partial.append((k, vals))
        else:
            missed.append(k)
    reasons: dict[str, list[str]] = {}
    for k in missed + [p[0] for p in partial]:
        reasons.setdefault(why_missed(k), []).append(k)
    n = len(keys)
    return {
        "dotted_paths": n,
        "fully_matched": len(full),
        "fully_matched_pct": round(100 * len(full) / n, 1) if n else None,
        "not_fully_matched": n - len(full),
        "not_fully_matched_pct": round(100 * (n - len(full)) / n, 1) if n else None,
        "partial_only": len(partial),
        "partial_examples": [[k, v] for k, v in partial[:10]],
        "misses_by_reason": {r: {"count": len(v), "examples": sorted(v)[:12]}
                             for r, v in sorted(reasons.items(), key=lambda kv: -len(kv[1]))},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    root = Path(a.checkout).resolve()
    sys.path.insert(0, str(root))
    from hermes_cli.config_defaults import DEFAULT_CONFIG
    import agent.context_compressor as cc

    row = next(p for name, p, _cap in cc._ANCHOR_PATTERNS if name == "dotted keys")
    paths = list(flat(DEFAULT_CONFIG))
    dotted_all = [k for k, _is_dict in paths if "." in k]
    dotted_leaf = [k for k, is_dict in paths if "." in k and not is_dict]
    named = {k: {"in_DEFAULT_CONFIG": k in dict(paths),
                 "row_values_when_scanned_alone": [m.group(0) for m in row.finditer(k)]} for k in NAMED}
    out = {
        "inputs": {
            "config_defaults_sha256": hashlib.sha256(
                (root / "hermes_cli" / "config_defaults.py").read_bytes()).hexdigest(),
            "context_compressor_sha256": hashlib.sha256(
                (root / "agent" / "context_compressor.py").read_bytes()).hexdigest(),
            "dotted_keys_row": row.pattern,
        },
        "flattened_paths_total": len(paths),
        "flattened_paths_without_dot": len(paths) - len(dotted_all),
        "all_dotted_paths": tally(dotted_all, row),
        "leaf_dotted_paths": tally(dotted_leaf, row),
        "named_examples": named,
    }
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
