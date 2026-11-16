"""Batched background-process notices are runtime scaffolding, not the user's words.

"[IMPORTANT: N background processes completed..." starts with a count, so the singular
"[IMPORTANT: Background process " prefix missed it. Capsules then named the notice as
"User asked" and filled the verbatim user section with job output (186 capsules audited
2026-11-16: 8 named a notice as the ask, 88 quoted envelopes as user words).
"""
from agent.context_compressor import ContextCompressor, _build_verbatim_user_section
from agent.conversation_compression import _is_real_user_message

REAL = "fix keyring issues permanently and stop other agents breaking it"
NOTICES = [
    "[IMPORTANT: 4 background processes completed. Treat these results as one batch.]\n\n[IMPORTANT: Background process proc_1 completed normally (exit code 0).",
    "[IMPORTANT: 2 background processes completed for this session.\nproc_a: exit 0",
    "[IMPORTANT: 2 background process results arrived while this session was busy. Treat them as one batch.]",
    "[ASYNC DELEGATION BATCH COMPLETE \u2014 deleg_0a3866e3]\nA background fan-out unit you dispatched finished.",
    "[ASYNC DELEGATION TASK FAILED \u2014 deleg_8ca64224, task 1/3]\nOne subagent in a background fan-out failed.",
]


def test_batch_notice_is_not_a_real_user_message():
    for n in NOTICES:
        assert not _is_real_user_message({"role": "user", "content": n})
    assert _is_real_user_message({"role": "user", "content": REAL})


def test_user_asked_snapshot_names_the_person_not_the_notice():
    msgs = [{"role": "user", "content": REAL}, {"role": "assistant", "content": "ok"}]
    for n in NOTICES:
        msgs += [{"role": "user", "content": n}, {"role": "assistant", "content": "noted"}]
    snap = ContextCompressor._latest_user_task_snapshot(msgs)
    assert snap and "keyring" in snap and "background processes" not in snap


def test_verbatim_section_drops_batch_notices():
    msgs = [{"role": "user", "content": REAL}, {"role": "assistant", "content": "ok"}]
    for n in NOTICES:
        msgs += [{"role": "user", "content": n}, {"role": "assistant", "content": "noted"}]
    section = _build_verbatim_user_section(msgs)
    assert REAL in section and "background processes" not in section
