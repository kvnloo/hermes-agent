"""External aux-LLM reference provider using the existing ctx.llm contract.

Not a host DecisionProvider / routing framework. Plugins already reach auxiliary
models via ctx.llm.complete_structured(..., task=...). This adapter:

- projects caller state through a bounded allowlist
- asks for a full label/mass distribution (never argmax-only)
- labels masses as self_estimated_not_calibrated
- stays advisory: no automatic security/authorization gate
- does not mutate host aux-task tables or context-tool prompts
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

# plugin_llm.PluginLlm.complete_structured keyword-only parameters (exact).
_COMPLETE_STRUCTURED_KW = frozenset(
    {
        "instructions",
        "input",
        "json_schema",
        "json_mode",
        "schema_name",
        "system_prompt",
        "provider",
        "model",
        "temperature",
        "max_tokens",
        "timeout",
        "agent_id",
        "profile",
        "purpose",
        "task",
    }
)

_STRUCTURED_RESULT_FIELDS = (
    "text",
    "provider",
    "model",
    "agent_id",
    "usage",
    "parsed",
    "content_type",
    "audit",
)

BOUNDED_STATE_ALLOWLIST = frozenset(
    {
        "request",
        "candidate_ids",
        "query",
        "excerpts",
    }
)

AUX_TASK_KEY = "jev_mimic_aux_decision"
PROBABILITY_KIND = "self_estimated_not_calibrated"

JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answers"],
    "properties": {
        "answers": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": False,
                "required": ["labels", "masses"],
                "properties": {
                    "labels": {"type": "array", "items": {"type": "string"}},
                    "masses": {"type": "array", "items": {"type": "number"}},
                },
            },
        }
    },
}

INSTRUCTIONS = (
    "Return one full distribution per question id. masses are self-estimated "
    "ranking scores, not calibrated confidence. Preserve every label; do not "
    "collapse to a single winner. Do not decide authorization or security."
)


@dataclass(frozen=True)
class ExactCtxLlmContract:
    complete_structured_kwargs = _COMPLETE_STRUCTURED_KW
    structured_result_fields = _STRUCTURED_RESULT_FIELDS


def project_state(raw: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: raw[k] for k in BOUNDED_STATE_ALLOWLIST if k in raw}


class AuxLlmReferenceProvider:
    """Caller-owned adapter around an existing ctx.llm instance."""

    def __init__(self, llm: Any, *, host_aux_baseline: Optional[Dict[str, Any]] = None) -> None:
        self._llm = llm
        self._host_aux_baseline = host_aux_baseline

    def evaluate(
        self,
        *,
        projected_state: Mapping[str, Any],
        questions: Sequence[Mapping[str, Any]],
        purpose: str = "aux-llm-reference",
        task: str = AUX_TASK_KEY,
        timeout: float = 8.0,
    ) -> Dict[str, Any]:
        import json

        state = project_state(projected_state)
        payload = {
            "state": state,
            "questions": [{"id": q["id"], "labels": list(q["labels"])} for q in questions],
        }
        result = self._llm.complete_structured(
            instructions=INSTRUCTIONS,
            input=[{"type": "text", "text": json.dumps(payload, sort_keys=True)}],
            json_schema=JSON_SCHEMA,
            json_mode=True,
            schema_name="aux.decision.distribution",
            system_prompt=None,
            provider=None,
            model=None,
            temperature=0.0,
            max_tokens=256,
            timeout=timeout,
            agent_id=None,
            profile=None,
            purpose=purpose,
            task=task,
        )
        parsed = getattr(result, "parsed", None)
        normalized = _normalize(parsed, questions)
        if normalized is None:
            return {
                "status": "unavailable",
                "available": False,
                "advisory_only": True,
                "normalized_output": None,
                "fallback": "continue_original_workflow",
                "policy": "caller_owned_no_automatic_security_gate",
                "probability_kind": PROBABILITY_KIND,
                "backend": {
                    "provider": getattr(result, "provider", None),
                    "model": getattr(result, "model", None),
                },
            }
        return {
            "status": "ok",
            "available": True,
            "advisory_only": True,
            "normalized_output": normalized,
            "fallback": "continue_original_workflow",
            "policy": "caller_owned_no_automatic_security_gate",
            "probability_kind": PROBABILITY_KIND,
            "backend": {
                "provider": getattr(result, "provider", None),
                "model": getattr(result, "model", None),
            },
        }


def _normalize(parsed: Any, questions: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(parsed, dict) or "answers" not in parsed:
        return None
    answers_in = parsed["answers"]
    if not isinstance(answers_in, dict):
        return None
    expected = {q["id"] for q in questions}
    if set(answers_in) != expected:
        return None
    out: Dict[str, Any] = {}
    for q in questions:
        qid = q["id"]
        block = answers_in[qid]
        labels = list(q["labels"])
        if not isinstance(block, dict):
            return None
        got_labels = block.get("labels")
        masses = block.get("masses")
        if list(got_labels) != labels:
            return None
        if not isinstance(masses, list) or len(masses) != len(labels):
            return None
        try:
            floats = [float(m) for m in masses]
        except (TypeError, ValueError):
            return None
        out[qid] = {
            "labels": labels,
            "masses": floats,
            "probability_kind": PROBABILITY_KIND,
        }
    return {"answers": out}
