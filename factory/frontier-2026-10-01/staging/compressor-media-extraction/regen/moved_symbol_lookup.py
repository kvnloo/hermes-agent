#!/usr/bin/env python3
"""Targeted lookup_sim census over exactly the moved functions (plus the facade's remaining defs).

The stock ``evals/codebase_navigability/lookup_sim.py`` samples a few thousand names from ~all
first-party symbols, so a 16-symbol move barely registers. This reuses its ``index``/``simulate``
policy unchanged and scores (a) every moved function and (b) every def/class still defined in the
facade, on both trees. Output is MODELED (simulated agent lookups), never observed agent behaviour.

    python moved_symbol_lookup.py <base> <head> <path/to/lookup_sim.py> --out OUT.json
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_media import FACADE, MOVED  # noqa: E402


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("lookup_sim", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _agg(rows):
    t = [r["tokens"] for r in rows]
    c = [r["calls"] for r in rows]
    return {
        "tasks": len(rows),
        "calls_total": sum(c),
        "tokens_total": sum(t),
        "tokens_mean": round(statistics.mean(t)) if t else 0,
        "tokens_p50": int(statistics.median(t)) if t else 0,
        "grep_hits_mean": round(statistics.mean(r["hits"] for r in rows), 2) if rows else 0,
        "file_lines_p50": int(statistics.median(r["file_lines"] for r in rows)) if rows else 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path)
    ap.add_argument("head", type=Path)
    ap.add_argument("lookup_sim", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ls = _load(a.lookup_sim)
    tok = ls.tokenizer()
    tok_name = "tiktoken o200k_base" if "tiktoken" in sys.modules else "bytes/4 fallback"
    bi, bf = ls.index(a.base)
    hi, hf = ls.index(a.head)
    moved_fns = [n for n in MOVED if n in bi and n in hi]  # constants are not indexed by lookup_sim
    facade_tree = ast.parse((a.head / FACADE).read_text(encoding="utf-8"))
    remaining = sorted({
        n.name for n in ast.walk(facade_tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("__")
    } & set(bi) & set(hi))
    out = {"tokenizer": tok_name, "label": "MODELED", "policy": "lookup_sim.simulate (grep + 200-line first read + 2,000-line paging)"}
    for label, names in (("moved_functions", moved_fns), ("facade_remaining_defs", remaining)):
        B = [ls.simulate(n, bi, bf, tok) for n in names]
        H = [ls.simulate(n, hi, hf, tok) for n in names]
        pairs = [(b, h) for b, h in zip(B, H) if b and h]
        out[label] = {
            "names": len(pairs),
            "base": _agg([b for b, _ in pairs]),
            "head": _agg([h for _, h in pairs]),
            "head_cheaper": sum(1 for b, h in pairs if h["tokens"] < b["tokens"]),
            "head_costlier": sum(1 for b, h in pairs if h["tokens"] > b["tokens"]),
            "equal": sum(1 for b, h in pairs if h["tokens"] == b["tokens"]),
            "rows": [
                {"name": b["name"], "base_file": b["file"], "head_file": h["file"], "base_tokens": b["tokens"],
                 "head_tokens": h["tokens"], "base_calls": b["calls"], "head_calls": h["calls"]}
                for b, h in pairs
            ] if label == "moved_functions" else [],
        }
    a.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "rows"}) for k, v in out.items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
