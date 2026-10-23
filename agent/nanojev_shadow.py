"""Track 1 spike (lab/track1/nanojev-spike): NanoJev as a shadow per-turn decider.

SEAM
----
Every user turn implicitly asks "what should this turn do?" z0int's
DecisionOpportunity answers it with ACT / ASK / ESCALATE (see
kvnloo/z0intelligence ``src/z0int/decision_opportunity.py`` ::
``deterministic_gate`` — first legal action by fixed priority, the #55
falsification baseline). Hermes core makes no such decision today: the turn
always goes to the frontier model. The z0int-decisions plugin
(``harness-adapters/hermes-z0int-decisions``) records opportunities in shadow.

This module wires z0int's NanoJev local decision backend (0.6B, CPU-capable)
as the decider for that question, in SHADOW MODE: it never alters a turn, it
only evaluates the ACT/ASK/ESCALATE choice and logs the verdict next to the
deterministic gate's, for agreement analysis.

WIRING
------
Hermes must not import z0int (not installed in its interpreter) and this
module stays stdlib-only — same rule as the z0int-decisions plugin. The
backend is reached via a detached child, exactly the way that plugin reaches
z0int::

    [z0int_python, -m, z0int.cli, backends, eval,
     --backend, nanojev, --input, <request.json>]

``z0int_python`` defaults to ``$Z0INT_PYTHON`` (the venv that has torch +
the NanoJev checkpoint); the checkpoint itself lives on the z0int side
(``~/.z0int/models/nanojev_06b`` or ``$Z0INT_NANOJEV_CHECKPOINT``).

INTEGRATION POINT
-----------------
Call :func:`shadow_turn` from a ``pre_llm_call`` plugin hook. It accepts the
same kwargs ``agent/turn_context._collect_pre_llm_call_context`` passes to
``hermes_cli.lifecycle.invoke_hook`` (``user_message``, ``turn_id``,
``session_id``, ``platform``, ...). It returns None (never hook context) and
appends one JSONL row per evaluated turn. Not wired to any hook yet — this
spike proves the backend runs and measures it; wiring is the follow-up.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Turn classification (port of z0int.hermes_decisions.classify — stdlib only).
# Kept in sync by hand; the z0int side owns the canonical version.
# ---------------------------------------------------------------------------

NON_USER_PLATFORMS = frozenset({"cron", "subagent", "curator", "kanban", "batch", "raft"})
SYSTEM_PREFIXES = (
    "[System:",
    "[SYSTEM:",
    "[SYSTEM NOTICE",
    "[IMPORTANT: Background process",
    "[IMPORTANT:",
    "<agent-message",
    "<task-notification",
    "[escaped: system-reminder",
)
NOTE_PREFIX = "[System note:"


def _strip_system_notes(text: str) -> str:
    text = text.lstrip()
    while text.startswith(NOTE_PREFIX):
        end = text.find("]")
        if end < 0:
            return ""
        text = text[end + 1 :].lstrip()
    return text


def classify_turn(user_message: Any, platform: str = "") -> Tuple[Optional[str], Optional[str]]:
    """Return ``(excluded_reason, text)``. ``excluded_reason`` None means a real
    user turn with ``text`` as the intent; otherwise the turn is not a decision
    opportunity and ``text`` is None."""
    if (platform or "").lower() in NON_USER_PLATFORMS:
        return f"platform:{platform.lower()}", None
    if isinstance(user_message, list):  # multimodal content blocks
        user_message = "\n".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in user_message
        )
    if not isinstance(user_message, str) or not user_message.strip():
        return "empty", None
    if user_message.lstrip().startswith(SYSTEM_PREFIXES):
        return "system_message", None
    text = _strip_system_notes(user_message)
    if not text:
        return "system_message", None
    return None, text


# ---------------------------------------------------------------------------
# The decision question (mirrors z0int's ACT/ASK/ESCALATE gate vocabulary).
# ---------------------------------------------------------------------------

TURN_QUESTION = {
    "id": "turn_action",
    "type": "choice",
    "instructions": (
        "What should this turn do about the user's request? "
        "ACT means answer or act on it directly. ASK means ask a clarifying "
        "question first. ESCALATE means surface it for capabilities, authority, "
        "or review beyond this turn."
    ),
    "options": [
        {
            "id": "ACT",
            "description": "The request is clear and within the agent's authority; proceed directly.",
        },
        {
            "id": "ASK",
            "description": "The request is ambiguous or missing information the user must supply; ask first.",
        },
        {
            "id": "ESCALATE",
            "description": "The request needs capabilities, authority, or review beyond this turn; escalate.",
        },
    ],
}

_EVAL_TIMEOUT_S = 600.0


def build_decision_request(turn_text: str, turn_id: Optional[str] = None) -> Dict[str, Any]:
    """Build the z0int DecisionRequest JSON for one turn.

    The state is deliberately minimal in this spike (turn text only); a real
    integration would attach the compiled state packet (see Track 4 / RLM).
    """
    return {
        "state": {"turn_text": turn_text[:2000], "turn_id": turn_id or ""},
        "questions": [TURN_QUESTION],
    }


def _z0int_python(explicit: Optional[str] = None) -> Optional[str]:
    return explicit or os.environ.get("Z0INT_PYTHON")


def evaluate_nanojev(
    request: Dict[str, Any],
    z0int_python: Optional[str] = None,
    timeout_s: float = _EVAL_TIMEOUT_S,
) -> Tuple[Optional[Dict[str, Any]], float, Optional[str]]:
    """Run one DecisionRequest through NanoJev via the z0int CLI child.

    Returns ``(result, latency_ms, error)``. ``result`` is the parsed
    DecisionResult dict on success, else None with ``error`` set. Never raises.
    """
    python = _z0int_python(z0int_python)
    if not python:
        return None, 0.0, "no z0int python (set Z0INT_PYTHON)"
    start = time.perf_counter()
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="nanojev_req_", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(request, fh, ensure_ascii=False)
            req_path = fh.name
        try:
            proc = subprocess.run(
                [
                    python,
                    "-m",
                    "z0int.cli",
                    "backends",
                    "eval",
                    "--backend",
                    "nanojev",
                    "--input",
                    req_path,
                ],
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        finally:
            try:
                os.unlink(req_path)
            except OSError:
                pass
    except Exception as exc:  # noqa: BLE001 - shadow must never break the turn
        return None, (time.perf_counter() - start) * 1000.0, f"{type(exc).__name__}: {exc}"
    latency_ms = (time.perf_counter() - start) * 1000.0
    if proc.returncode != 0:
        return None, latency_ms, f"z0int exited {proc.returncode}: {proc.stderr.strip()[-300:]}"
    try:
        return json.loads(proc.stdout), latency_ms, None
    except ValueError as exc:
        return None, latency_ms, f"bad JSON from z0int: {exc}"


def nanojev_verdict(result: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, float], Optional[float]]:
    """Extract (choice, probabilities, confidence) from a DecisionResult dict."""
    try:
        answers = result.get("answers") or []
        ans = next(a for a in answers if a.get("question_id") == "turn_action")
        probs = {str(k): float(v) for k, v in (ans.get("probabilities") or {}).items()}
        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}
        choice = ans.get("value")
        choice = str(choice) if choice in ("ACT", "ASK", "ESCALATE") else None
        conf = ans.get("confidence")
        return choice, probs, float(conf) if conf is not None else None
    except Exception:  # noqa: BLE001
        return None, {}, None


def shadow_records_path() -> Path:
    root = os.environ.get("NANOJEV_SHADOW_DIR") or (Path.home() / ".hermes-lab" / "track1")
    path = Path(root).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path / "nanojev_shadow.jsonl"


def append_record(record: Dict[str, Any]) -> None:
    try:
        with shadow_records_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.warning("nanojev_shadow: could not append record: %s", exc)


def shadow_turn(
    user_message: Any,
    *,
    turn_id: Optional[str] = None,
    session_id: Optional[str] = None,
    platform: str = "",
    z0int_python: Optional[str] = None,
    record: bool = True,
) -> Dict[str, Any]:
    """Shadow-evaluate one turn. Never raises; never returns hook context.

    Returns the record dict: classification, NanoJev verdict/probabilities/
    latency, or the exclusion/error reason.
    """
    t0 = time.perf_counter()
    excluded, text = classify_turn(user_message, platform)
    rec: Dict[str, Any] = {
        "schema": "hermes-lab.track1.nanojev_shadow.v1",
        "ts": time.time(),
        "turn_id": turn_id,
        "session_id": session_id,
        "platform": platform,
        "excluded": excluded,
    }
    if excluded is not None:
        rec["wall_ms"] = (time.perf_counter() - t0) * 1000.0
        if record:
            append_record(rec)
        return rec

    request = build_decision_request(text or "", turn_id)
    result, latency_ms, error = evaluate_nanojev(request, z0int_python)
    rec["nanojev_latency_ms"] = latency_ms
    if error is not None:
        rec["nanojev_error"] = error
    else:
        choice, probs, conf = nanojev_verdict(result or {})
        rec["nanojev_choice"] = choice
        rec["nanojev_probabilities"] = probs
        rec["nanojev_confidence"] = conf
    rec["wall_ms"] = (time.perf_counter() - t0) * 1000.0
    if record:
        append_record(rec)
    return rec


def hook_entry(**kwargs: Any) -> None:
    """``pre_llm_call``-shaped entry point (not wired yet — spike only).

    Accepts the kwargs ``agent/turn_context._collect_pre_llm_call_context``
    passes to ``hermes_cli.lifecycle.invoke_hook``. Returns None: a shadow
    hook must never inject context.
    """
    try:
        shadow_turn(
            kwargs.get("user_message"),
            turn_id=kwargs.get("turn_id"),
            session_id=kwargs.get("session_id"),
            platform=kwargs.get("platform") or "",
        )
    except Exception as exc:  # noqa: BLE001 - a shadow hook must never break a turn
        logger.warning("nanojev_shadow hook failed: %s", exc)
    return None


def summarize_records(path: Optional[Path] = None) -> Dict[str, Any]:
    """Agreement/latency summary over shadow records (for the bench)."""
    rows: List[Dict[str, Any]] = []
    p = path or shadow_records_path()
    try:
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except OSError:
        pass
    evaluated = [r for r in rows if not r.get("excluded") and r.get("nanojev_choice")]
    errors = [r for r in rows if r.get("nanojev_error")]
    lat = sorted(r["nanojev_latency_ms"] for r in evaluated if r.get("nanojev_latency_ms"))
    dist: Dict[str, int] = {}
    for r in evaluated:
        dist[r["nanojev_choice"]] = dist.get(r["nanojev_choice"], 0) + 1

    def pct(q: float) -> Optional[float]:
        return lat[min(len(lat) - 1, int(q * len(lat)))] if lat else None

    return {
        "turns": len(rows),
        "excluded": len(rows) - len(evaluated) - len(errors),
        "evaluated": len(evaluated),
        "errors": len(errors),
        "verdict_distribution": dist,
        "latency_ms_p50": pct(0.5),
        "latency_ms_p95": pct(0.95),
    }
