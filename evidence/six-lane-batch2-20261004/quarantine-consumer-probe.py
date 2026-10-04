"""Local review probe; owner fixes leave dependency-group pins quarantined."""
from copy import deepcopy
from pathlib import Path
import tomllib

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
import pytest

from pm.workspace import _core_release_quarantine

ROOT = Path(__file__).resolve().parents[2]
OWNER_ADDITIONS = {
    "pilk", "playwright", "pyopen-wakeword", "pypinyin", "resvg-py", "tomli-w", "truststore",
}


@pytest.mark.parametrize("additions", [set(), OWNER_ADDITIONS, OWNER_ADDITIONS | {"distlib"}],
                         ids=["current-main", "both-owner-seven-pin-policies", "group-inclusive-control"])
def test_exact_pins_remain_exempt_in_generated_workspace(additions):
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tables = {"core": manifest["project"]["dependencies"], "build": manifest["build-system"]["requires"]}
    tables.update({f"extra:{name}": rows for name, rows in manifest["project"]["optional-dependencies"].items()})
    tables.update({f"group:{name}": rows for name, rows in manifest["dependency-groups"].items()})
    policy = manifest["tool"]["uv"]["exclude-newer-package"]
    policy.update({name: False for name in additions})
    generated = deepcopy(manifest)
    _core_release_quarantine(generated, ROOT / "uv.lock")
    declared = {canonicalize_name(name): value for name, value in policy.items()}
    normalized = {canonicalize_name(name): value for name, value in generated["tool"]["uv"]["exclude-newer-package"].items()}
    missing = []
    for table, rows in tables.items():
        for row in rows:
            if not isinstance(row, str):
                continue  # include-group references add no direct requirements.
            req = Requirement(row)
            specs = list(req.specifier)
            if len(specs) != 1 or specs[0].operator != "==" or "*" in specs[0].version:
                continue
            name = canonicalize_name(req.name)
            # Existing dated per-package overrides remain valid reviewed policy.
            expected = declared.get(name, False)
            if name not in declared or normalized.get(name) != expected:
                missing.append(f"{table}: {req} -> {normalized.get(name)!r}, expected {expected!r}")
    assert not missing, "\n".join(sorted(missing))
