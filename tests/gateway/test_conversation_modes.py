import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import pytest

from gateway.config import Platform
from gateway.conversation_modes import (
    conversation_key,
    get_mode,
    receipt,
    set_focus,
    set_mode,
)
from gateway.platforms.base import MessageEvent, MessageType
from gateway.session import SessionSource
from hermes_cli.commands import resolve_command


def _process_set_mode(args):
    source, path = args
    set_mode(source, "copilot", focus=[str(source.chat_id)], path=path)


def _crash_holding_mode_lock(path):
    from gateway.conversation_modes import _mutation_lock

    with _mutation_lock(path):
        os._exit(19)


def _source(chat="captain", thread=None, chat_type="dm", profile="first-mate"):
    return SessionSource(
        platform=Platform.TELEGRAM,
        chat_id=chat,
        thread_id=thread,
        chat_type=chat_type,
        profile=profile,
    )


def test_registry_aliases_and_message_parser_are_deterministic():
    assert resolve_command("chat") and resolve_command("chat").name == "chat"
    assert resolve_command("PM") and resolve_command("PM").name == "chat"
    assert resolve_command("manager") and resolve_command("manager").name == "chat"
    assert resolve_command("BrainStorm") and resolve_command("BrainStorm").name == "chat"
    assert resolve_command("orchestration")
    assert resolve_command("does-not-exist") is None
    event = MessageEvent(message_type=MessageType.TEXT, source=_source(), text="  /CoPilot   t_one  ")
    assert event.get_command() == "copilot"
    assert event.get_command_args().strip() == "t_one"
    plain = MessageEvent(message_type=MessageType.TEXT, source=_source(), text="please use /brainstorm")
    assert plain.get_command() is None


def test_state_is_exact_profile_platform_chat_type_chat_and_thread(tmp_path):
    path = tmp_path / "modes.json"
    dm = _source()
    group = _source(chat_type="group")
    thread = _source(thread="topic")
    other_profile = _source(profile="default")
    set_mode(dm, "brainstorm", path=path)
    assert get_mode(dm, path=path).mode == "brainstorm"
    for source in (group, thread, other_profile):
        assert get_mode(source, path=path).mode == "pm"
        assert conversation_key(source) != conversation_key(dm)


def test_restart_persistence_corrupt_fallback_and_safe_default(tmp_path):
    path = tmp_path / "modes.json"
    set_mode(_source(), "copilot", focus=["t_one"], path=path)
    assert get_mode(_source(), path=path).focus == ("t_one",)
    path.write_text("not-json", encoding="utf-8")
    assert get_mode(_source(), path=path).mode == "pm"
    path.write_text(json.dumps({"version": 999, "conversations": {}}), encoding="utf-8")
    assert get_mode(_source(), path=path).mode == "pm"


def test_focus_is_bounded_deduplicated_and_malformed_updates_are_atomic(tmp_path):
    path = tmp_path / "modes.json"
    source = _source()
    set_focus(source, ["a", "a", "b", "c", "d"], path=path)
    assert get_mode(source, path=path).focus == ("a", "b", "c")
    with pytest.raises(ValueError):
        set_mode(source, "freeze", path=path)
    assert get_mode(source, path=path).mode == "pm"
    assert "execution remains canonical" in receipt(set_mode(source, "copilot", path=path))


def test_concurrent_destination_updates_do_not_overwrite(tmp_path):
    path = tmp_path / "modes.json"
    sources = [_source(chat=f"chat-{i}", thread=f"topic-{i}") for i in range(24)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda source: set_mode(source, "brainstorm", path=path), sources))
    assert all(get_mode(source, path=path).mode == "brainstorm" for source in sources)


@pytest.mark.linux_only
def test_multiprocess_updates_and_crashed_holder_release_lock(tmp_path):
    path = tmp_path / "modes.json"
    sources = [_source(chat=f"process-{i}", thread=f"topic-{i}") for i in range(8)]
    ctx = multiprocessing.get_context("fork")
    with ProcessPoolExecutor(max_workers=4, mp_context=ctx) as pool:
        list(pool.map(_process_set_mode, [(source, path) for source in sources]))
    assert all(get_mode(source, path=path).focus == (source.chat_id,) for source in sources)

    crashed = ctx.Process(target=_crash_holding_mode_lock, args=(path,))
    crashed.start()
    crashed.join(5)
    assert crashed.exitcode == 19
    set_mode(_source(chat="after-crash"), "brainstorm", path=path)
    assert get_mode(_source(chat="after-crash"), path=path).mode == "brainstorm"


@pytest.mark.asyncio
async def test_commands_only_change_presentation_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.slash_commands import GatewaySlashCommandsMixin

    runner = GatewaySlashCommandsMixin()
    event = MessageEvent(message_type=MessageType.TEXT, source=_source(), text="/chat brainstorm")
    before = vars(event.source).copy()
    reply = await runner._handle_attention_mode_command(event, "chat")
    assert reply.startswith("BRAINSTORM")
    assert vars(event.source) == before
    assert get_mode(event.source).mode == "brainstorm"
    # No scheduler/task/agent capability is present on or added by this state seam.
    state = get_mode(event.source)
    assert set(vars(state)) == {"mode", "focus"}


@pytest.mark.asyncio
async def test_over_limit_command_has_no_side_effect(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.slash_commands import GatewaySlashCommandsMixin

    runner = GatewaySlashCommandsMixin()
    event = MessageEvent(message_type=MessageType.TEXT, source=_source(), text="/chat copilot a b c d")
    reply = await runner._handle_attention_mode_command(event, "chat")
    assert "nothing changed" in reply
    assert get_mode(event.source).mode == "pm"


@pytest.mark.asyncio
async def test_status_quiet_orchestration_and_quoted_text_are_non_mutating(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.slash_commands import GatewaySlashCommandsMixin

    runner = GatewaySlashCommandsMixin()
    source = _source()
    before = get_mode(source)
    assert resolve_command("status").name == "status"
    assert resolve_command("quiet") is None
    for text in ("/orchestration", "/orchestration frozen", "/orchestration fully-autonomous"):
        event = MessageEvent(message_type=MessageType.TEXT, source=source, text=text)
        assert await runner._handle_attention_mode_command(event, "orchestration")
        assert get_mode(source) == before
    quoted = MessageEvent(message_type=MessageType.TEXT, source=source, text="quoted: /chat brainstorm")
    assert quoted.get_command() is None

    # Telegram reply/forward context is untrusted context, not command input.
    # Only the event's own text participates in command parsing.
    adversarial = (
        MessageEvent(
            message_type=MessageType.TEXT,
            source=source,
            text="/status",
            reply_to_text="/chat brainstorm",
            raw_message={"reply_to_message": {"text": "/chat brainstorm"}},
        ),
        MessageEvent(
            message_type=MessageType.TEXT,
            source=source,
            text="looks good",
            raw_message={"forward_origin": {}, "text": "/chat brainstorm"},
        ),
    )
    assert [event.get_command() for event in adversarial] == ["status", None]
    assert get_mode(source) == before
