#!/usr/bin/env python3
"""Fold-in row order check (round 5; $0, T0, no LLM, no network, no private data).

Question: does the fold-in for #117462 change any line that #117462 itself would emit?
In #117462 every section fills one shared 7,000-char budget in table order (per-section
truncation, no ``break``), so a row placed before ``files``/``errors`` takes budget from them.

Part 1, synthetic: reads the coverage JSON written by anchor_coverage.py for the arms
c117462 (main + #117462), c117462_foldin (round-5 order: the three rows appended after
``errors``) and c117462_foldin_r03 (round-3 order: ``task ids`` after ``todo ids``,
``dotted keys`` before ``files``, ``error messages`` last). For each of the 180 regions it
compares every #117462 section line with the same label on each fold-in arm.

Part 2, real text: regions built from public Python source (agent/*.py at a declared main,
exported with git archive) as read_file tool traffic: one assistant tool call
read_file(path=...) plus one tool message whose content is the JSON a read_file call returns
({"content": "<n>|<line>...", "total_lines": N, ...}, first 2,000 lines). Region sizes: the
first 40, the first 120 and all files in name order. Same comparison, on the real
_build_anchor_index of each arm.

Usage: foldin_order_check.py --checkout <worktree for imports> --coverage <json> --corpus <dir with *.py>
       --arm c117462=<file> --arm c117462_foldin=<file> --arm c117462_foldin_r03=<file> --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics as st
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import anchor_coverage as ac  # noqa: E402  (also installs the loopback-only socket guard)

CARRIER = "c117462"
FOLDINS = ("c117462_foldin", "c117462_foldin_r03")
NEW_LABELS = ("task ids", "dotted keys", "error messages")


def by_label(sections: list[str]) -> dict[str, str]:
    return {s.split(":", 1)[0]: s for s in sections}


def compare(carrier_secs: list[str], arm_secs: list[str]) -> dict:
    c, a = by_label(carrier_secs), by_label(arm_secs)
    changed = {lab: [len(line), len(a.get(lab, ""))] for lab, line in c.items() if a.get(lab) != line}
    return {"prefix": arm_secs[:len(carrier_secs)] == carrier_secs, "changed": changed,
            "new_lens": {lab: len(a[lab]) for lab in NEW_LABELS if lab in a}}


def med(xs):
    return int(st.median(xs)) if xs else None


def synthetic(cov: dict) -> dict:
    arms = cov["arms"]
    key = lambda x: (x["density"], x["seed"], x["bank"])  # noqa: E731
    carrier = {key(x): x["sections"] for x in arms[CARRIER]["F02s"]}
    out = {}
    for arm in FOLDINS:
        rows = {key(x): x["sections"] for x in arms[arm]["F02s"]}
        res = {"regions": len(carrier), "carrier_lines_prefix": 0, "regions_with_a_carrier_line_changed": 0, "per_density": {}}
        for dens in ("sparse", "medium", "dense"):
            keys = [k for k in carrier if k[0] == dens]
            cmp = [compare(carrier[k], rows[k]) for k in keys]
            res["carrier_lines_prefix"] += sum(c["prefix"] for c in cmp)
            res["regions_with_a_carrier_line_changed"] += sum(bool(c["changed"]) for c in cmp)
            labels = sorted({lab for c in cmp for lab in c["changed"]})
            per = {}
            for lab in labels:
                pairs = [c["changed"][lab] for c in cmp if lab in c["changed"]]
                per[lab] = {"regions_changed": len(pairs), "of": len(keys),
                            "carrier_len_p50": med([p[0] for p in pairs]), "foldin_len_p50": med([p[1] for p in pairs]),
                            "cut_to_bare_label": sum(1 for p in pairs if p[1] == len(lab) + 1),
                            "label_removed": sum(1 for p in pairs if p[1] == 0)}
            new = {}
            for lab in NEW_LABELS:
                lens = [c["new_lens"][lab] for c in cmp if lab in c["new_lens"]]
                new[lab] = {"emitted_in": len(lens), "of": len(keys), "len_p50": med(lens),
                            "bare_label": sum(1 for v in lens if v == len(lab) + 1)}
            res["per_density"][dens] = {"carrier_lines_changed": per, "new_sections": new}
        out[arm] = res
    return out


def read_file_region(paths: list[Path], root: Path) -> list[dict]:
    msgs = []
    for i, p in enumerate(paths):
        rel = f"agent/{p.name}"
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        page = lines[:2000]
        body = {"content": "\n".join(f"{n}|{ln}" for n, ln in enumerate(page, start=1)),
                "total_lines": len(lines), "truncated": len(lines) > 2000}
        msgs.append({"role": "assistant", "content": "",
                     "tool_calls": [{"id": f"call_{i}", "type": "function",
                                     "function": {"name": "read_file", "arguments": json.dumps({"path": rel})}}]})
        msgs.append({"role": "tool", "tool_call_id": f"call_{i}", "content": json.dumps(body, ensure_ascii=False)})
    return msgs


def worker(checkout: str, arm_file: str, corpus: str, out: str) -> None:
    mod = ac.load_arm(checkout, arm_file)
    files = sorted(Path(corpus).glob("*.py"))
    res = {"arm_file_sha256": hashlib.sha256(Path(arm_file).read_bytes()).hexdigest(), "regions": {}}
    for n in (40, 120, len(files)):
        region = read_file_region(files[:n], Path(corpus))
        res["regions"][str(n)] = {"files": n, "region_chars": sum(len(m["content"]) for m in region),
                                  "sections": ac.sections_of(mod._build_anchor_index(region))}
    res["egress_blocked"] = list(ac._blocked)
    Path(out).write_text(json.dumps(res), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--coverage")
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--arm", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--worker", nargs=2, metavar=("ARM_FILE", "OUT"))
    a = ap.parse_args()
    if a.worker:
        worker(a.checkout, a.worker[0], a.corpus, a.worker[1])
        return
    arms = dict(s.split("=", 1) for s in a.arm)
    real = {}
    for name, path in arms.items():
        tmp = f"{a.out}.{name}.part"
        subprocess.run([sys.executable, __file__, "--checkout", a.checkout, "--corpus", a.corpus,
                        "--worker", path, tmp], check=True)
        real[name] = json.loads(Path(tmp).read_text(encoding="utf-8"))
        Path(tmp).unlink()
    files = sorted(Path(a.corpus).glob("*.py"))
    corpus_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files)
    real_cmp = {}
    for arm in FOLDINS:
        real_cmp[arm] = {}
        for n, reg in real[CARRIER]["regions"].items():
            c = compare(reg["sections"], real[arm]["regions"][n]["sections"])
            real_cmp[arm][n] = {"files": reg["files"], "region_chars": reg["region_chars"], **c}
    cov = json.loads(Path(a.coverage).read_text(encoding="utf-8"))
    Path(a.out).write_text(json.dumps({
        "coverage_sha256": hashlib.sha256(Path(a.coverage).read_bytes()).hexdigest(),
        "corpus": {"files": len(files), "chars": len(corpus_text),
                   "sha256": hashlib.sha256(corpus_text.encode()).hexdigest()},
        "synthetic": synthetic(cov),
        "real_text": real_cmp,
        "real_text_sections": {k: v["regions"] for k, v in real.items()},
        "arm_sha256": {k: v["arm_file_sha256"] for k, v in real.items()},
        "egress_blocked": {k: v["egress_blocked"] for k, v in real.items()},
    }, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
