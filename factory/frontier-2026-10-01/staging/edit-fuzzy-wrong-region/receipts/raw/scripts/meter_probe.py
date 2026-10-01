"""M01: what hermes.file_edit.count would record for each contract case on this tree.

Runs ShellFileOperations.patch_replace inside the shared-metrics edit probe (the same
context-local probe record_file_edit installs) and maps it with file_edit_fields.
No metrics store is written; nothing leaves the process. usage: meter_probe.py <repo>
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(sys.argv[1]) / "tests" / "tools"))

from hermes_cli.observability import shared_metrics_harness as harness  # noqa: E402
from hermes_cli.observability.shared_metrics_contract import (  # noqa: E402
    FILE_EDIT_OUTCOMES, FILE_EDIT_STRATEGIES)
from tools.environments.local import LocalEnvironment  # noqa: E402
from tools.file_operations import ShellFileOperations  # noqa: E402
from tools.fuzzy_match import STRATEGIES  # noqa: E402
from test_fuzzy_match_wrong_region import NEAR_MISS, WRONG_REGION  # noqa: E402

cases = {**{k: v[:3] for k, v in WRONG_REGION.items()}, **{k: v[:3] for k, v in NEAR_MISS.items()}}
out = {"strategy_labels": sorted(FILE_EDIT_STRATEGIES), "outcome_labels": sorted(FILE_EDIT_OUTCOMES),
       "strategies_chain": [n for n, _ in STRATEGIES], "cases": {}}
with tempfile.TemporaryDirectory() as tmp:
    ops = ShellFileOperations(LocalEnvironment(cwd=tmp, timeout=15), cwd=tmp)
    for name, (content, old, new) in cases.items():
        target = Path(tmp) / f"{name}.py"
        target.write_text(content, encoding="utf-8")
        probe = harness._EditProbe()
        token = harness._EDIT_PROBE.set(probe)
        try:
            result = ops.patch_replace(str(target), old, new)
        finally:
            harness._EDIT_PROBE.reset(token)
        fields = harness.file_edit_fields(tool="patch", mode="replace", result=result.to_dict(), probe=probe)
        out["cases"][name] = {
            "outcome": fields["outcome"], "match_strategy": fields["match_strategy"],
            "labels_in_contract": fields["outcome"] in FILE_EDIT_OUTCOMES and fields["match_strategy"] in FILE_EDIT_STRATEGIES,
            "file_unchanged": target.read_text(encoding="utf-8") == content,
        }
print(json.dumps(out, indent=1))
