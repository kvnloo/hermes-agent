"""Frozen synthetic source fixtures. No user corpus and no model-generated facts."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from stats import Probe, digest

SEEDS = (10, 11)
CHECKPOINTS = (300, 600)
SLOTS_PER_CYCLE = 40


def source(seed, cycle, slot):
    literal = "rfc-id-" + sha256(f"{seed}:{cycle}:{slot}".encode()).hexdigest()[:20]
    return f"Synthetic record {cycle}/{slot}: {literal}. Observation complete."


def freeze():
    positions = ((1, 20), (50, 20), (150, 20), (290, 20), (300, 31), (300, 40))
    probes = []
    for seed in SEEDS:
        for cycle, slot in positions:
            text = source(seed, cycle, slot)
            literal = text.split(": ")[1].split(".")[0]
            probes.append(Probe(seed, f"cycle-{cycle}-slot-{slot}", cycle,
                sha256(text.encode()).hexdigest(), "synthetic:rfc143379:v1", literal,
                stratum="recent-at-300" if cycle == 300 else "historical"))
    return {"schema": "rfc143379-paired-manifest-v1", "measurement": "deterministic_boundary",
            "cycles_are": "completed compress() generations, each fed 40 conversational rounds",
            "checkpoints": list(CHECKPOINTS), "ratios_requested": [4, 6, 8],
            "probes": [asdict(p) for p in probes], "probes_digest": digest([asdict(p) for p in probes])}


def load_manifest(path):
    payload = json.loads(Path(path).read_text())
    if payload != freeze():
        raise ValueError("frozen manifest/source mismatch; do not silently regenerate")
    return payload, [Probe(**p) for p in payload["probes"]]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.output.open("x") as out:
        out.write(json.dumps(freeze(), indent=2) + "\n")
