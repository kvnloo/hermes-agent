"""Track 1 spike (lab/track1/nanojev-spike): unit tests for agent/nanojev_shadow.

Stdlib-only: no torch, no z0int import, no network. Covers the turn
classifier (port of z0int.hermes_decisions.classify), the DecisionRequest
builder, and DecisionResult parsing. The live backend path is exercised by
lab/track1/bench_nanojev.py, not here.
"""

import json

from agent import nanojev_shadow as ns


def test_classify_user_turn_passes_through():
    excluded, text = ns.classify_turn("what is the capital of france?", platform="cli")
    assert excluded is None
    assert text == "what is the capital of france?"


def test_classify_strips_system_note_prefix():
    excluded, text = ns.classify_turn(
        "[System note: budget 80%] what is 2+2?", platform="telegram"
    )
    assert excluded is None
    assert text == "what is 2+2?"


def test_classify_excludes_system_messages():
    excluded, text = ns.classify_turn("[System: turn budget exceeded]", platform="cli")
    assert excluded == "system_message"
    assert text is None


def test_classify_excludes_empty():
    excluded, text = ns.classify_turn("   ", platform="cli")
    assert excluded == "empty"
    assert text is None


def test_classify_excludes_non_user_platforms():
    excluded, _ = ns.classify_turn("run the nightly job", platform="cron")
    assert excluded == "platform:cron"


def test_classify_joins_multimodal_blocks():
    excluded, text = ns.classify_turn(
        [{"type": "text", "text": "describe this"}, {"type": "image", "text": ""}],
        platform="cli",
    )
    assert excluded is None
    assert "describe this" in text


def test_build_decision_request_shape():
    req = ns.build_decision_request("do the thing", turn_id="t1")
    assert req["state"]["turn_text"] == "do the thing"
    assert req["state"]["turn_id"] == "t1"
    (q,) = req["questions"]
    assert q["id"] == "turn_action"
    assert q["type"] == "choice"
    assert [o["id"] for o in q["options"]] == ["ACT", "ASK", "ESCALATE"]
    # Finite JSON-compatible (the z0int contract requirement).
    json.dumps(req, allow_nan=False)


def test_build_decision_request_truncates_long_turns():
    req = ns.build_decision_request("x" * 5000)
    assert len(req["state"]["turn_text"]) <= 2000


def test_nanojev_verdict_parses_result():
    result = {
        "answers": [
            {
                "question_id": "turn_action",
                "type": "choice",
                "probabilities": {"ACT": 0.7, "ASK": 0.2, "ESCALATE": 0.1},
                "value": "ACT",
                "confidence": 0.7,
            }
        ]
    }
    choice, probs, conf = ns.nanojev_verdict(result)
    assert choice == "ACT"
    assert probs == {"ACT": 0.7, "ASK": 0.2, "ESCALATE": 0.1}
    assert conf == 0.7


def test_nanojev_verdict_rejects_unknown_choice():
    result = {
        "answers": [
            {
                "question_id": "turn_action",
                "type": "choice",
                "probabilities": {"ACT": 0.5, "BOGUS": 0.5},
                "value": "BOGUS",
            }
        ]
    }
    choice, probs, _ = ns.nanojev_verdict(result)
    assert choice is None
    assert set(probs) == {"ACT", "BOGUS"}


def test_nanojev_verdict_empty_result():
    assert ns.nanojev_verdict({}) == (None, {}, None)
    assert ns.nanojev_verdict({"answers": []}) == (None, {}, None)


def test_shadow_turn_excluded_never_touches_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("NANOJEV_SHADOW_DIR", str(tmp_path))
    monkeypatch.setenv("Z0INT_PYTHON", "/nonexistent/python")
    rec = ns.shadow_turn("[System: hi]", platform="cli")
    assert rec["excluded"] == "system_message"
    assert "nanojev_error" not in rec  # no backend call attempted
    rows = (tmp_path / "nanojev_shadow.jsonl").read_text().strip().splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["excluded"] == "system_message"


def test_shadow_turn_no_python_records_error(monkeypatch, tmp_path):
    monkeypatch.setenv("NANOJEV_SHADOW_DIR", str(tmp_path))
    monkeypatch.delenv("Z0INT_PYTHON", raising=False)
    rec = ns.shadow_turn("hello", platform="cli")
    assert rec["excluded"] is None
    assert "no z0int python" in rec["nanojev_error"]
