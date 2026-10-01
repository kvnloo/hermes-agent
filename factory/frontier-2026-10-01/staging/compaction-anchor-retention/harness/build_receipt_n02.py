#!/usr/bin/env python3
"""Write receipts/N02-config-key-coverage.json from raw/config_key_coverage.json.

Round 4 (text and receipts only, head unchanged). Run from the staging directory:
    python3 harness/build_receipt_n02.py
"""
import hashlib
import json
from pathlib import Path

BASE = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
HEAD = "30a746f7920c2b4101f121353778d94f5ce001b5"
RECHECK_MAIN = "44a1ce9724502b9c692faaef00af3054bf11f1a6"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    here = Path(".")
    raw_path = here / "raw" / "config_key_coverage.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    alln, leaf = raw["all_dotted_paths"], raw["leaf_dotted_paths"]
    receipt = {
        "schema": "xf.receipt.v1",
        "staging": "compaction-anchor-retention",
        "issue": None,
        "origin_refs": ["NousResearch/hermes-agent#116246", "NousResearch/hermes-agent#117462"],
        "base_revision": BASE,
        "head_revision": HEAD,
        "supersedes": None,
        "policy_revision": {
            "factory": "FACTORY.md (frontier-2026-10-01)",
            "protocol": "promotion-readiness-2026-10-01/PROTOCOL.md",
        },
        "env": {
            "python": "3.11 (HERMES_PYTHON venv, read-only bind)",
            "sandbox": "harness/sandbox.sh (bwrap, no network, fresh HOME/HERMES_HOME, live install masked except the venv); harness/egress_sitecustomize.py egress logger",
        },
        "provenance": "self",
        "ai_assistance": "Claude Code (Opus 5.5) wrote the harness and ran it; disclosed per repository policy",
        "privacy": "public-aggregate (input is the committed hermes_cli/config_defaults.py); no absolute local paths",
        "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "tokens": 0},
        "id": "N02/r20261001-04",
        "kind": "static",
        "question": "Which dotted DEFAULT_CONFIG key paths does the head's `dotted keys` row capture verbatim, and why are the others missed?",
        "inputs": {
            "checkout": f"tree of {HEAD} (git archive). The row is read from the head's agent/context_compressor.py. hermes_cli/config_defaults.py is byte-identical on base {BASE[:10]}, the head and main {RECHECK_MAIN[:10]}, and agent/context_compressor.py is unchanged between base and main {RECHECK_MAIN[:10]}, so the figures hold on that main too.",
            "config_defaults_sha256": raw["inputs"]["config_defaults_sha256"],
            "context_compressor_sha256_head": raw["inputs"]["context_compressor_sha256"],
            "dotted_keys_row": raw["inputs"]["dotted_keys_row"],
            "harness_sha256": {"config_key_coverage.py": sha(here / "harness" / "config_key_coverage.py")},
            "raw": {"path": "raw/config_key_coverage.json", "sha256": sha(raw_path)},
        },
        "command": "VENV=$VENV HERMES_INSTALL=<live install> EGRESS_DIR=<dir with sitecustomize.py> $SANDBOX $TREE <fresh home on a non-/tmp disk> <egress log> $PY $STAGING/harness/config_key_coverage.py --checkout $TREE --out <home>/n02.json   # $TREE = git archive of the head; copied to raw/config_key_coverage.json",
        "method": "Flatten DEFAULT_CONFIG into every key path (intermediate dict nodes included, as N01 does), keep the 996 paths that contain a dot, scan each path alone with the production row; a path is fully matched when one match equals the whole path. Leaf-only figures (non-dict values) are reported beside it.",
        "results": {
            "flattened_paths_total": raw["flattened_paths_total"],
            "all_dotted_paths": {k: alln[k] for k in ("dotted_paths", "fully_matched", "fully_matched_pct", "not_fully_matched", "not_fully_matched_pct", "partial_only")},
            "leaf_dotted_paths": {k: leaf[k] for k in ("dotted_paths", "fully_matched", "fully_matched_pct", "not_fully_matched", "not_fully_matched_pct", "partial_only")},
            "misses_by_reason_all": {r: v["count"] for r, v in alln["misses_by_reason"].items()},
            "miss_examples_all": next(iter(alln["misses_by_reason"].values()))["examples"],
            "named_examples": raw["named_examples"],
        },
        "egress": "0 lookups, 0 connect attempts",
        "readout": [
            f"{alln['fully_matched']} of {alln['dotted_paths']} dotted DEFAULT_CONFIG paths ({alln['fully_matched_pct']}%) are captured verbatim; {alln['not_fully_matched']} ({alln['not_fully_matched_pct']}%) are not.",
            f"Leaf settings only: {leaf['fully_matched']} of {leaf['dotted_paths']} captured; {leaf['not_fully_matched']} ({leaf['not_fully_matched_pct']}%) missed.",
            "Every miss has a one-word last segment (no underscore), e.g. terminal.backend, compression.threshold, compression.enabled, browser.backend, checkpoints.enabled. No path is partly matched.",
            "This is the cost of the snake_case last-segment rule that keeps file names (config.yaml), hosts (api.openai.com) and e.g out of the row.",
            "plugins.stream_reasoning_deltas (the one config-key gold) is not a DEFAULT_CONFIG path; it is captured.",
        ],
        "label": "OBSERVED",
        "limitations": [
            "measures the row on bare key strings; how often a one-word-leaf key is the fact a real summary loses is NOT_MEASURED",
            "DEFAULT_CONFIG is not the whole config surface (plugin and provider keys live elsewhere)",
        ],
        "verdict": "KEEP (limit disclosed: invariant narrowed to dotted keys whose last segment is snake_case; both bodies state the miss rate)",
    }
    out = here / "receipts" / "N02-config-key-coverage.json"
    out.write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out, sha(out))


if __name__ == "__main__":
    main()
