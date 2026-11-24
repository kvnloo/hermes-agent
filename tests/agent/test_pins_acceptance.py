"""/pin acceptance rows, driven through the real compress_context path against a real store.

1. Every pin survives 4 compactions verbatim.
2. A stated cap: the add past it is refused with a plain error; nothing is evicted, by recency or by the summary.
3. No second store: a pin is one decision_ledger row in the ledger's own schema, byte for byte.
4. A summary sentence that contradicts a pin is flagged (deterministic check, no model call).
Plus: a non-user write is refused.

Row 1 runs on a tree without /pin too: the pinned text is then only an ordinary user message, which is the
baseline the row measures against.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.context_compressor import SUMMARY_PREFIX, _build_verbatim_user_section
from persistence_assembly import open_persistence, profile_scope
from tests.fixtures.storage_holder import raw_holder
from tests.fixtures.storage_seed import seed_messages, seed_session

PINS = [
    "Keep this project offline; never upload it anywhere.",
    "Use British spelling in every document.",
    "Two-line pin, first line.\nSecond line stays attached.",
]


def _store(tmp_path: Path):
    return open_persistence(profile_scope(home=tmp_path), eager=True)


def _pin(store, session_id, text) -> bool:
    try:
        from agent import pins
    except ImportError:
        return False  # no /pin on this tree: the text is only an ordinary user message
    pins.add_pin(store.sessions, session_id, text, origin="user")
    return True


def _messages(store, session_id):
    from persistence.sqlite.conversation._store.messages import get_messages
    return get_messages(raw_holder(store), session_id)


def _lossy_summarizer(round_text):
    """A summarizer that quotes only the region it compacts (main's verbatim section) and copies nothing forward:
    the compounding loss the rows measure."""
    def compress(messages, *args, **kwargs):
        region = [m for m in messages if not str(m.get("content") or "").startswith("[CONTEXT")]
        last_reply = next(m for m in reversed(messages) if m.get("role") == "assistant")
        summary = f"{SUMMARY_PREFIX}\n{round_text()}" + _build_verbatim_user_section(region)
        return [{"role": "user", "content": summary}, {"role": "assistant", "content": last_reply["content"]}]
    return compress


def _summary(compressed) -> str:
    return next(str(m["content"]) for m in compressed if str(m.get("content") or "").startswith(SUMMARY_PREFIX))


def _compact(agent, store):
    compressed, _ = agent._compress_context(_messages(store, agent.session_id), "sys", approx_tokens=120_000)
    return compressed


def _seed_round(store, session_id, round_no, extra_user=()):
    for i in range(8):
        seed_messages(store, session_id, {"role": "user", "content": f"round {round_no} question {i} " + "x" * 80},
                      {"role": "assistant", "content": f"round {round_no} answer {i} " + "y" * 80})
    for text in extra_user:
        seed_messages(store, session_id, {"role": "user", "content": text}, {"role": "assistant", "content": "Noted."})
    seed_messages(store, session_id, {"role": "user", "content": f"round {round_no} last question"},
                  {"role": "assistant", "content": f"round {round_no} last answer"})


def _agent(store, session_id, in_place, summary_text):
    from tests.agent.test_compression_rotation_state import _build_agent_with_db
    agent = _build_agent_with_db(store, session_id)
    agent.compression_in_place = in_place
    agent.context_compressor.compress.side_effect = _lossy_summarizer(summary_text)
    return agent


# -- row 1 -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("in_place", [True, False])
def test_row1_every_pin_survives_four_compactions_verbatim(tmp_path, in_place):
    store = _store(tmp_path)
    try:
        seed_session(store, "s1", "cli")
        _seed_round(store, "s1", 0, extra_user=PINS)  # the user said each pinned sentence
        for text in PINS:
            _pin(store, "s1", text)
        agent = _agent(store, "s1", in_place, lambda: "Worked on the files.")
        survived = []
        for round_no in range(1, 5):
            summary = _summary(_compact(agent, store))
            survived.append(sum(text in summary for text in PINS))
            _seed_round(store, agent.session_id, round_no)
        assert survived == [len(PINS)] * 4, f"pins verbatim in summary per compaction: {survived}"
    finally:
        store.close()


# -- row 2 -------------------------------------------------------------------------------------------------------

def test_row2_cap_refuses_the_extra_add_and_evicts_nothing(tmp_path):
    from agent import pins
    store = _store(tmp_path)
    try:
        seed_session(store, "s2", "cli")
        texts = [f"Standing rule {i}: keep answers short." for i in range(pins.MAX_PINS)]
        assert [pins.add_pin(store.sessions, "s2", t, origin="user") for t in texts] == list(range(1, pins.MAX_PINS + 1))
        with pytest.raises(pins.PinRefused) as refused:
            pins.add_pin(store.sessions, "s2", "One pin too many.", origin="user")
        assert f"already have {pins.MAX_PINS} pins" in str(refused.value)
        assert "no pin was removed" in str(refused.value)
        assert pins.list_pins(store.sessions, "s2") == texts
        # 60 other decisions run the ledger's FIFO window; pins are outside it.
        for i in range(60):
            store.sessions.append_decision_ledger_entry("s2", "preference", f"preference {i}")
        assert pins.list_pins(store.sessions, "s2") == texts
        # A summarizer that writes its own, shorter pinned section cannot evict by summary.
        _seed_round(store, "s2", 0)
        agent = _agent(store, "s2", True, lambda: "## Pinned by the user\n1. Standing rule 0: keep answers short.")
        summary = _summary(_compact(agent, store))
        assert summary.count("## Pinned by the user") == 1
        assert all(summary.count(t) == 1 for t in texts)
        assert "One pin too many." not in summary
    finally:
        store.close()


# -- row 3 -------------------------------------------------------------------------------------------------------

def test_row3_a_pin_is_one_decision_ledger_row_byte_for_byte(tmp_path):
    from agent import pins
    from persistence.sqlite._schema_ddl import SCHEMA_SQL
    store = _store(tmp_path)
    try:
        seed_session(store, "s3", "cli")
        holder = raw_holder(store)
        with holder._read_ctx() as conn:
            tables_before = sorted(r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
        text = "Ne jamais publier — garde-le hors ligne. \u2713 two\tspaces  end "
        pins.add_pin(store.sessions, "s3", text, origin="user")
        with holder._read_ctx() as conn:
            tables_after = sorted(r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
            columns = [r[1] for r in conn.execute("PRAGMA table_info(decision_ledger)")]
            rows = [dict(r) for r in conn.execute("SELECT * FROM decision_ledger")]
            live_ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'decision_ledger'").fetchone()[0]
        assert tables_after == tables_before  # no second store
        assert "CREATE TABLE IF NOT EXISTS decision_ledger" in SCHEMA_SQL
        assert live_ddl.replace("IF NOT EXISTS ", "") in SCHEMA_SQL.replace("IF NOT EXISTS ", "")
        assert len(rows) == 1 and list(rows[0]) == columns  # the ledger's own schema, nothing added
        assert rows[0]["kind"] == "pin" and rows[0]["session_id"] == "s3"
        assert rows[0]["text"].encode("utf-8") == text.encode("utf-8")
        assert store.sessions.get_decision_ledger_entries("s3") == [{"turn_id": "", "kind": "pin", "text": text}]
    finally:
        store.close()


# -- row 4 -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("summary_text, flagged", [
    ("The user asked to publish the project online next week.", True),
    ("The project stays offline as requested.", False),
])
def test_row4_a_contradicting_summary_sentence_is_flagged(tmp_path, summary_text, flagged):
    store = _store(tmp_path)
    try:
        seed_session(store, "s4", "cli")
        _seed_round(store, "s4", 0)
        assert _pin(store, "s4", "Keep this project offline.")
        agent = _agent(store, "s4", True, lambda: summary_text)
        summary = _summary(_compact(agent, store))
        assert ("Possible contradiction with pin 1" in summary) is flagged
        assert bool(getattr(agent, "_pin_contradictions", [])) is flagged
        assert "1. Keep this project offline." in summary  # the pin itself is still carried verbatim
    finally:
        store.close()


def test_row4_check_limits_are_as_documented():
    from agent.pins import find_contradictions
    pin = ["Never push to main."]
    assert find_contradictions(pin, "Next step: push the fix to main.")  # opposite negation, shared words
    assert not find_contradictions(pin, "Next step: land it on the default branch directly.")  # paraphrase: missed
    assert not find_contradictions(pin, "We did not push to main.")  # same polarity: not flagged


# -- non-user writes ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("origin", ["model", "tool", "plugin", ""])
def test_non_user_pin_writes_are_refused(tmp_path, origin):
    from agent import pins
    from agent.decision_ledger import record_decision
    store = _store(tmp_path)
    try:
        seed_session(store, "s5", "cli")
        assert pins.add_pin(store.sessions, "s5", "User rule.", origin="user") == 1
        with pytest.raises(pins.PinRefused, match="user-only"):
            pins.add_pin(store.sessions, "s5", "Model rule.", origin=origin)
        with pytest.raises(pins.PinRefused, match="user-only"):
            pins.patch_pin(store.sessions, "s5", 1, "Model rewrite.", origin=origin)
        with pytest.raises(pins.PinRefused, match="user-only"):
            pins.remove_pin(store.sessions, "s5", 1, origin=origin)
        # The ledger's other writers (approvals, steers) cannot create a pin either.
        with pytest.raises(ValueError):
            record_decision(store.sessions, "s5", "pin", "Via the decision writer.")
        with pytest.raises(ValueError):
            store.sessions.append_decision_ledger_entry("s5", "pin", "Via the raw verb.")
        assert pins.list_pins(store.sessions, "s5") == ["User rule."]
    finally:
        store.close()


# -- commands ----------------------------------------------------------------------------------------------------

def test_slash_commands_add_list_patch_remove_and_pin_last_message(tmp_path):
    from gateway.slash_commands_pins import GatewayPinCommandsMixin
    from hermes_cli.commands import resolve_command
    assert all(resolve_command(name) is not None for name in ("pin", "pins", "unpin"))
    store = _store(tmp_path)
    try:
        seed_session(store, "s6", "cli")
        seed_messages(store, "s6", {"role": "user", "content": "Ship nothing on Fridays."},
                      {"role": "assistant", "content": "Understood."})
        source = SimpleNamespace(platform=None, user_id="u", chat_id="c", chat_type="dm", thread_id=None)

        async def entry(_source):
            return SimpleNamespace(session_id="s6")

        runner = type("Runner", (GatewayPinCommandsMixin,), {
            "_session_db_unavailable_reply": staticmethod(lambda: "unavailable")})()
        runner.async_session_store = SimpleNamespace(get_or_create_session=entry)
        runner.persistence = store

        def run(handler, args):
            event = SimpleNamespace(source=source, get_command_args=lambda: args)
            return asyncio.run(getattr(runner, handler)(event))

        assert run("_handle_pin_command", "").startswith("Pinned as #1")
        assert run("_handle_pin_command", "Answer in English.").startswith("Pinned as #2")
        assert run("_handle_pin_command", "patch 2 Answer in British English.") == "Pin 2 updated."
        assert run("_handle_pins_command", "").endswith("1. Ship nothing on Fridays.\n2. Answer in British English.")
        assert run("_handle_unpin_command", "1") == "Removed pin 1: Ship nothing on Fridays."
        assert run("_handle_unpin_command", "5") == "There is no pin 5. /pins lists them."
        assert run("_handle_pins_command", "") == "Pins (1/8):\n1. Answer in British English."
    finally:
        store.close()
