"""RED→GREEN coverage for the common Hermes integration receipt + failure runner (#322)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "lab" / "z0_hermes_observer" / "receipt_runner.py"


def _load():
    spec = importlib.util.spec_from_file_location("receipt_runner_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _identity(**extra):
    base = {
        "harness_id": "hermes",
        "session_id": "sess",
        "task_id": "task",
        "turn_id": "turn-1",
        "trace_id": "trace-1",
        "api_request_id": "req-1",
    }
    base.update(extra)
    return base


def test_failure_catalog_covers_required_cases_with_expected_mode():
    module = _load()
    cases = {c["id"]: c for c in module.FAILURE_CASES}
    required = {
        "z0int_backend_unavailable",
        "malformed_backend_response",
        "state_packet_source_disappears",
        "source_revision_changes_after_compile",
        "contradictory_evidence",
        "sol_pi_projection_exception",
        "duplicate_replay",
        "stale_computer_use_observation",
        "verifier_unavailable",
        "local_model_oom_or_residency_miss",
    }
    assert required <= set(cases)
    for case_id in required:
        assert cases[case_id]["expected_mode"] in {"fail_open", "fail_closed"}
        assert cases[case_id]["description"]


def test_build_receipt_joins_by_trace_and_keeps_execution_vs_verified_apart():
    module = _load()
    observer_rows = [
        {
            "schema": "z0int.hermes_observer_event.v1",
            "event": "pre_api_request",
            "identity": _identity(),
            "fields": {"provider": "p", "model": "m"},
        },
        {
            "schema": "z0int.hermes_observer_event.v1",
            "event": "post_api_request",
            "identity": _identity(),
            "fields": {},
        },
    ]
    receipt = module.build_experiment_receipt(
        experiment_id="exp-1",
        arm="Z",
        task_family="api.attempt_will_fail",
        revisions={"hermes": "abc123"},
        observer_events=observer_rows,
        fixture_id="fix-1",
        measurements={"wall_ms": 12.5, "retries": 0},
        verified_success=None,  # independent verifier unknown
        verifier_id=None,
    )
    assert receipt["schema"] == module.EXPERIMENT_SCHEMA
    assert receipt["identity"]["trace_id"] == "trace-1"
    assert receipt["identity"]["harness_id"] == "hermes"
    assert receipt["outcome"]["execution_completed"] is True
    # Unknown stays unknown; execution completion must not mint success.
    assert receipt["outcome"]["verified_success"] is None
    assert receipt["outcome"]["execution_completed"] is not receipt["outcome"]["verified_success"]
    assert receipt["promotion_ready"] is False
    assert "z0int.hermes_observer_event.v1" in receipt["component_receipts"]


def test_validate_rejects_self_credited_success_and_aliasing():
    module = _load()
    good = module.build_experiment_receipt(
        experiment_id="exp-2",
        arm="H0",
        task_family="smoke",
        revisions={"hermes": "abc"},
        observer_events=[{
            "schema": "z0int.hermes_observer_event.v1",
            "event": "api_request_error",
            "identity": _identity(trace_id="t2", api_request_id="r2"),
            "fields": {},
        }],
        verified_success=False,
        verifier_id="oracle-fixture",
    )
    assert module.validate_experiment_receipt(good) == []

    aliased = dict(good)
    aliased["outcome"] = dict(good["outcome"])
    aliased["outcome"]["execution_completed"] = True
    aliased["outcome"]["verified_success"] = True  # illegal self-upgrade without verifier
    aliased["outcome"]["verifier_id"] = None
    errors = module.validate_experiment_receipt(aliased)
    assert any("verified_success" in e or "verifier" in e for e in errors)

    promoted = dict(good)
    promoted["promotion_ready"] = True
    assert any("promotion_ready" in e for e in module.validate_experiment_receipt(promoted))


def test_replay_same_receipt_does_not_mint_second_side_effect():
    module = _load()
    first = module.build_experiment_receipt(
        experiment_id="exp-3",
        arm="Z",
        task_family="smoke",
        revisions={"hermes": "abc"},
        observer_events=[{
            "schema": "z0int.hermes_observer_event.v1",
            "event": "post_api_request",
            "identity": _identity(trace_id="t3"),
            "fields": {},
        }],
        verified_success=False,
        verifier_id="oracle",
        physical_side_effect_id="fx-1",
    )
    second = module.record_replay_attempt(first, physical_side_effect_id="fx-1")
    assert second["outcome"]["duplicate_side_effect"] is True
    assert second["outcome"]["execution_completed"] == first["outcome"]["execution_completed"]
    # Replay must not invent a new verified success.
    assert second["outcome"]["verified_success"] == first["outcome"]["verified_success"]


def test_simulate_failure_case_is_attributable_and_respects_mode():
    module = _load()
    result = module.simulate_failure_case("z0int_backend_unavailable")
    assert result["case_id"] == "z0int_backend_unavailable"
    assert result["expected_mode"] == "fail_open"
    assert result["component"] == "z0int"
    assert result["attributable"] is True
    assert result["hermes_behavior_changed"] is False

    dup = module.simulate_failure_case("duplicate_replay")
    assert dup["expected_mode"] == "fail_closed"
    assert dup["blocks_second_side_effect"] is True
