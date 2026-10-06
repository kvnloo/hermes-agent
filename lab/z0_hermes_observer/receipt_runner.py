"""Common Hermes integration experiment receipt + failure-injection runner (#322).

Join layer only: existing observer/shadow/decision receipts stay canonical.
This module adds a thin experiment envelope (identity, revisions, measurements,
outcome) plus an offline failure-injection catalog. Shadow/observability only —
never changes Hermes retries, routing, or model choice. promotion_ready is
always false. execution_completed never aliases into verified_success.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

EXPERIMENT_SCHEMA = "z0eval.hermes_stack_experiment.v0"
ARMS: tuple[str, ...] = ("H0", "Z", "R", "S", "ZR", "ZS", "RS", "ZRS")

# Offline catalog: expected fail-open / fail-closed for each required case.
# Simulations attribute the component and never claim Hermes behavior changed.
FAILURE_CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "z0int_backend_unavailable",
        "component": "z0int",
        "expected_mode": "fail_open",
        "description": "z0int backend unreachable; Hermes continues without shadow control.",
    },
    {
        "id": "malformed_backend_response",
        "component": "z0int",
        "expected_mode": "fail_open",
        "description": "Backend returns unparseable payload; drop decision, keep execution.",
    },
    {
        "id": "state_packet_source_disappears",
        "component": "state_packet",
        "expected_mode": "fail_open",
        "description": "State Packet source gone; omit packet fields, do not invent state.",
    },
    {
        "id": "source_revision_changes_after_compile",
        "component": "state_packet",
        "expected_mode": "fail_closed",
        "description": "Source revision drifts after compile; refuse stale packet use.",
    },
    {
        "id": "contradictory_evidence",
        "component": "verifier",
        "expected_mode": "fail_closed",
        "description": "Contradictory evidence → verified_success stays unknown/false; no self-credit.",
    },
    {
        "id": "sol_pi_projection_exception",
        "component": "sol_pi",
        "expected_mode": "fail_open",
        "description": "SoL-Pi projection throws; omit projection, continue shadow-only.",
    },
    {
        "id": "duplicate_replay",
        "component": "receipt_runner",
        "expected_mode": "fail_closed",
        "description": "Replaying the same receipt must not mint a second physical side effect.",
    },
    {
        "id": "stale_computer_use_observation",
        "component": "computer_use",
        "expected_mode": "fail_closed",
        "description": "Stale CU observation discarded; do not act on expired evidence.",
    },
    {
        "id": "verifier_unavailable",
        "component": "verifier",
        "expected_mode": "fail_open",
        "description": "Verifier down → verified_success remains unknown; never invent success.",
    },
    {
        "id": "local_model_oom_or_residency_miss",
        "component": "local_model",
        "expected_mode": "fail_open",
        "description": "Local model OOM/residency miss; skip local arm, do not credit success.",
    },
)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _identity_from_events(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    for row in rows:
        ident = _as_mapping(row.get("identity"))
        if ident.get("trace_id"):
            return {
                "harness_id": ident.get("harness_id") or "hermes",
                "session_id": ident.get("session_id"),
                "task_id": ident.get("task_id"),
                "turn_id": ident.get("turn_id"),
                "trace_id": str(ident["trace_id"]),
                "api_request_id": ident.get("api_request_id"),
            }
    raise ValueError("observer events must include identity.trace_id for join")


def _execution_completed(rows: Sequence[Mapping[str, Any]]) -> bool:
    terminal = {"post_api_request", "api_request_error", "on_session_end"}
    return any(row.get("event") in terminal for row in rows)


def _component_pointers(rows: Sequence[Mapping[str, Any]]) -> dict[str, str | None]:
    schemas = sorted({str(row.get("schema")) for row in rows if row.get("schema")})
    pointers: dict[str, str | None] = {schema: "joined_by_trace_id" for schema in schemas}
    # Envelope points at existing receipts; does not duplicate payloads.
    pointers.setdefault("z0int.hermes_observer_event.v1", None)
    return pointers


def build_experiment_receipt(
    *,
    experiment_id: str,
    arm: str,
    task_family: str,
    revisions: Mapping[str, str],
    observer_events: Sequence[Mapping[str, Any]],
    fixture_id: str | None = None,
    measurements: Mapping[str, Any] | None = None,
    verified_success: bool | None = None,
    verifier_id: str | None = None,
    abstained: bool = False,
    escalated: bool = False,
    physical_side_effect_id: str | None = None,
    invariant_violations: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a thin experiment envelope joined on stable Hermes identity."""
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}")
    if not revisions.get("hermes"):
        raise ValueError("revisions.hermes is required")
    identity = _identity_from_events(observer_events)
    if identity.get("harness_id") != "hermes":
        identity = dict(identity)
        identity["harness_id"] = "hermes"

    execution_completed = _execution_completed(observer_events)
    # Hard rule: never upgrade unknown/false verified_success from execution alone.
    if verified_success is True and not verifier_id:
        raise ValueError("verified_success=True requires verifier_id (no observer self-credit)")

    receipt = {
        "schema": EXPERIMENT_SCHEMA,
        "experiment_id": experiment_id,
        "arm": arm,
        "task_family": task_family,
        "fixture_id": fixture_id,
        "revisions": dict(revisions),
        "identity": identity,
        "component_receipts": _component_pointers(observer_events),
        "measurements": dict(measurements or {}),
        "outcome": {
            "execution_completed": bool(execution_completed),
            "verified_success": verified_success,
            "verifier_id": verifier_id,
            "abstained": bool(abstained),
            "escalated": bool(escalated),
            "duplicate_side_effect": False,
            "stale_answer": False,
            "invariant_violations": list(invariant_violations or []),
        },
        "physical_side_effect_id": physical_side_effect_id,
        "promotion_ready": False,
        "note": "Shadow join envelope only; no runtime authority or promotion implied.",
    }
    return receipt


def validate_experiment_receipt(receipt: Mapping[str, Any]) -> list[str]:
    """Return human-readable validation errors (empty list = ok)."""
    errors: list[str] = []
    if receipt.get("schema") != EXPERIMENT_SCHEMA:
        errors.append(f"schema must be {EXPERIMENT_SCHEMA}")
    if receipt.get("arm") not in ARMS:
        errors.append("arm is not a known experiment arm")
    if not _as_mapping(receipt.get("revisions")).get("hermes"):
        errors.append("revisions.hermes is required")
    ident = _as_mapping(receipt.get("identity"))
    if not ident.get("trace_id"):
        errors.append("identity.trace_id is required")
    if ident.get("harness_id") not in (None, "hermes"):
        errors.append("identity.harness_id must be hermes")

    outcome = _as_mapping(receipt.get("outcome"))
    if "execution_completed" not in outcome:
        errors.append("outcome.execution_completed is required")
    if "verified_success" not in outcome:
        errors.append("outcome.verified_success is required (bool or null/unknown)")

    verified = outcome.get("verified_success")
    execution_completed = outcome.get("execution_completed")
    verifier_id = outcome.get("verifier_id")

    # Never alias execution completion into verified success.
    if execution_completed is True and verified is True and not verifier_id:
        errors.append(
            "verified_success cannot be True from execution_completed alone; "
            "requires verifier_id (no observer self-credit)"
        )
    if verified is True and not verifier_id:
        errors.append("verified_success=True requires verifier_id")
    if receipt.get("promotion_ready") is not False:
        errors.append("promotion_ready must remain false on this shadow join layer")
    return errors


def record_replay_attempt(
    prior: Mapping[str, Any],
    *,
    physical_side_effect_id: str | None,
) -> dict[str, Any]:
    """Replay of the same receipt must not mint a second physical side effect."""
    out = json.loads(json.dumps(prior))  # deep copy via JSON (lab envelopes are JSON-safe)
    prior_fx = prior.get("physical_side_effect_id")
    outcome = dict(_as_mapping(out.get("outcome")))
    if prior_fx and physical_side_effect_id and prior_fx == physical_side_effect_id:
        outcome["duplicate_side_effect"] = True
    elif prior_fx and physical_side_effect_id and prior_fx != physical_side_effect_id:
        # Distinct effect id on replay of same experiment cell is still a violation.
        outcome["duplicate_side_effect"] = True
        violations = list(outcome.get("invariant_violations") or [])
        violations.append("replay_attempted_new_side_effect")
        outcome["invariant_violations"] = violations
    else:
        outcome["duplicate_side_effect"] = True
    # Preserve prior verification; never invent success on replay.
    out["outcome"] = outcome
    out["promotion_ready"] = False
    return out


def simulate_failure_case(case_id: str) -> dict[str, Any]:
    """Offline attribution for a catalogued failure (no Hermes behavior change)."""
    case = next((c for c in FAILURE_CASES if c["id"] == case_id), None)
    if case is None:
        raise KeyError(f"unknown failure case: {case_id}")
    mode = case["expected_mode"]
    return {
        "schema": "z0int.hermes_failure_injection.v0",
        "case_id": case_id,
        "component": case["component"],
        "expected_mode": mode,
        "attributable": True,
        "hermes_behavior_changed": False,
        "blocks_second_side_effect": case_id == "duplicate_replay" or mode == "fail_closed"
        and case_id in {
            "duplicate_replay",
            "source_revision_changes_after_compile",
            "stale_computer_use_observation",
            "contradictory_evidence",
        },
        "verified_success_policy": "unknown_or_independent_only",
        "promotion_ready": False,
        "description": case["description"],
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    join_p = sub.add_parser("join", help="Build experiment receipt from observer JSONL")
    join_p.add_argument("events", type=Path)
    join_p.add_argument("--experiment-id", required=True)
    join_p.add_argument("--arm", required=True, choices=ARMS)
    join_p.add_argument("--task-family", required=True)
    join_p.add_argument("--hermes-rev", required=True)
    join_p.add_argument("--fixture-id")
    join_p.add_argument("--verified-success", choices=["true", "false", "unknown"], default="unknown")
    join_p.add_argument("--verifier-id")
    join_p.add_argument("--output", type=Path)

    fail_p = sub.add_parser("fail", help="Simulate one failure-injection catalog case")
    fail_p.add_argument("case_id")
    fail_p.add_argument("--output", type=Path)

    list_p = sub.add_parser("list-failures", help="Print failure-injection catalog")

    args = parser.parse_args(argv)
    if args.cmd == "list-failures":
        print(json.dumps(list(FAILURE_CASES), indent=2))
        return
    if args.cmd == "fail":
        payload = simulate_failure_case(args.case_id)
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return

    verified: bool | None
    if args.verified_success == "true":
        verified = True
    elif args.verified_success == "false":
        verified = False
    else:
        verified = None
    receipt = build_experiment_receipt(
        experiment_id=args.experiment_id,
        arm=args.arm,
        task_family=args.task_family,
        revisions={"hermes": args.hermes_rev},
        observer_events=read_jsonl(args.events),
        fixture_id=args.fixture_id,
        verified_success=verified,
        verifier_id=args.verifier_id,
    )
    errors = validate_experiment_receipt(receipt)
    if errors:
        raise SystemExit("validation failed:\n- " + "\n- ".join(errors))
    rendered = json.dumps(receipt, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
