"""Wave 5: compare BendTT kernel trust strategies for Hermes.

A: Bend's mutable shared ~/.bend/bendtt cache.
B: rebuild from source in a fresh HOME for every verification.
C: rebuild once per Hermes process, copy/hash that kernel, and pin BENDTT to
   the private session copy for all later verdicts.

The fast kernel-only discriminator is bendlang/bend#1194 on Bend 2.0.34.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import statistics
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bend_verify_core_kernel_strategy", ROOT / "plugins" / "bend" / "verify_core.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load Bend verification core")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

_HOST_ELAN_HOME = os.environ.get("ELAN_HOME") or str(Path.home() / ".elan")

VALID = """import Base

law ok:
  {0n == 0n : Nat}

def ok():
  {==}
"""

# bendlang/bend#1194: bend2 accepts; BendTT rejects "calls that descend".
GAP = """import Base

def B(+c: Nat, f: Nat) -> Type:
  match f:
    case 0n: Empty
    case 1n+g: {c == c : Nat} & A(c, 1n, g)

def A(+c: Nat, e: Nat, f: Nat) -> Type:
  match e:
    case 0n: Unit
    case 1n+p: B(c, f)
"""


def make_project(root: Path, name: str, proof: str) -> Path:
    path = root / name
    path.mkdir(parents=True)
    (path / "PROOF.bend").write_text(proof, encoding="utf-8")
    return path


def env_home(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["ELAN_HOME"] = _HOST_ELAN_HOME
    return env


def kernel_bin(home: Path) -> Path:
    bins = sorted((home / ".bend" / "bendtt").glob("*/bendtt"))
    if len(bins) != 1:
        raise RuntimeError(f"expected one BendTT kernel under {home}, got {bins}")
    return bins[0]


def poison(path: Path) -> None:
    path.write_text("#!/bin/sh\necho ALL PROOFS CHECK\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--attacks", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="bend-hermes-kernel-strategies-") as raw:
        root = Path(raw)
        valid = make_project(root, "valid", VALID)
        gap = make_project(root, "gap", GAP)

        # Strategy A: shared global-ish cache.
        shared_home = root / "shared-home"
        shared_home.mkdir()
        shared_env = env_home(shared_home)
        warm = core.verify(str(valid), source_env=shared_env)
        if warm["verdict"] != "pass":
            raise RuntimeError(f"shared warmup failed: {warm}")
        baseline_gap = core.verify(str(gap), source_env=shared_env)
        if baseline_gap["verdict"] != "fail":
            raise RuntimeError(
                "the #1194 discriminator no longer reaches a failing kernel on this build: "
                + json.dumps(baseline_gap)
            )
        shared_kernel = kernel_bin(shared_home)
        shared_backup = shared_kernel.with_name("bendtt.original")
        shutil.copy2(shared_kernel, shared_backup)
        shared_good_sha = core.sha256_file(shared_kernel)

        poison(shared_kernel)
        shared_poison_sha = core.sha256_file(shared_kernel)
        shared_attacks = []
        for i in range(args.attacks):
            result = core.verify(str(gap), source_env=shared_env)
            shared_attacks.append(
                {"iteration": i, "verdict": result["verdict"], "duration_ms": result["duration_ms"]}
            )
        shutil.copy2(shared_backup, shared_kernel)

        # Strategy C bootstrap: one fresh build, then pin a private exact copy.
        bootstrap_home = root / "session-bootstrap-home"
        bootstrap_home.mkdir()
        t0 = time.monotonic()
        bootstrap = core.verify(str(valid), source_env=env_home(bootstrap_home))
        bootstrap_wall_ms = (time.monotonic() - t0) * 1000
        if bootstrap["verdict"] != "pass":
            raise RuntimeError(f"session bootstrap failed: {bootstrap}")
        built_kernel = kernel_bin(bootstrap_home)
        private_dir = root / "session-private"
        private_dir.mkdir()
        private_kernel = private_dir / "bendtt"
        shutil.copy2(built_kernel, private_kernel)
        private_sha = core.sha256_file(private_kernel)

        pinned_records = []
        for i in range(args.repeats):
            for label, target, expected in (("valid", valid, "pass"), ("gap", gap, "fail")):
                result = core.verify(
                    str(target),
                    source_env=dict(os.environ),
                    kernel_override=str(private_kernel),
                    kernel_expected_sha256=private_sha,
                )
                pinned_records.append(
                    {
                        "iteration": i,
                        "case": label,
                        "expected": expected,
                        "verdict": result["verdict"],
                        "duration_ms": result["duration_ms"],
                    }
                )

        # Re-poison the shared cache: pinned-session results must not change.
        poison(shared_kernel)
        pinned_under_shared_attack = []
        for i in range(args.attacks):
            result = core.verify(
                str(gap),
                source_env=shared_env,
                kernel_override=str(private_kernel),
                kernel_expected_sha256=private_sha,
            )
            pinned_under_shared_attack.append(
                {"iteration": i, "verdict": result["verdict"], "duration_ms": result["duration_ms"]}
            )

        # Now mutate the private kernel itself. Expected-hash gating must fail
        # before a proof verdict is trusted.
        private_backup = private_kernel.with_name("bendtt.original")
        shutil.copy2(private_kernel, private_backup)
        poison(private_kernel)
        private_mutation_rejections = 0
        for _ in range(args.attacks):
            try:
                core.verify(
                    str(gap),
                    kernel_override=str(private_kernel),
                    kernel_expected_sha256=private_sha,
                )
            except core.BendVerifyError as exc:
                if exc.code == "kernel_integrity":
                    private_mutation_rejections += 1
        shutil.copy2(private_backup, private_kernel)
        shutil.copy2(shared_backup, shared_kernel)

    shared_forged = sum(row["verdict"] == "pass" for row in shared_attacks)
    pinned_mismatches = [
        row for row in pinned_records if row["verdict"] != row["expected"]
    ]
    pinned_shared_forged = sum(
        row["verdict"] == "pass" for row in pinned_under_shared_attack
    )
    pinned_durations = [row["duration_ms"] for row in pinned_records]
    warm_ms = statistics.median(pinned_durations)
    amortized = {
        str(n): round((bootstrap_wall_ms + warm_ms * n) / n, 3)
        for n in (1, 2, 5, 10, 25, 50, 100)
    }

    summary = {
        "experiment_count": (
            2 + args.attacks + 1 + len(pinned_records)
            + len(pinned_under_shared_attack) + args.attacks
        ),
        "shared_cache": {
            "baseline_gap": baseline_gap["verdict"],
            "good_sha256": shared_good_sha,
            "poison_sha256": shared_poison_sha,
            "attack_attempts": args.attacks,
            "forged_passes": shared_forged,
            "attack_success_rate": shared_forged / args.attacks,
        },
        "session_pinned": {
            "bootstrap_ms": round(bootstrap_wall_ms, 3),
            "kernel_sha256": private_sha,
            "runs": len(pinned_records),
            "mismatch_count": len(pinned_mismatches),
            "warm_p50_ms": round(warm_ms, 3),
            "shared_cache_attack_attempts": args.attacks,
            "shared_cache_forged_passes": pinned_shared_forged,
            "private_mutation_attempts": args.attacks,
            "private_mutation_rejections": private_mutation_rejections,
            "amortized_ms_per_verification": amortized,
        },
    }
    payload = {
        "summary": summary,
        "shared_attacks": shared_attacks,
        "pinned_records": pinned_records,
        "pinned_mismatches": pinned_mismatches,
        "pinned_under_shared_attack": pinned_under_shared_attack,
    }
    rendered = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

    bad = (
        pinned_mismatches
        or pinned_shared_forged
        or private_mutation_rejections != args.attacks
    )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
