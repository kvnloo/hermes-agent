"""Behavior contracts for the poisoned kanban session policy (#664)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from agent.error_classifier import FailoverReason
from agent.kanban_session_poison import (
    RecoveryDecision,
    classify_failure,
    failure_signature,
    fresh_session_seed,
)


def _failed(
    reason: FailoverReason = FailoverReason.timeout,
    error: str = "ReadTimeout: upstream timed out after 15 seconds",
    **extra,
) -> dict:
    return {
        "failed": True,
        "completed": False,
        "failure_retryable": True,
        "failure_reason": reason.value,
        "error": error,
        "final_response": "API call failed after retries",
        "messages": [],
        **extra,
    }


def _success() -> dict:
    return {"failed": False, "completed": True, "final_response": "Done", "messages": []}


@pytest.mark.parametrize(
    "reason",
    [
        pytest.param(FailoverReason.rate_limit, id="rate-limit"),
        pytest.param(FailoverReason.billing, id="billing"),
        pytest.param(FailoverReason.upstream_rate_limit, id="upstream-rate-limit"),
        pytest.param(FailoverReason.auth_permanent, id="permanent-auth"),
        pytest.param(FailoverReason.model_entitlement, id="entitlement"),
        pytest.param(FailoverReason.content_policy_blocked, id="content-policy"),
        pytest.param(FailoverReason.data_policy_denied, id="data-policy"),
    ],
)
def test_unrecoverable_failures_stop(reason):
    decision = classify_failure([_failed(reason)])
    assert decision.action == "stop"
    assert decision.reason == "non_recoverable_reason"
    assert decision.signature is not None


@pytest.mark.parametrize(
    "reason",
    [
        pytest.param(FailoverReason.context_overflow, id="context-overflow"),
        pytest.param(FailoverReason.payload_too_large, id="payload-too-large"),
        pytest.param(FailoverReason.format_error, id="format-error"),
        pytest.param(FailoverReason.role_alternation, id="role-alternation"),
        pytest.param(FailoverReason.invalid_encrypted_content, id="encrypted-replay"),
        pytest.param(FailoverReason.thinking_signature, id="thinking-signature"),
        pytest.param(FailoverReason.image_corrupt, id="corrupt-image"),
    ],
)
def test_first_session_borne_failure_requires_fresh_session(reason):
    decision = classify_failure([_failed(reason)])
    assert decision.action == "fresh_session"
    assert decision.reason == "session_borne_failure"


def test_terminal_max_iterations_blocks_even_a_session_borne_failure():
    exhausted = _failed(
        FailoverReason.context_overflow,
        turn_exit_reason="max_iterations_reached(5/5)",
    )
    assert failure_signature(exhausted) is None
    assert classify_failure([exhausted]) == RecoveryDecision("stop", "terminal_turn", None)


def test_success_interrupt_and_empty_history_cannot_authorize_recovery():
    assert failure_signature(_success()) is None
    assert classify_failure([]).action == "stop"
    assert classify_failure([_failed(), _success()]).action == "stop"
    interrupted = _failed(interrupted=True)
    assert failure_signature(interrupted) is None
    assert classify_failure([interrupted]).action == "stop"


def test_repeated_identical_transient_error_rotates_the_session():
    result = _failed()
    assert classify_failure([result]).action == "in_place"
    decision = classify_failure([result, _failed()])
    assert decision.action == "fresh_session"
    assert decision.reason == "repeated_failure"
    assert decision.signature == failure_signature(result)


def test_different_transient_errors_stay_in_place():
    first = _failed(FailoverReason.timeout, "ReadTimeout: connection timed out")
    second = _failed(FailoverReason.server_error, "HTTPStatusError: gateway unavailable")
    assert classify_failure([first, second]).action == "in_place"


def test_different_messages_with_the_same_reason_do_not_count_as_poison():
    first = _failed(error="ReadTimeout: peer closed connection")
    second = _failed(error="ReadTimeout: request timed out")
    assert classify_failure([first, second]).action == "in_place"


def test_success_breaks_a_consecutive_failure_streak():
    result = _failed()
    assert classify_failure([result, _success(), result]).action == "in_place"


@pytest.mark.parametrize(
    "reason",
    [FailoverReason.timeout, FailoverReason.overloaded, FailoverReason.server_error],
)
def test_single_transient_failure_is_in_place(reason):
    assert classify_failure([_failed(reason)]).action == "in_place"


def test_signature_normalizes_ids_numbers_and_posix_temp_paths():
    earlier = _failed(
        error="ReadTimeout: request_id=req-1928 at /tmp/run-8356/out.log after 15 seconds\n"
              "internal previous-message content",
    )
    later = _failed(
        error="ReadTimeout: request_id=req-9273 at /tmp/run-9765/out.log after 90 seconds\n"
              "a different second line",
    )
    a, b = failure_signature(earlier), failure_signature(later)
    assert a is not None and a == b
    assert "req-1928" not in a
    assert "/tmp/" not in a
    assert "15" not in a
    assert "internal previous-message content" not in a
    assert classify_failure([earlier, later]).action == "fresh_session"


@pytest.mark.parametrize(
    ("first_location", "second_location"),
    [
        pytest.param(
            "/tmp/run-1928/SocketError.log", "/tmp/run-9765/RequestFailure.log",
            id="posix-path",
        ),
        pytest.param(
            r"C:\scratch\SocketError.log", r"C:\scratch\RequestFailure.log",
            id="windows-path",
        ),
        pytest.param(
            "https://example.invalid/SocketError?id=1928",
            "https://example.invalid/RequestFailure?id=9765",
            id="url",
        ),
        pytest.param(
            "SocketError@example.invalid", "RequestFailure@example.invalid",
            id="email",
        ),
    ],
)
def test_exception_looking_locations_cannot_change_inferred_class(
    first_location, second_location,
):
    first = _failed(error=f"gateway rejected value at {first_location} after 15 seconds")
    second = _failed(error=f"gateway rejected value at {second_location} after 90 seconds")
    signature = failure_signature(first)
    assert signature is not None
    assert signature == failure_signature(second)
    assert "|unclassified|" in signature
    assert classify_failure([first, second]).action == "fresh_session"


def test_inferred_class_ignores_path_before_real_exception():
    result = _failed(error="at /tmp/run-123/SocketError.py: provider.ReadTimeout: disconnected")
    signature = failure_signature(result)
    assert signature is not None
    assert "|readtimeout|" in signature
    assert "|socketerror|" not in signature


@pytest.mark.parametrize("threshold", [True, False, 2.0, 2.5, "2", None])
def test_repeat_threshold_rejects_noninteger_values(threshold):
    with pytest.raises(ValueError, match="repetition_threshold"):
        classify_failure([_failed()], repetition_threshold=threshold)


def test_signature_prefers_structured_exception_class():
    result = _failed(error="connection lost", error_class="provider.exceptions.ReadTimeout")
    assert "|readtimeout|" in failure_signature(result)


def test_signature_is_none_for_nonfailed_partial_turn():
    result = {"completed": False, "partial": True, "error": "timeout", "messages": []}
    assert failure_signature(result) is None
    assert classify_failure([result]).action == "stop"


def test_repeat_threshold_accepts_config_value_not_global_state():
    failures = [_failed(), _failed(), _failed()]
    assert classify_failure(failures[:2], repetition_threshold=3).action == "in_place"
    assert classify_failure(failures, repetition_threshold=3).action == "fresh_session"
    with pytest.raises(ValueError, match="repetition_threshold"):
        classify_failure(failures, repetition_threshold=1)


def test_stop_reasons_take_precedence_over_identical_signatures():
    failures = [_failed(FailoverReason.billing), _failed(FailoverReason.billing)]
    assert classify_failure(failures).action == "stop"


def test_decision_is_immutable():
    decision = classify_failure([_failed()])
    with pytest.raises(FrozenInstanceError):
        decision.action = "stop"


def test_seed_deduplicates_signatures_without_copying_conversation():
    first = _failed(
        error="ReadTimeout: request_id=req-123 at /tmp/run-1/log after 1 seconds",
        messages=[{"role": "user", "content": "HISTORY_SENTINEL"}],
    )
    duplicate = _failed(
        error="ReadTimeout: request_id=req-999 at /tmp/run-9/log after 8 seconds",
        final_response="UNRELATED_PREVIOUS_TURN_TEXT",
    )
    seed = fresh_session_seed("Finish the assigned kanban task", [first, duplicate], max_chars=900)
    signature = failure_signature(first)
    assert signature == failure_signature(duplicate)
    assert seed.startswith("Task:\nFinish the assigned kanban task")
    assert seed.count(f"- {signature}") == 1
    assert "kanban_complete" in seed and "kanban_block" in seed
    assert "HISTORY_SENTINEL" not in seed
    assert "UNRELATED_PREVIOUS_TURN_TEXT" not in seed
    assert "req-123" not in seed


def test_seed_bounds_long_task_and_failure_history_and_preserves_terminal_call():
    failures = [
        _failed(error=f"ReadTimeout: batch {n} raised a provider-side error")
        for n in range(100)
    ]
    seed = fresh_session_seed("T" * 10_000, failures, max_chars=600)
    assert len(seed) <= 600
    assert seed.startswith("Task:\n")
    assert "kanban_complete(...)" in seed
    assert "kanban_block(...)" in seed
    assert "Do not replay" not in seed  # the actual instruction is 'never replay'
    assert "never replay previous conversation history" in seed


def test_seed_handles_minimal_budget_without_exceeding_it():
    assert fresh_session_seed("task", [], max_chars=0) == ""
    assert len(fresh_session_seed("task", [], max_chars=50)) <= 50
    with pytest.raises(ValueError, match="max_chars"):
        fresh_session_seed("task", [], max_chars=-1)
