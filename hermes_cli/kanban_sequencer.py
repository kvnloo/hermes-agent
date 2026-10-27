"""Supervise ordered kanban tasks through injected spawn, recovery, and ledger ports.

This module never owns worker processes, a board database, or a CLI entry point.
The spawn port must return a settled status for each attempt; the ledger port
durably records each settled attempt before the next attempt can begin.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class Step:
    task_id: str
    body: str
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id must not be empty")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


@dataclass(frozen=True)
class SequenceResult:
    completed: list[str]
    stopped_at: str | None
    reason: str | None
    attempts: int


class _RecoveryDecision(Protocol):
    action: str
    reason: str
    signature: str | None


def _fresh_seed(step: Step, failures: Sequence[Mapping[str, Any]]) -> str:
    """Use the session-poison policy when installed; otherwise seed from the task.

    The fallback intentionally carries no previous conversation or error text.
    """
    try:
        from agent.kanban_session_poison import fresh_session_seed
    except ModuleNotFoundError as exc:
        if exc.name != "agent.kanban_session_poison":
            raise
        prefix = f"Task {step.task_id} (fresh session retry):\n"
        suffix = "\nFinish with kanban_complete or kanban_block."
        room = 4000 - len(prefix) - len(suffix)
        return prefix + step.body.strip()[:max(0, room)] + suffix
    return fresh_session_seed(step.body, failures)


def run_sequence(
    steps: Iterable[Step],
    *,
    spawn: Callable[..., Mapping[str, Any]],
    policy: Callable[[Sequence[Mapping[str, Any]]], _RecoveryDecision],
    ledger: Callable[[dict[str, Any]], None],
    sleep: Callable[[float], None] = time.sleep,
    delays: Sequence[float] = (15, 45, 90),
) -> SequenceResult:
    """Run tasks in order, stopping at the first block, hard failure, or budget.

    The policy sees the failed settled results for the current step, in order.
    A fresh-session retry starts from a seed; an in-place retry retains the
    worker session and applies bounded backoff. The injected ledger is the sole
    write port, so a ledger failure aborts rather than silently losing evidence.
    """
    if not delays:
        raise ValueError("delays must contain at least one backoff interval")

    completed: list[str] = []
    total_attempts = 0

    for step in steps:
        failures: list[Mapping[str, Any]] = []
        fresh = False
        seed: str | None = None

        for attempt in range(1, step.max_attempts + 1):
            result = spawn(step, fresh=fresh, seed=seed)
            total_attempts += 1
            status = result["status"]
            reason: str | None = None
            signature: str | None = None

            if status == "done":
                action = "advance"
            elif status == "blocked":
                action = "stop"
                reason = str(result.get("reason") or "blocked: human input required")
            elif status == "failed":
                failures.append(result)
                decision = policy(tuple(failures))
                action = decision.action
                reason = decision.reason
                signature = decision.signature
                if action not in ("in_place", "fresh_session", "stop"):
                    raise ValueError(f"invalid recovery action: {action!r}")
                if action != "stop" and attempt == step.max_attempts:
                    action = "stop"
                    reason = f"attempt budget exhausted ({step.max_attempts}) for {step.task_id}"
            else:
                raise ValueError(f"invalid settled status: {status!r}")

            ledger({
                "task_id": step.task_id,
                "attempt": attempt,
                "fresh": fresh,
                "status": status,
                "action": action,
                "reason": reason,
                "signature": signature,
            })

            if action == "advance":
                completed.append(step.task_id)
                break
            if action == "stop":
                return SequenceResult(completed, step.task_id, reason, total_attempts)
            if action == "in_place":
                sleep(delays[min(attempt - 1, len(delays) - 1)])
                fresh = False
                seed = None
            else:
                seed = _fresh_seed(step, failures)
                if not seed.strip():
                    raise ValueError("fresh-session policy produced an empty seed")
                fresh = True

    return SequenceResult(completed, None, None, total_attempts)
