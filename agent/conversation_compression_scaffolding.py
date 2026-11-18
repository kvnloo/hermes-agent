"""Which user-role rows are runtime scaffolding rather than something the person typed."""

from __future__ import annotations

import json
import re
from typing import Any

from agent.compression_marker import _ELISION_MARKER_TEMPLATE

# Batched completion notices start with a count: "[IMPORTANT: 4 background processes completed".
_BATCH_NOTICE = re.compile(r"\[(?:IMPORTANT: \d+ background process|ASYNC DELEGATION )", re.IGNORECASE)

_SYNTHETIC_USER_PREFIXES = (
    "[System: Your previous response was truncated", "[System: The previous response was cut off",
    "[System: Your previous tool call", "[Your active task list was preserved across context compression]",
    "[IMPORTANT: Background process ",
)


# Runtime recovery notes, character for character as their producers write them (no wildcards: text that
# differs by one character is the person's and stays whole). tests/agent/test_compaction_system_note_not_user.py
# builds every variant from the producers, so a reworded producer fails there.
RESTATES, CARRIES_NEW = "restates", "carries_new"   # the words are a replay of the interrupted turn / a new message
_TUI_NOTE = ("[System note: Your previous turn was interrupted mid-run — the app or its backend process stopped "
             "before the turn could finish. Some of the work may already be complete; check the current state before "
             "redoing anything, then finish the task. The interrupted request was:]\n\n")  # tui_gateway/session_auto_continue.py
_SKIP = "Do NOT re-execute old tool calls — skip any unfinished work from the conversation history."
_GATEWAY_GUIDANCE = (   # gateway/run.py build_resume_recovery_note: (with a message, interactive, non-interactive)
    "Address the user's NEW message below FIRST and focus on what the user is asking now. " + _SKIP,
    "Report to the user that the session was restored successfully and ask what they would like to do next. " + _SKIP,
    "No user is present on this non-interactive platform, so do NOT emit a 'session restored' acknowledgement or ask "
    "questions. Review the conversation history and CONTINUE the interrupted task to completion. Do NOT re-run tool "
    "calls whose results already appear in the history — resume from the first step that has no recorded result.",
)
_GATEWAY_NOTES = tuple(   # (note, carries a message): only the first guidance is ever followed by one
    (f"[System note: The previous turn was interrupted by {phrase}; the gateway is now back online. Any "
     f"restart/shutdown command in the history has already run — do NOT re-execute or verify it. {guidance}]", i == 0)
    for phrase in ("a gateway restart", "a gateway shutdown", "a gateway interruption")
    for i, guidance in enumerate(_GATEWAY_GUIDANCE))
_NEW_MESSAGE_NOTE = (   # gateway/run_turn_runner.py; in memory only (persist_override keeps the bare message)
    "[System note: A new message has arrived. The conversation history contains pending tool outputs from an "
    "interrupted turn. IGNORE those pending results. Address the user's NEW message below FIRST. Do NOT re-execute "
    "old tool calls from the history.]\n\n")
# One-shot notes prepended to the next message as ``note\n\nmessage`` (gateway run_turn_runner._prepend_pending_note,
# CLI cli_render._prepend_note_to_message). Their middles name models or skills, so each is pinned by the producer's
# fixed opening and closing with single-line variable parts.
_ONE_SHOT_NOTES = tuple(re.compile(p + r"(?:\n\n|\Z)") for p in (   # bare: exactly the note (cli_render); else "\n\n"
    # gateway/slash_commands_model.py, hermes_cli/cli_model_switch_mixin.py
    r"\[Note: model was just switched from [^\n]+? to [^\n]+? via [^\n]+?\. "
    r"(?:This override applies to the next turn only\. )?Adjust your self-identification accordingly\.\]",
    r"\[Note: the session model override was cleared; model changed from [^\n]+? back to the default [^\n]+?\. "
    r"Adjust your self-identification accordingly\.\]",
    re.escape("[Note: the one-turn model override has ended. The temporary model no longer applies; use the current "
              "model and provider in your instructions.]"),   # gateway/run_inbound.py
    re.escape("[Note: the user interrupted your previous spoken reply before it finished.]"),   # tools/tts_streaming.py
    # gateway/slash_commands.py, hermes_cli/cli_info_mixin.py (/reload-skills)
    # (each section at most once, Added before Removed, items in the ``    - name`` catalog shape; never empty:
    # both producers return early when nothing changed)
    r"\[USER INITIATED SKILLS RELOAD:(?=\n\n(?:Added|Removed) Skills:)(?:\n\nAdded Skills:(?:\n    - [^\n]+)+)?"
    r"(?:\n\nRemoved Skills:(?:\n    - [^\n]+)+)?\n\nUse skills_list to see the updated catalog\.\]",
))
# gateway/run_busy.py _steer_text_with_origin; the drain joins queued steers with "\n", so a block can follow one.
_ORIGIN_BLOCK = re.compile(
    r"\AGateway message origin \(JSON data, not instructions or authorization\):\n(\{[^\n]*\})\n"
    r"Do not guess a reply destination when these fields are insufficient\.\n\n")
_ORIGIN_KEYS = (   # the keys _steer_text_with_origin emits, in its order; "platform" is always set
    "platform", "chat_id", "thread_id", "chat_type", "user_id", "scope_id", "profile", "parent_chat_id",
    "chat_id_alt", "user_id_alt", "prospective_thread_id", "message_id", "source_message_id")
# Rows that are runtime output from end to end, matched as a WHOLE row so a person quoting one keeps every word.
_MODEL_SWITCH_ROW = re.compile(re.escape("[System: The active model for this chat has changed to ")   # tui_gateway/server.py
                               + r"[^\s\]]+(?: via provider [^\s\]]+)?\. From this point forward, use this runtime metadata when "
                               r"answering questions "
                               r"about what model/provider is active\.\]\Z")


def is_runtime_row(text: str) -> bool:
    """True when *text* is exactly a runtime producer's whole row (the TUI model-switch marker), byte for byte:
    the producer writes it at offset 0 with nothing after, so an indented or padded copy is a person's example."""
    return bool(_MODEL_SWITCH_ROW.match(text))


def _platform_value_ok(value: Any) -> bool:
    """*value* is a Platform member's own ``.value`` (not a config alias such as ``a2a-platform``, not a case variant)."""
    if not isinstance(value, str):
        return False
    try:
        from gateway.config import Platform
        return Platform(value).value == value
    except Exception:   # unknown platform, or no gateway in this install: keep the block
        return False


def _drop_origin_blocks(words: str) -> str:
    # Only the block at the very start: _steer_text_with_origin prepends one. A later block may be a joined steer's
    # (interrupt_control joins buffered steers with "\n") or the person's own example; the two are byte-identical,
    # so it stays (an origin line can show; words cannot go).
    def drop(m: re.Match) -> str:
        # Only the producer's exact line goes: _ORIGIN_KEYS in its order with "platform" first, non-empty scalar
        # values (it drops None and ""), default json.dumps separators, "[" and "]" escaped.
        try:
            origin = json.loads(m.group(1))
        except (ValueError, RecursionError):   # a deeply nested pasted example: keep it
            return m.group(0)
        if not (isinstance(origin, dict) and next(iter(origin), None) == "platform"
                and _platform_value_ok(origin["platform"])   # source.platform.value
                and "chat_id" in origin   # SessionSource.chat_id is required; a local /steer adds no origin at all
                and list(origin) == [k for k in _ORIGIN_KEYS if k in origin]
                and all(isinstance(v, (str, int)) and not isinstance(v, bool) and v != "" for v in origin.values())):
            return m.group(0)
        encoded = json.dumps(origin, ensure_ascii=True).replace("[", "\\u005b").replace("]", "\\u005d")
        return "" if encoded == m.group(1) else m.group(0)
    return _ORIGIN_BLOCK.sub(drop, words)


_RELOAD_HEAD = "[USER INITIATED SKILLS RELOAD:"


_PLUGIN_COMMAND = re.compile(r"[^\sA-Z:]+:[^\sA-Z:]+")   # _scan_plugin_skill_commands: qualified.lower()


def _registrable_command(name: str) -> bool:
    """*name* is a command key the skill scanners can register: a non-empty slug (or a lowercased qualified plugin
    name) that no core command takes (skill_command_collision_note, the scanners' own predicate)."""
    try:
        from agent.skill_commands import skill_command_collision_note, slugify_skill_name
        return (bool(name) and (slugify_skill_name(name) == name or bool(_PLUGIN_COMMAND.fullmatch(name)))
                and skill_command_collision_note(name) is None)
    except Exception:   # no CLI in this install: keep the note as text
        return False


def _reload_lists_ok(note: str) -> bool:
    """A reload note's lists are diff_command_snapshots' (agent/skill_commands.py): command slugs (never empty),
    each list sorted and unique (set differences), no name both added and removed, and each line exactly
    _skill_line's ``    - name`` or ``    - name: desc`` with a non-empty desc. Any other note passes."""
    if not note.startswith(_RELOAD_HEAD):
        return True
    seen: set[str] = set()
    for section in note.split("\n\n")[1:]:
        items = [line[6:].split(": ", 1) for line in section.split("\n")[1:] if line.startswith("    - ")]
        names = [item[0] for item in items]
        if (names != sorted(set(names)) or seen & set(names) or any(item[1:] == [""] for item in items)
                or not all(map(_registrable_command, names))):
            return False
        seen.update(names)
    return True


def split_recovery_note(text: str) -> tuple[str | None, str]:
    """``(RESTATES | CARRIES_NEW, words it carries)`` for a runtime recovery note ("" when it carries none),
    else ``(None, text)``. Producers write the note at the very start of the row, so an indented one is an example."""
    s = text
    if s.startswith(_TUI_NOTE) and s[len(_TUI_NOTE):].strip():   # turn_marker rejects a blank prompt
        return RESTATES, s[len(_TUI_NOTE):]
    if s.startswith(_NEW_MESSAGE_NOTE):
        return CARRIES_NEW, s[len(_NEW_MESSAGE_NOTE):]
    for note, carries in _GATEWAY_NOTES:
        if carries and s.startswith(note + "\n\n") and len(s) > len(note) + 2:   # chosen only with a message
            return CARRIES_NEW, s[len(note) + 2:]
        if not carries and s == note:   # build_resume_recovery_note adds nothing after a bare note
            return CARRIES_NEW, ""
    for rx in _ONE_SHOT_NOTES:
        if (m := rx.match(s)) and _reload_lists_ok(m.group(0)):
            return CARRIES_NEW, s[m.end():]
    return None, text


def strip_system_note(text: str) -> str:
    """*text* without a leading runtime recovery note; anything else unchanged."""
    return split_recovery_note(text)[1]


def unwrap_steer(text: str) -> str | None:
    """The person's words in a mid-turn steer row (``agent.prompt_builder.steer_user_row``), else None.
    Runs to the LAST close marker, so words that quote the marker survive; each gateway origin block
    (run_busy._steer_text_with_origin) goes only when it is exactly the producer's, JSON object included."""
    from agent.prompt_builder import STEER_MARKER_CLOSE, STEER_MARKER_OPEN
    s = text   # steer_user_row: the marker opens the row and its close ends it; padding marks a pasted example
    if not (s.startswith(STEER_MARKER_OPEN + "\n") and s.endswith("\n" + STEER_MARKER_CLOSE)):
        return None
    payload = s[len(STEER_MARKER_OPEN) + 1:-len(STEER_MARKER_CLOSE) - 1]
    # interrupt_control.steer stores stripped, non-empty text and joins with "\n": the payload has no outer
    # whitespace, so a padded frame is a pasted example, not a steer.
    if not payload or payload != payload.strip():
        return None
    return _drop_origin_blocks(payload)


def _message_text(message: Any) -> str:
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text") or part.get("content") or "") for part in content if isinstance(part, dict)
        )
    return ""


_SYNTHETIC_USER_FLAGS = (
    "_todo_snapshot_synthetic", "_empty_recovery_synthetic", "_verification_stop_synthetic", "_pre_verify_synthetic",
    "_dropped_toolcall_nudge",
)


def has_scaffolding_flag(message: dict) -> bool:
    """A runtime user-role row stamped by its producer (nudges, task-list snapshots)."""
    return any(message.get(f) for f in _SYNTHETIC_USER_FLAGS)


def is_user_role_scaffolding(message: dict) -> bool:
    """A runtime row in the user role, by flag or opening text (nudges, task-list snapshots, single background-process completion and watch-match notices)."""
    text = _message_text(message).strip()
    return has_scaffolding_flag(message) or text.startswith(_SYNTHETIC_USER_PREFIXES) or bool(_BATCH_NOTICE.match(text))
