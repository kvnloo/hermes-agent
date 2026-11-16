"""Mid-turn compaction must keep the reply the user just read (#144546).

The user reads a reply, answers it ("Go ahead and do it."), and the agent starts a long
tool loop. Compaction fires inside that loop. The active turn is over the tail ceiling,
so ``_ensure_last_assistant_message_in_tail`` yields (#131412), and the reply and the
request both fold into the summary while the current tool chain stays. The reply's only
slot is next to the first kept tool-call row, so the reply anchor skips it, and the
restated request is left pointing at text that is no longer in context.
"""

import itertools
import json
import os
from unittest.mock import patch

import pytest

REPLY = "Plan: I will migrate the three cron jobs to the new queue, keeping job ids stable. " * 4
ASK = "Go ahead and do it."
POINTER = f'[Replying to your previous message: "{REPLY.strip()}"]'


def _tool_round(i):
    call_id = f"call_{i}"
    args = json.dumps({"path": f"f{i}.py", "content": "w" * 4000})
    return [
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": "write_file", "arguments": args}},
        ]},
        {"role": "tool", "tool_call_id": call_id, "content": f"wrote f{i}.py"},
    ]


@pytest.fixture
def agent(tmp_path):
    from agent.context_compressor import ContextCompressor
    from hermes_state import SessionDB

    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("S144546", source="cli")
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
        from run_agent import AIAgent

        agent = AIAgent(
            api_key="test-key", base_url="https://openrouter.ai/api/v1", model="test/model",
            platform="cli", quiet_mode=True, session_db=db, session_id="S144546",
            skip_context_files=True, skip_memory=True,
        )
    # protect_first_n=0: the head a session has after its first compactions (#147853).
    agent.context_compressor = ContextCompressor(
        model="test/model", config_context_length=128_000, quiet_mode=True, protect_first_n=0,
    )
    for i in range(8):
        db.append_message("S144546", "user", f"early question {i} " + "q" * 400)
        db.append_message("S144546", "assistant", f"early answer {i} " + "a" * 400)
    db.append_message("S144546", "user", "What is your plan for the cron jobs?")
    db.append_message("S144546", "assistant", REPLY)
    return agent


def _messages(agent, rounds):
    messages = agent._session_db.get_messages_as_conversation("S144546", include_row_ids=True)
    messages.append({"role": "user", "content": ASK})
    agent._persist_user_message_idx = len(messages) - 1
    for i in range(rounds):
        messages += _tool_round(i)
    return messages


def _compress(agent, messages):
    from agent.conversation_compression import CompressionCommitFence

    with patch.object(agent.context_compressor, "_generate_summary", return_value="Earlier work summarized."):
        out, _ = agent._compress_context(
            messages, "sys", approx_tokens=70_000, commit_fence=CompressionCommitFence(),
        )
    return out


def _text(message):
    content = message.get("content")
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


def _assert_shape(out):
    roles = [m.get("role") for m in out]
    assert not any(a == b == "assistant" for a, b in itertools.pairwise(roles)), roles
    for i, m in enumerate(out):
        if m.get("tool_calls"):
            assert out[i + 1].get("role") == "tool"


def test_folded_reply_is_quoted_on_the_restated_request(agent, caplog):
    messages = _messages(agent, rounds=24)
    with caplog.at_level("WARNING", logger="agent.conversation_compression_reply_anchor"):
        out = _compress(agent, messages)

    assert len(out) < len(messages)
    _assert_shape(out)
    carriers = [m for m in out if REPLY.strip() in _text(m)]
    assert len(carriers) == 1, "the reply the user just read is gone from the model's context"
    text = _text(carriers[0])
    # Chronology: the quote sits on the restated request, before the request's own words.
    assert text.index(POINTER) < text.rindex(ASK)
    assert not [r for r in caplog.records if "not reinserting" in r.getMessage()]


def test_second_compaction_does_not_stack_the_quote(agent):
    out = _compress(agent, _messages(agent, rounds=24))
    out += [row for i in range(24, 48) for row in _tool_round(i)]

    again = _compress(agent, out)

    assert sum(_text(m).count(POINTER) for m in again) == 1
    _assert_shape(again)


def test_request_with_its_own_quote_gets_no_second_one(agent):
    """A gateway reply already quotes the message it answers; never stack another quote."""
    messages = _messages(agent, rounds=24)
    own = '[Replying to: "an older cron report"]\n\n' + ASK
    messages[agent._persist_user_message_idx]["content"] = own

    out = _compress(agent, messages)

    assert any(own in _text(m) for m in out)
    assert not any(POINTER in _text(m) for m in out)


def test_reply_kept_in_the_head_is_not_quoted(agent):
    """#100818's layout: reply and request sit in the protected head, so the request is
    restated past the summary while the reply is still there verbatim."""
    agent.context_compressor.protect_first_n = 3
    rows = [
        {"role": "user", "content": "What is your plan for the cron jobs?"},
        {"role": "assistant", "content": REPLY},
        {"role": "user", "content": ASK},
    ]
    agent._persist_user_message_idx = 2
    out = _compress(agent, rows + [row for i in range(24) for row in _tool_round(i)])

    assert any(_text(m).strip() == REPLY.strip() for m in out)
    assert not any(POINTER in _text(m) for m in out)
