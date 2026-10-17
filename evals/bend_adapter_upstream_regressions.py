"""Cross-version upstream Bend verifier qualification for the Hermes adapter.

Replays the semantic-attestation regression from bendlang/bend#1212. The source
program evaluates to False. We emit the BendTT book and append two kernel
oracles to learn whether the certified translation says main=False or main=True.

Usage:
  python evals/bend_adapter_upstream_regressions.py \
    --bend 2.0.32=/path/to/bend --bend 2.0.33=/path/to/bend \
    --bend 2.0.34=/path/to/bend --repeats 25 --output result.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bend_verify_core_upstream", ROOT / "plugins" / "bend" / "verify_core.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load Bend verification core")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

_HOST_ELAN_HOME = os.environ.get("ELAN_HOME") or str(Path.home() / ".elan")

HELPER = """def ign(-b: Bool, r: Bool) -> Bool:
  r

law L:
  for n: Nat
  Bool

def M(n: Nat) -> Bool:
  ign(L(n), True{})
"""

PROOF = """import Base
import ./a-b.bend as AB

def a_2d_b.M(n: Nat) -> Bool:
  AB.ign(AB.L(n), False{})

def AB.L(n):
  match n:
    case Zero{}:
      True{}
    case Succ{p}:
      AB.M(p)

def main() -> Bool:
  a_2d_b.M(Zero{})
"""

ORACLE_FALSE = "ora_false : {main == (.False, ()) : Bool} = {==}\n"
ORACLE_TRUE = "ora_true : {main == (.True, ()) : Bool} = {==}\n"


def parse_bend(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--bend must be VERSION=/path/to/bend")
    version, raw = value.split("=", 1)
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Bend binary does not exist: {path}")
    return version, path


def env_for(home: Path, bend_lib: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in core._BEND_ENV_DENY:
        env.pop(key, None)
    env.update(
        HOME=str(home),
        ELAN_HOME=_HOST_ELAN_HOME,
        BEND_LIB=str(bend_lib),
        BEND_NO_TELEMETRY="1",
    )
    return env


def run(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 30):
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def kernel_bin(home: Path) -> Path:
    bins = sorted((home / ".bend" / "bendtt").glob("*/bendtt"))
    if len(bins) != 1:
        raise RuntimeError(f"expected one BendTT kernel under {home}, got {bins}")
    return bins[0]


def kernel_oracle(kernel: Path, book: Path, line: str, root: Path) -> dict:
    candidate = root / ("oracle-" + ("false" if "False" in line else "true") + ".bendtt")
    candidate.write_bytes(book.read_bytes() + b"\n" + line.encode("utf-8"))
    got = subprocess.run(
        [str(kernel), str(candidate)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return {
        "pass": got.returncode == 0 and got.stdout.strip() == "ALL PROOFS CHECK",
        "exit_code": got.returncode,
        "stdout": core.bounded(got.stdout),
        "stderr": core.bounded(got.stderr),
    }


def qualify(label: str, bend: Path, repeats: int, root: Path) -> dict:
    project = root / label / "project"
    project.mkdir(parents=True)
    (project / "a-b.bend").write_text(HELPER, encoding="utf-8")
    (project / "PROOF.bend").write_text(PROOF, encoding="utf-8")

    home = root / label / "home"
    lib = root / label / "bend-lib"
    home.mkdir()
    lib.mkdir()
    env = env_for(home, lib)

    version = run([str(bend), "version"], cwd=project, env=env, timeout=5)
    source = run([str(bend), "PROOF.bend"], cwd=project, env=env)
    records = []
    for iteration in range(repeats):
        result = core.verify(
            str(project),
            which=lambda _name, path=str(bend): path,
            source_env=env,
        )
        records.append(
            {
                "iteration": iteration,
                "verdict": result["verdict"],
                "success": result["success"],
                "duration_ms": result["duration_ms"],
                "exit_code": result["exit_code"],
                "bend_sha256": result.get("bend_sha256"),
            }
        )

    kernel = kernel_bin(home)
    emitted = root / label / "translated.bendtt"
    emit = run([str(bend), "PROOF.bend", "-o", str(emitted)], cwd=project, env=env)
    if emit.returncode != 0 or not emitted.exists():
        false_oracle = {"pass": False, "error": "emit failed"}
        true_oracle = {"pass": False, "error": "emit failed"}
    else:
        false_oracle = kernel_oracle(kernel, emitted, ORACLE_FALSE, root / label)
        true_oracle = kernel_oracle(kernel, emitted, ORACLE_TRUE, root / label)

    if false_oracle.get("pass") and not true_oracle.get("pass"):
        certified_main = "False"
    elif true_oracle.get("pass") and not false_oracle.get("pass"):
        certified_main = "True"
    elif false_oracle.get("pass") and true_oracle.get("pass"):
        certified_main = "both"
    else:
        certified_main = "neither"

    source_value = source.stdout.strip()
    adapter_passes = sum(record["verdict"] == "pass" for record in records)
    translation_mismatch = source_value == "False{}" and certified_main != "False"

    return {
        "label": label,
        "bend_path": str(bend),
        "bend_version_output": version.stdout.strip(),
        "source_exit_code": source.returncode,
        "source_stdout": core.bounded(source.stdout),
        "source_stderr": core.bounded(source.stderr),
        "adapter_runs": repeats,
        "adapter_passes": adapter_passes,
        "adapter_pass_rate": adapter_passes / repeats,
        "emit_exit_code": emit.returncode,
        "emit_stdout": core.bounded(emit.stdout),
        "emit_stderr": core.bounded(emit.stderr),
        "kernel_sha256": core.sha256_file(kernel),
        "false_oracle": false_oracle,
        "true_oracle": true_oracle,
        "certified_main": certified_main,
        "translation_mismatch": translation_mismatch,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bend", action="append", required=True, type=parse_bend)
    parser.add_argument("--repeats", type=int, default=25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")

    with tempfile.TemporaryDirectory(prefix="bend-hermes-upstream-") as raw:
        root = Path(raw)
        reports = [qualify(label, bend, args.repeats, root) for label, bend in args.bend]

    summary = {
        "experiment_count": sum(report["adapter_runs"] + 3 for report in reports),
        "versions": {
            report["label"]: {
                "bend_version_output": report["bend_version_output"],
                "adapter_pass_rate": report["adapter_pass_rate"],
                "source_stdout": report["source_stdout"],
                "certified_main": report["certified_main"],
                "translation_mismatch": report["translation_mismatch"],
            }
            for report in reports
        },
        "safe_candidates": [
            report["label"] for report in reports if not report["translation_mismatch"]
        ],
    }
    payload = {"summary": summary, "reports": reports}
    rendered = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
