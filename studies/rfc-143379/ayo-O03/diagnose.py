#!/usr/bin/env python3
"""Reuse archived run_one on an exact git-archive source snapshot."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

root = Path.cwd()
study = Path(__file__).resolve().parent
out = root / "out"
out.mkdir(exist_ok=False)
manifest = json.loads((root / "input-manifest.json").read_text())
archive = root / "candidate-source.tar"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest["archive_sha256"]
candidate = root / "candidate"
candidate.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    assert tar.pax_headers["comment"] == manifest["candidate_sha"]
    tar.extractall(candidate, filter="data")
source_hashes = {str(p.relative_to(candidate)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in candidate.rglob("*") if p.is_file()}
assert (candidate / "tests/_fixtures/env_filter.py").is_file(), "Snapshot omits canonical test fixture imports"
heldout = ["HELDOUT-CONSENT-CODE-TM5729", "CLIENT-REF-VZ8046"]
identifier_matches = {token: [str(p.relative_to(candidate)) for p in candidate.rglob("*")
                              if p.is_file() and token.encode() in p.read_bytes()]
                      for token in heldout}
assert not any(identifier_matches.values()), identifier_matches
probes = candidate / "tests/tools/ayo_O03"
probes.mkdir(parents=True, exist_ok=False)
for name in ["test_real_checkout.py", "test_consent_nonce_invariance.py", "test_heldout.py", "rfc_consent_scenarios.json"]:
    shutil.copyfile(study / name, probes / name)
spec = importlib.util.spec_from_file_location("shared_runner", study / "run_fixed_substrate.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
env = {k: os.environ[k] for k in ("PATH", "HOME", "HERMES_PYTHON")}
env.update(HERMES_HOME=str(root / "isolated-hermes-home"), TZ="UTC", LANG="C.UTF-8")
Path(env["HERMES_HOME"]).mkdir()
rows = []
for name, label in [("test_real_checkout.py", "unchanged_shared"),
                    ("test_consent_nonce_invariance.py", "unchanged_renamed"),
                    ("test_heldout.py", "heldout")]:
    rows.append(runner.run_one(candidate, out, env, label, "independent_diagnostic",
                               f"tests/tools/ayo_O03/{name}"))
changed = [name for name, digest in source_hashes.items()
           if hashlib.sha256((candidate / name).read_bytes()).hexdigest() != digest]
receipt = dict(candidate_sha=manifest["candidate_sha"], archive_sha256=manifest["archive_sha256"],
               runner_source_sha=manifest["runner_source_sha"],
               runner_sha256=hashlib.sha256((study / "run_fixed_substrate.py").read_bytes()).hexdigest(),
               driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               probe_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in study.iterdir() if p.is_file()},
               source_changed=changed, source_snapshot_scope=manifest["scope"],
               heldout_identifier_matches_before_injection=identifier_matches,
               environment_scope="Minimal separately provisioned compatibility environment, NOT canonical lockfile/CI qualification",
               python=subprocess.check_output([env["HERMES_PYTHON"], "--version"], text=True).strip(),
               real_model=False, full_suite=False, author_297_battery=False,
               overall="NOT_CERTIFIED", results=rows)
(out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
assert not changed, changed
raise SystemExit(0 if all(row["passed"] for row in rows) else 1)
