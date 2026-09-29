"""Frozen-input gate for the Hermes lane of z0evals#56.

The six family labels in PR #57 are not executable questions. Refuse to call
those labels a frozen cohort when prompts, evidence and an oracle are absent.
"""
from __future__ import annotations

import json
import re

QUESTION_IDS = (
    "exact-identifier", "supersession", "cross-harness", "contradiction",
    "missing-evidence", "minimal-context",
)
Z0INT_REVISION = "c4a4554d8a3874b456c46feef6ea937993af744a"
SCHEMA_REVISION = "e41696618c12e6556b49b98ca57a5902833a5a72"
CACHE_REVISION = "3e762e9d8f2f71fd89e0909911b23be44e22c9e3"


def validate_frozen_bundle(bundle: dict) -> dict:
    """Check an operator-supplied DSH freeze; never invent missing fields."""
    def require(condition):
        if not condition:
            raise ValueError("Incomplete freeze")

    try:
        origin = bundle["origin"]
        require(origin["harness"] == "dsh")
        require(re.fullmatch(r"[0-9a-f]{40}", origin["revision"]))
        require(isinstance(origin["locator"], str) and origin["locator"])
        questions = bundle["questions"]
        require(len(questions) == len(QUESTION_IDS))
        require({q["id"] for q in questions} == set(QUESTION_IDS))
        for question in questions:
            require(isinstance(question["prompt"], str) and question["prompt"].strip())
            sources = question["sources"]
            require(isinstance(sources, list) and sources)
            ids = [s["source_id"] for s in sources]
            require(len(ids) == len(set(ids)))
            for source in sources:
                require(isinstance(source["source_id"], str) and source["source_id"])
                require(isinstance(source["path"], str) and source["path"])
                require(re.fullmatch(r"[0-9a-f]{64}", source["sha256"]))
            expected = question["expected_evidence"]
            require(isinstance(expected, list) and set(expected) <= set(ids))
            oracle = question["verification"]
            require(isinstance(oracle["answer"], str))
            require(isinstance(oracle["abstained"], bool))
            require(isinstance(oracle["citations"], list))
            require(set(oracle["citations"]) == set(expected))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Missing or invalid frozen DSH prompts, source pointers, or verification oracle") from exc
    return bundle


def verify_answer(question, packet, answer, *, injected, model_completed):
    """Exact structured oracle, not a model judge or retrieval=use inference.

    The caller must pin the oracle before running and independently inspect its
    relationship to the sources. Only a correctly cited supported answer or an
    actual gap + explicit abstention can verify. Execution success is separate.
    """
    result = {"verified": False, "answer_supported": False, "abstained": False}
    try:
        parsed = json.loads(answer)
        if not isinstance(parsed, dict):
            return result
        result["abstained"] = parsed.get("abstained") is True
        if not injected or not model_completed or parsed != question["verification"]:
            return result
        if type(parsed.get("abstained")) is not bool:
            return result
        refs = packet.get("evidence", [])
        gaps = packet.get("unresolved_gaps", [])
        cited = set(parsed["citations"])
        expected = set(question["expected_evidence"])
        actual = {r["source_id"] for r in refs}
        provenance = all(r.get("source_id") and r.get("locator") and r.get("trust_class")
                         and re.fullmatch(r"sha256:[0-9a-f]{64}", r.get("source_version", "")) for r in refs)
        if result["abstained"]:
            result["verified"] = bool(gaps) and not cited and not parsed["answer"]
        elif provenance and not gaps and cited == expected and expected and expected <= actual:
            result["answer_supported"] = result["verified"] = True
    except (ValueError, KeyError, TypeError):
        pass
    return result
