"""Follow-up probes for RFC #143379 comment 6412944809 (xngg1021), run on upstream main.

Each test asserts the behaviour the comment CLAIMS. A PASS means the claim reproduces on
the checked-out commit; a FAIL means it does not. No network, no model, scratch HERMES_HOME.

F1  Anchor Index survives only one compaction generation (_augment_summary_lean).
F1c Reference carry-forward (study-only, not a proposed patch): union keeps both generations.
F2  Reasoning-field fallback is sliced to 8,000 chars with finish_reason still "stop",
    so the finish_reason=="length" partial-summary guard cannot see it.
F3  session_search scroll returns message content uncapped (read shape caps at 2,000).
"""
import json
import re

from agent import context_compressor as cc
from agent.auxiliary_client import extract_content_or_reasoning

SHA_GEN1 = "a1b2c3d4e5f6a7b8c9d0"  # 20-hex, matches the commits pattern
SHA_GEN2 = "0f9e8d7c6b5a49382716"
PATH_GEN1 = "tools/alpha_probe_tool.py"


def _bare_compressor():
    comp = object.__new__(cc.ContextCompressor)
    comp.tail_mode = "lean"
    comp._session_id = "probe-session"
    return comp


def _turns(sha, path=None):
    text = f"Pinned constraint: do not touch commit {sha}."
    if path:
        text += f" Edit only {path}."
    return [{"role": "assistant", "content": text}, {"role": "tool", "content": f"ok {sha}"}]


def _anchor_section(summary):
    i = summary.find(cc._LEAN_ANCHOR_HEADING)
    return "" if i < 0 else summary[i:]


def test_f1_llm_drops_heading_gen1_anchor_lost():
    comp = _bare_compressor()
    s1 = comp._augment_summary_lean("Narrative gen 1.", _turns(SHA_GEN1, PATH_GEN1))
    assert SHA_GEN1 in _anchor_section(s1)
    # Gen 2: the iterative-update prompt does not ask the LLM to keep the Anchor Index,
    # so a faithful-but-lossy rewrite returns narrative only.
    s2 = comp._augment_summary_lean("Narrative gen 2 (rewritten).", _turns(SHA_GEN2))
    assert SHA_GEN2 in _anchor_section(s2)
    assert SHA_GEN1 not in s2, "claim: gen-1 anchor lost after one generation"
    assert PATH_GEN1 not in s2


def test_f1_llm_keeps_heading_gen2_anchor_never_added():
    comp = _bare_compressor()
    s1 = comp._augment_summary_lean("Narrative gen 1.", _turns(SHA_GEN1))
    # Gen 2: the LLM echoes the previous summary, heading included, then adds narrative.
    s2 = comp._augment_summary_lean(s1 + "\n\nNarrative gen 2.", _turns(SHA_GEN2))
    assert SHA_GEN1 in s2
    # The augment step only appends when the heading is absent, so gen-2 anchors are skipped.
    assert SHA_GEN2 not in s2, "finding: heading present -> new generation's anchors never harvested"


def _carry_forward_augment(comp, summary, turns, previous_summary):
    """Study-only reference: union prior + new anchor lines outside the LLM body, under the budget."""
    def lines(s):
        sec = _anchor_section(s or "")
        body = sec.split("\n", 1)[1] if "\n" in sec else ""
        body = re.split(r"\n## ", body, maxsplit=1)[0]
        return [ln for ln in body.splitlines() if ln.strip()]
    new_body = cc._redact_compaction_text(cc._build_anchor_index(turns))
    merged, seen, used = [], set(), 0
    for ln in lines(new_body if new_body.strip() else "") + lines(previous_summary) + lines(summary):
        if ln in seen or used + len(ln) > cc._LEAN_ANCHOR_BUDGET_CHARS:
            continue
        seen.add(ln); merged.append(ln); used += len(ln) + 1
    i = summary.find(cc._LEAN_ANCHOR_HEADING)
    body = summary if i < 0 else summary[:i].rstrip()
    body += "\n\n" + cc._LEAN_ANCHOR_HEADING + "\n" + "\n".join(merged)
    return comp._augment_summary_lean(body, turns)


def test_f1c_carry_forward_keeps_both_generations_in_both_llm_behaviours():
    comp = _bare_compressor()
    s1 = comp._augment_summary_lean("Narrative gen 1.", _turns(SHA_GEN1, PATH_GEN1))
    drop = _carry_forward_augment(comp, "Narrative gen 2.", _turns(SHA_GEN2), s1)
    keep = _carry_forward_augment(comp, s1 + "\n\nNarrative gen 2.", _turns(SHA_GEN2), s1)
    s3 = _carry_forward_augment(comp, "Narrative gen 3.", _turns("deadbeefcafe12345678"), drop)
    for s in (drop, keep):
        assert SHA_GEN1 in s and SHA_GEN2 in s and PATH_GEN1 in s
        assert s.count(cc._LEAN_ANCHOR_HEADING) == 1
    assert SHA_GEN1 in s3 and SHA_GEN2 in s3 and "deadbeefcafe12345678" in s3


class _Msg:
    def __init__(self, content, reasoning_content):
        self.content = content
        self.reasoning_content = reasoning_content


class _Choice:
    def __init__(self, msg, finish_reason):
        self.message = msg
        self.finish_reason = finish_reason


class _Resp:
    def __init__(self, msg, finish_reason):
        self.choices = [_Choice(msg, finish_reason)]


def test_f2_reasoning_fallback_sliced_without_length_signal():
    body = "".join(f"- item {i}: kept fact {i:05d}\n" for i in range(600))  # ~17K chars
    tail_fact = "- item 599: kept fact 00599"
    resp = _Resp(_Msg("", body), "stop")
    out = extract_content_or_reasoning(resp, max_reasoning_chars=8000)
    assert len(body) > 8000 and len(out) == 8000
    assert tail_fact not in out, "tail of the summary is dropped"
    # The compressor's partial-summary guard keys on finish_reason only.
    assert cc._response_finish_reason(resp) == "stop"
    assert cc._TRUNCATED_SUMMARY_MARKER not in out


def test_f3_scroll_content_uncapped(tmp_path):
    from hermes_state import SessionDB
    from tools.session_search_tool import session_search, _READ_MAX_CONTENT

    db = SessionDB(tmp_path / "state.db")
    db.create_session("s_big", source="cli")
    db.append_message("s_big", role="user", content="probe archive start")
    db.append_message("s_big", role="tool", content="X" * 74_000)
    db.append_message("s_big", role="assistant", content="probe archive end")
    read = json.loads(session_search(session_id="s_big", db=db))
    rows = read.get("messages") or []
    big_read = [m for m in rows if (m.get("original_content_chars") or len(m.get("content") or "")) >= 74_000]
    assert big_read and len(big_read[0]["content"]) <= _READ_MAX_CONTENT + 1
    mid = big_read[0]["id"]
    scroll = json.loads(session_search(session_id="s_big", around_message_id=mid, window=1, db=db))
    assert scroll["mode"] == "scroll"
    big = [m for m in scroll["messages"] if m["id"] == mid][0]
    assert len(big["content"]) == 74_000, "claim: scroll is uncapped"
