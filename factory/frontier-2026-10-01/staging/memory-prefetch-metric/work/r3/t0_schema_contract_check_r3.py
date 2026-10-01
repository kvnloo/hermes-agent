"""T0 static check: hermes.memory.prefetch.count schema <-> contract <-> doc agreement (no I/O beyond reading files).

Round 3: same checks as round 2; the builder samples follow the amended builder, which classifies
success/empty itself from the raw ``recalled`` value (a ``success`` whose ``recalled`` holds no text is
``empty``; a non-str value never raises).

Round 2: same checks as round 1, plus a per-row split of WHICH layer rejects each out-of-contract row.
The JSON schema types `provider` as `vocabulary_identifier` (a lowercase-identifier pattern, the same as
memory_op_counter), so it cannot reject a lowercase raw provider name; the closed provider set is enforced
by the contract's counter_dimensions_are_valid (mark projection and store write) and the builder's
memory_provider_name rule. The added `hindsight` row shows that split.

Usage: python t0_schema_contract_check_r3.py --repo <tree> --out <json>
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
repo = Path(a.repo).resolve()
sys.path.insert(0, str(repo))

import jsonschema  # noqa: E402

from hermes_cli.observability import shared_metrics_contract as contract  # noqa: E402
from hermes_cli.observability import shared_metrics_loop as loop  # noqa: E402

schema_path = repo / "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json"
schema = json.loads(schema_path.read_text(encoding="utf-8"))
jsonschema.Draft202012Validator.check_schema(schema)
metric = contract.MEMORY_PREFETCH_METRIC
item_validator = jsonschema.Draft202012Validator({"$defs": schema["$defs"], **schema["properties"]["metrics"]["items"]})
out: dict = {"metric": metric, "schema": str(schema_path.relative_to(repo)), "checks": {}}

defs = {d["properties"]["name"]["const"]: k for k, d in schema["$defs"].items()
        if isinstance(d, dict) and "properties" in d and "const" in d["properties"].get("name", {})}
refs = {item["$ref"].rsplit("/", 1)[1] for item in schema["properties"]["metrics"]["items"]["oneOf"]}
def_name = defs.get(metric)
out["checks"]["schema_def_present"] = def_name is not None
out["checks"]["schema_def_referenced_by_metrics_items"] = def_name in refs
dims = schema["$defs"][def_name]["properties"]["dimensions"]
contract_dims = contract._COUNTER_DIMENSION_VALUES[metric]
out["checks"]["dimension_fields_equal"] = set(dims["properties"]) == set(contract_dims) == set(dims["required"])
out["checks"]["outcome_enum_equals_contract"] = set(dims["properties"]["outcome"]["enum"]) == set(contract.MEMORY_PREFETCH_OUTCOMES)
lat = schema["$defs"]["tool_latency_bucket"]["enum"]
out["checks"]["latency_enum_equals_contract"] = set(lat) == set(contract.TOOL_LATENCY_BUCKETS)
out["checks"]["mark_projects_to_metric"] = contract._DECISION_MARK_METRICS.get(contract.MEMORY_PREFETCH_MARK) == metric
out["checks"]["is_counter_metric"] = metric in contract.COUNTER_METRICS

# Every value the contract allows validates; values outside it are rejected.
accepted = rejected_bad = 0
for provider, outcome, bucket in itertools.product(
        sorted(contract.MEMORY_PROVIDERS), sorted(contract.MEMORY_PREFETCH_OUTCOMES), sorted(contract.TOOL_LATENCY_BUCKETS)):
    row = {"name": metric, "type": "counter", "value": 1,
           "dimensions": {"provider": provider, "outcome": outcome, "latency_bucket": bucket}}
    accepted += item_validator.is_valid(row)
total = len(contract.MEMORY_PROVIDERS) * len(contract.MEMORY_PREFETCH_OUTCOMES) * len(contract.TOOL_LATENCY_BUCKETS)
bad_rows = [
    ("bad outcome", {"provider": "plugin", "outcome": "timeout", "latency_bucket": "lt_100ms"}),
    ("bad bucket", {"provider": "plugin", "outcome": "success", "latency_bucket": "7s"}),
    ("raw provider name, capitals and spaces", {"provider": "Acme Private Memory", "outcome": "success", "latency_bucket": "lt_100ms"}),
    ("raw provider name, lowercase identifier", {"provider": "hindsight", "outcome": "success", "latency_bucket": "lt_100ms"}),
    ("extra field carrying the query", {"provider": "plugin", "outcome": "success", "latency_bucket": "lt_100ms", "query": "what do I prefer?"}),
    ("missing field", {"provider": "plugin", "outcome": "success"}),
]
contract_ok = all(contract.counter_dimensions_are_valid(metric, {"provider": p, "outcome": o, "latency_bucket": b})
                  for p, o, b in itertools.product(sorted(contract.MEMORY_PROVIDERS), sorted(contract.MEMORY_PREFETCH_OUTCOMES),
                                                   sorted(contract.TOOL_LATENCY_BUCKETS)))
split = []
for label, d in bad_rows:
    schema_rejects = not item_validator.is_valid({"name": metric, "type": "counter", "value": 1, "dimensions": d})
    contract_rejects = not contract.counter_dimensions_are_valid(metric, d)
    rejected_bad += schema_rejects or contract_rejects
    split.append({"row": label, "dimensions": d, "schema_rejects": schema_rejects, "contract_rejects": contract_rejects})
out["checks"]["all_contract_combinations_valid"] = {"accepted": accepted, "total": total, "pass": accepted == total}
out["checks"]["all_contract_combinations_pass_contract_check"] = contract_ok
out["checks"]["out_of_contract_rows_rejected"] = {
    "rejected_by_schema_or_contract": rejected_bad, "rejected_by_schema": sum(r["schema_rejects"] for r in split),
    "rejected_by_contract": sum(r["contract_rejects"] for r in split), "total": len(bad_rows),
    "pass": rejected_bad == len(bad_rows) and all(r["contract_rejects"] for r in split)}
out["rejection_split"] = split
out["schema_provider_type"] = {"ref": dims["properties"]["provider"].get("$ref"),
                               "pattern": schema["$defs"]["vocabulary_identifier"].get("pattern"),
                               "same_as_memory_op_counter": dims["properties"]["provider"] ==
                               schema["$defs"][defs[contract.MEMORY_OP_METRIC]]["properties"]["dimensions"]["properties"]["provider"]}

# Builder maps raw producer values onto the closed sets (provider rule, outcome fallback, buckets).
samples = [
    ({"provider": "honcho", "outcome": "success", "waited_ms": 12, "recalled": "- prefers tabs"}, {"provider": "honcho", "outcome": "success", "latency_bucket": "lt_100ms"}),
    ({"provider": "honcho", "outcome": "success", "waited_ms": 12, "recalled": "  "}, {"provider": "honcho", "outcome": "empty", "latency_bucket": "lt_100ms"}),
    ({"provider": "honcho", "outcome": "success", "waited_ms": 12}, {"provider": "honcho", "outcome": "empty", "latency_bucket": "lt_100ms"}),
    ({"provider": "honcho", "outcome": "success", "waited_ms": 12, "recalled": {"context": "- prefers tabs"}}, {"provider": "honcho", "outcome": "empty", "latency_bucket": "lt_100ms"}),
    ({"provider": "honcho", "outcome": "failed", "waited_ms": 12, "recalled": "- prefers tabs"}, {"provider": "honcho", "outcome": "failed", "latency_bucket": "lt_100ms"}),
    ({"provider": "hindsight", "outcome": "timed_out", "waited_ms": 8000.4}, {"provider": "plugin", "outcome": "timed_out", "latency_bucket": "5s_to_10s"}),
    ({"provider": "Acme-Private", "outcome": "weird", "waited_ms": None}, {"provider": "plugin", "outcome": "failed", "latency_bucket": "unknown"}),
    ({"provider": "", "outcome": "skipped", "waited_ms": 0.2}, {"provider": "builtin", "outcome": "skipped", "latency_bucket": "lt_100ms"}),
    ({"provider": "mem0", "outcome": "EMPTY", "waited_ms": 20000}, {"provider": "mem0", "outcome": "empty", "latency_bucket": "10s_to_30s"}),
]
out["checks"]["builder_samples"] = [
    {"raw": raw, "got": loop.memory_prefetch_fields(**raw), "expected": exp, "pass": loop.memory_prefetch_fields(**raw) == exp}
    for raw, exp in samples
]

# Doc row lists the enumerated outcome values and the latency range.
doc = (repo / "website/docs/developer-guide/relay-shared-metrics.md").read_text(encoding="utf-8")
row = next((ln for ln in doc.splitlines() if ln.startswith(f"| `{metric}`")), "")
out["doc_row"] = row
out["checks"]["doc_row_present"] = bool(row)
out["checks"]["doc_row_lists_outcomes"] = all(f"`{v}`" in row for v in contract.MEMORY_PREFETCH_OUTCOMES)
out["checks"]["doc_row_latency_range"] = "`lt_100ms`" in row and "`gte_30s`" in row
out["checks"]["doc_row_says_never_content"] = bool(re.search(r"Never the query or the recalled text", row))
out["bundled_memory_providers"] = sorted(contract.MEMORY_PROVIDERS)
flat = []
for k, v in out["checks"].items():
    if isinstance(v, bool):
        flat.append(v)
    elif isinstance(v, dict):
        flat.append(bool(v.get("pass")))
    elif isinstance(v, list):
        flat.append(all(x["pass"] for x in v))
out["all_pass"] = all(flat)
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({"all_pass": out["all_pass"], "checks": {k: (v if not isinstance(v, list) else all(x['pass'] for x in v)) for k, v in out["checks"].items()}}, indent=2))
