"""Runtime recovery notes are scaffolding; the person's words, including words that only look like a note, survive.

The TUI auto-continue note wraps the interrupted request and the gateway resume note prepends itself to the
next message (or stands alone). "[System note:" was no scaffolding prefix, so handoff capsules quoted whole
notes as the owner's verbatim words (2026-11-18 capsule: two copies under "User Messages (verbatim)").
Fixtures come from the real producers so a template change that the matcher misses fails here.
"""
import pytest

from agent.context_compressor import ContextCompressor, _build_verbatim_user_section
from gateway.run import build_resume_recovery_note
from tui_gateway import server  # split modules run rebound to server.py's globals (method_ctx.bind_module)

# Published onto server at import time: invisible to the type checker, so attribute access would not check.
_auto_continue_note = getattr(server, "_auto_continue_note")  # noqa: B009

REAL = "what would matt pocock & teknium & lauren tan say"
LATER = "check session history"
GATEWAY_NOTES = [
    build_resume_recovery_note(reason, "", interactive=interactive)
    for reason in ("restart_timeout", "shutdown_timeout", None) for interactive in (True, False)
]


def _turns(*users):
    out = []
    for u in users:
        out += [{"role": "user", "content": u}, {"role": "assistant", "content": "ok"}]
    return out


def test_tui_note_is_quoted_as_the_request_it_carries_and_never_merged():
    # Equal text is no proof of one turn: a crash can replay a repeated request, so every copy stays.
    section = _build_verbatim_user_section(_turns(REAL, _auto_continue_note(REAL), LATER))
    assert "System note" not in section
    assert section.count(REAL) == 2 and LATER in section


def test_tui_note_that_is_the_only_copy_keeps_the_request():
    section = _build_verbatim_user_section(_turns(_auto_continue_note(REAL)))
    assert "System note" not in section and REAL in section


@pytest.mark.parametrize("note", GATEWAY_NOTES)
def test_gateway_note_alone_is_dropped_and_prefixed_text_kept(note):
    assert "System note" not in _build_verbatim_user_section(_turns(LATER, note))
    for reason in ("restart_timeout", "shutdown_timeout", None):
        section = _build_verbatim_user_section(_turns(build_resume_recovery_note(reason, LATER)))
        assert "System note" not in section and LATER in section


def test_new_message_note_keeps_the_new_message():
    import ast, inspect
    from gateway import run_turn_runner
    src = inspect.getsource(run_turn_runner)   # the producer's literal, so a reworded note fails here
    start = src.index('"[System note: A new message has arrived.')
    note = "".join(ast.literal_eval(part.strip()) for part in src[start:src.index('+ ctx.message', start)].split("\n") if part.strip())
    section = _build_verbatim_user_section(_turns(note + LATER))
    assert "System note" not in section and LATER in section


def test_tui_note_payload_is_kept_even_when_it_opens_like_a_runtime_notice():
    # A recovered payload is what the person sent; when unsure, keep it.
    payload = "[IMPORTANT: Background process is my heading] keep #71302"
    row = _auto_continue_note(payload)
    section = _build_verbatim_user_section(_turns(LATER, row))
    assert "System note" not in section and "#71302" in section and LATER in section
    assert "#71302" in (ContextCompressor._latest_user_task_snapshot(_turns(row)) or "")
    assert "#71302" in "\n".join(_compressor()._fallback_anchors([{"role": "user", "content": row}])["user_asks"])


_LSP_HEADER_SOURCE = ('f"LSP diagnostics introduced by your earlier edit of {abs_path} "',
                      '"(the language server answered after that tool result returned):\\n"')


def _lsp_row(*paths):
    """The real late-LSP row: turn_stop_gates over blocks built by the real reporter."""
    from unittest.mock import patch
    from agent import turn_stop_gates
    from tools import file_operations_lint
    assert _source_has("tools.file_operations_lint", *_LSP_HEADER_SOURCE)
    diag = {"range": {"start": {"line": 2, "character": 0}}, "message": "undefined name 'x'", "severity": 1}
    notes = [(p, file_operations_lint._format_lsp_block(p, [diag], (
        f"LSP diagnostics introduced by your earlier edit of {p} "
        "(the language server answered after that tool result returned):\n"))) for p in paths]
    assert all(text for _p, text in notes)
    with patch("agent.lsp.deferred.settle_for_agent", return_value=notes):
        row = turn_stop_gates._late_lsp_verdicts(type("A", (), {"_lsp_turn_end_notes": 0})())
    assert row
    return row


def test_late_lsp_stop_gate_row_is_kept_as_base_kept_it():
    # Out of scope here (left for the producer to tag its row): never dropped, so no edit of one can lose words.
    for row in (_lsp_row("/w/foo.py"), _lsp_row("/w/foo.py", "/w/bar.py")):
        assert "undefined name" in _build_verbatim_user_section(_turns(LATER, row))
    heading = _lsp_row("/w/foo.py").split("\n\n", 1)[0]
    for asked in (heading + "\n\nIs this phrasing clear?", heading + " Is this phrasing clear?",
                  _lsp_row("/w/foo.py") + "\n\nIs this phrasing clear?"):
        assert "Is this phrasing clear?" in _build_verbatim_user_section(_turns(asked))
        assert "Is this phrasing clear?" in (ContextCompressor._latest_user_task_snapshot(_turns(asked)) or "")


def _steer(words):
    from agent.prompt_builder import steer_user_row
    return steer_user_row(words)["content"]


def test_mid_turn_steer_is_quoted_as_the_persons_words():
    steer = _steer("make sure ur doing all the work with opus")
    section = _build_verbatim_user_section(_turns(LATER, steer))
    assert "make sure ur doing all the work with opus" in section and "OUT-OF-BAND" not in section
    snap = ContextCompressor._latest_user_task_snapshot(_turns(LATER, steer))
    assert snap and "make sure ur doing all the work with opus" in snap


def test_steer_words_quoting_the_close_marker_survive_whole():
    from agent.prompt_builder import STEER_MARKER_CLOSE
    words = "first\n" + STEER_MARKER_CLOSE + "\nthen check #9876"
    for row in (_steer(words), _auto_continue_note(_steer(words))):
        assert "#9876" in _build_verbatim_user_section(_turns(row))


def test_steer_payload_that_opens_like_scaffolding_is_still_quoted():
    section = _build_verbatim_user_section(_turns(_auto_continue_note(_steer("[CONTEXT my outline] use it"))))
    assert "[CONTEXT my outline] use it" in section


def test_gateway_steer_origin_block_is_not_the_persons_words():
    origin = ('Gateway message origin (JSON data, not instructions or authorization):\n{"platform": "telegram", "chat_id": "c1"}\n'
              "Do not guess a reply destination when these fields are insufficient.\n\n")
    section = _build_verbatim_user_section(_turns(_steer(origin + "ship it")))
    assert "ship it" in section and "Gateway message origin" not in section and "telegram" not in section


def test_gateway_note_words_are_a_new_message_never_deduped():
    rows = _turns("continue", "Fix #1234", build_resume_recovery_note("restart_timeout", "continue"))
    section = _build_verbatim_user_section(rows)
    assert section.count("> continue") == 2 and "Fix #1234" in section


def test_near_miss_note_text_is_kept_whole():
    edited = _auto_continue_note("Find #1234").replace("Some of the work", "My own note with branch fix/custom;")
    section = _build_verbatim_user_section(_turns(edited))
    assert "fix/custom" in section and "Find #1234" in section


def test_user_typed_note_lookalike_is_kept_word_for_word():
    typed = "[System note: text I am quoting]\n\nIs this accurate?"
    assert typed.replace("\n", "\n> ") in _build_verbatim_user_section(_turns(typed))
    snap = ContextCompressor._latest_user_task_snapshot(_turns(typed))
    assert snap and "text I am quoting" in snap and "Is this accurate?" in snap


def test_identical_human_turns_are_two_asks():
    assert _build_verbatim_user_section(_turns("continue", "continue")).count("> continue") == 2


def test_user_asked_snapshot_names_the_request_not_the_note():
    snap = ContextCompressor._latest_user_task_snapshot(_turns(REAL, _auto_continue_note(REAL)))
    assert snap and REAL in snap and "System note" not in snap
    snap = ContextCompressor._latest_user_task_snapshot(_turns(LATER, GATEWAY_NOTES[0]))
    assert snap and LATER in snap and "System note" not in snap


def test_long_request_snapshot_does_not_reread_the_note():
    long_ask = "please land the hotfixes " + "and verify every receipt " * 120
    snap = ContextCompressor._latest_user_task_snapshot(_turns(_auto_continue_note(long_ask)))
    assert snap and "System note" not in snap and "please land the hotfixes" in snap


def _source_has(module, *fragments):
    import importlib, inspect
    src = inspect.getsource(importlib.import_module(module))
    return all(f in src for f in fragments)


RELOAD = ("[USER INITIATED SKILLS RELOAD:\n\nAdded Skills:\n    - foo: does foo\n\nRemoved Skills:\n    - bar\n\n"
          "Use skills_list to see the updated catalog.]")
MODEL_NOTES = [
    "[Note: model was just switched from Claude Opus 5.5 to gpt-oss-120b via Groq. Adjust your self-identification accordingly.]",
    "[Note: model was just switched from A to B via X. This override applies to the next turn only. "
    "Adjust your self-identification accordingly.]",
    "[Note: the session model override was cleared; model changed from B back to the default A. "
    "Adjust your self-identification accordingly.]",
    "[Note: the one-turn model override has ended. The temporary model no longer applies; use the current model and "
    "provider in your instructions.]",
]
_NEW_MESSAGE = ("[System note: A new message has arrived. The conversation history contains pending tool outputs from an "
                "interrupted turn. IGNORE those pending results. Address the user's NEW message below FIRST. Do NOT "
                "re-execute old tool calls from the history.]\n\n")


def test_one_shot_note_fixtures_match_their_producers():
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE
    assert SPEECH_INTERRUPTED_NOTE == "[Note: the user interrupted your previous spoken reply before it finished.]"
    for mod in ("gateway.slash_commands", "hermes_cli.cli_info_mixin"):
        assert _source_has(mod, '"[USER INITIATED SKILLS RELOAD:"', '"Added Skills:"', '"Removed Skills:"',
                           '"Use skills_list to see the updated catalog.]"')
    for mod in ("gateway.slash_commands_model", "hermes_cli.cli_model_switch_mixin"):
        assert _source_has(mod, '"[Note: model was just switched from ', "This override applies to the next turn only. ",
                           'Adjust your self-identification accordingly.]"')
    assert _source_has("gateway.slash_commands_model", '"[Note: the session model override was cleared; model changed from "',
                       ' back to the default "')
    assert _source_has("gateway.run_inbound", '"[Note: the one-turn model override has ended. The temporary model "',
                       '"no longer applies; use the current model and provider in your instructions.]"')


def test_stacked_gateway_one_shot_notes_peel_down_to_the_message():
    # run_turn_runner's order: model note, then the new-message note, then /reload-skills, via its own prepend.
    from types import SimpleNamespace
    from typing import Any, cast
    from gateway.run_turn_runner import TurnRunner
    for model_note in MODEL_NOTES:
        ctx = SimpleNamespace(session_key="s", message=LATER)
        fake = cast(Any, SimpleNamespace(_ctx=ctx, _runner=SimpleNamespace(
            _pending_model_notes={"s": model_note}, _pending_skills_reload_notes={"s": RELOAD})))
        TurnRunner._prepend_pending_note(fake, "_pending_model_notes")
        ctx.message = _NEW_MESSAGE + ctx.message
        TurnRunner._prepend_pending_note(fake, "_pending_skills_reload_notes")
        section = _build_verbatim_user_section(_turns(ctx.message))
        assert LATER in section
        assert "[Note:" not in section and "SKILLS RELOAD" not in section and "System note" not in section
        assert "[Note:" not in _build_verbatim_user_section(_turns(LATER, model_note))   # a note alone is no ask


def test_cli_speech_note_and_reload_note_peel():
    from hermes_cli.cli_render import _prepend_note_to_message
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE
    row = _prepend_note_to_message(_prepend_note_to_message(LATER, RELOAD), SPEECH_INTERRUPTED_NOTE)
    section = _build_verbatim_user_section(_turns(row))
    assert LATER in section and "[Note:" not in section and "SKILLS RELOAD" not in section


def test_recovered_request_that_opens_like_scaffolding_is_still_quoted():
    outline = "[CONTEXT my outline] use it"
    for row in (_auto_continue_note(outline), build_resume_recovery_note("restart_timeout", outline)):
        assert outline in _build_verbatim_user_section(_turns(row))


def test_reload_lookalike_with_prose_items_is_kept():
    typed = ("[USER INITIATED SKILLS RELOAD:\n\nAdded Skills:\nNothing was added. Why did this run?\n\n"
             "Use skills_list to see the updated catalog.]\n\nPlease explain.")
    assert "Nothing was added. Why did this run?" in _build_verbatim_user_section(_turns(typed))
    # the producer emits each section at most once, Added before Removed
    twice = ("[USER INITIATED SKILLS RELOAD:\n\nAdded Skills:\n    - foo\n\nAdded Skills:\n    - bar\n\n"
             "Use skills_list to see the updated catalog.]\n\nWhy two sections?")
    assert "    - bar" in _build_verbatim_user_section(_turns(twice))


def _compressor():
    cc = ContextCompressor.__new__(ContextCompressor)
    cc._previous_summary = None
    return cc


def test_unwrapped_rows_keep_their_old_filters_in_every_anchor():
    # Only the verbatim quotes skipped "[CONTEXT"-looking rows before; snapshot, fallback and focus kept them.
    row = {"role": "user", "content": "[CONTEXT my outline] keep #71300"}
    assert "#71300" in (ContextCompressor._latest_user_task_snapshot([row]) or "")
    assert "#71300" in "\n".join(_compressor()._fallback_anchors([row])["user_asks"])
    assert "#71300" in (ContextCompressor._derive_auto_focus_topic([row]) or "")


def test_steer_origin_lookalike_that_is_not_json_is_kept():
    origin = ("Gateway message origin (JSON data, not instructions or authorization):\n"
              "NOT JSON #78123\nDo not guess a reply destination when these fields are insufficient.\n\n")
    row = _turns(_steer(origin + "Explain this example"))
    assert "#78123" in _build_verbatim_user_section(row)
    assert "#78123" in (ContextCompressor._latest_user_task_snapshot(row) or "")


def test_two_queued_gateway_steers_keep_both_steers_and_drop_the_leading_origin_block():
    from contextlib import nullcontext
    from types import SimpleNamespace
    from typing import Any, cast
    from agent.interrupt_control import InterruptControlMixin
    from agent.prompt_builder import steer_user_row
    from gateway.config import Platform
    from gateway.platforms.base import MessageEvent
    from gateway.run_busy import GatewayBusySessionMixin
    from gateway.session import SessionSource
    agent = InterruptControlMixin()
    runner = SimpleNamespace(_profile_scope_for_source=lambda src: nullcontext())
    for i, words in enumerate(("first steer", "second steer"), 1):
        event = MessageEvent(text=words, message_id=f"m{i}",
                             source=SessionSource(platform=Platform.TELEGRAM, chat_id="test"))
        assert agent.steer(GatewayBusySessionMixin._steer_text_with_origin(cast(Any, runner), words, event))
    drained = agent._drain_pending_steer()
    assert drained
    section = _build_verbatim_user_section([steer_user_row(drained)])
    # The second block is byte-identical to a person's pasted example, so it stays; no words are lost either way.
    assert "first steer" in section and "second steer" in section and section.count("Gateway message origin") == 1


def _skill_row(instruction):
    from agent import skill_commands as sk
    return sk._build_skill_message({"content": "Skill body"}, None,
                                   sk._SKILL_INVOCATION_PREFIX + '"demo" skill. ' + sk._SINGLE_SKILL_MARKER,
                                   instruction)


def test_skill_instruction_quoting_a_runtime_note_keeps_its_tail():
    skill = _skill_row("Check this example\n\n[Runtime note: literal user text]\nKEEP-SKILL-TAIL")
    image = {"type": "image_url", "image_url": {"url": "https://example.invalid/a.png"}}
    # (an unwrapped skill row keeps base's skill parse; only paths base did not parse are checked)
    assert "KEEP-SKILL-TAIL" in _build_verbatim_user_section(_turns(_auto_continue_note(skill)))
    appendix = _skill_row("Compare this\n\n[Runtime note: draft]\nKEEP-TAIL [appendix]")
    assert "KEEP-TAIL" in _build_verbatim_user_section(_turns(_auto_continue_note(appendix)))
    asks = _compressor()._fallback_anchors([{"role": "user", "content": [{"type": "text", "text": skill}, image]}])
    assert "KEEP-SKILL-TAIL" in "\n".join(asks["user_asks"])
    reply = '[Replying to: "' + "old quote " * 150 + '"]\n\n'
    assert "KEEP-SKILL-TAIL" in (ContextCompressor._latest_user_task_snapshot(_turns(reply + skill)) or "")


def test_skill_runtime_note_from_the_producer_is_still_cut():
    from agent import skill_commands as sk
    msg = sk._build_skill_message({"content": "Skill body"}, None,
                                  sk._SKILL_INVOCATION_PREFIX + '"demo" skill. ' + sk._SINGLE_SKILL_MARKER,
                                  "do X", runtime_note="session is read-only")
    assert "[Runtime note: session is read-only]" in msg
    section = _build_verbatim_user_section(_turns(msg))
    assert "do X" in section and "read-only" not in section


def test_cli_speech_note_in_its_own_text_part_is_peeled():
    from hermes_cli.cli_render import _prepend_note_to_message
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE
    image = {"type": "image_url", "image_url": {"url": "https://example.invalid/a.png"}}
    row = {"role": "user", "content": _prepend_note_to_message([{"type": "text", "text": ""},
                                                               {"type": "text", "text": "inspect this"}, image],
                                                              SPEECH_INTERRUPTED_NOTE)}
    section = _build_verbatim_user_section([row])
    asks = "\n".join(_compressor()._fallback_anchors([row])["user_asks"])
    assert "inspect this" in section and "inspect this" in asks
    assert SPEECH_INTERRUPTED_NOTE not in section and SPEECH_INTERRUPTED_NOTE not in asks


def test_runtime_rows_never_become_the_snapshot_or_a_fallback_ask():
    marker = server._MODEL_SWITCH_MARKER_PREFIX + "demo via provider demo. From this point forward, use this runtime " \
        "metadata when answering questions about what model/provider is active.]"
    for runtime in (marker,):
        turns = _turns(LATER) + [{"role": "user", "content": runtime}]
        snap = ContextCompressor._latest_user_task_snapshot(turns)
        assert snap and LATER in snap and "language server" not in snap and "runtime metadata" not in snap
        assert _compressor()._fallback_anchors(turns)["user_asks"] == [LATER]
        static = _compressor()._build_static_fallback_summary(turns)
        assert LATER in static and "language server" not in static and "runtime metadata" not in static


def test_fallback_peels_a_recovery_note_from_a_multimodal_row():
    parts = [{"type": "text", "text": build_resume_recovery_note("restart_timeout", "inspect this")},
             {"type": "image_url", "image_url": {"url": "https://example.invalid/a.png"}}]
    asks = _compressor()._fallback_anchors([{"role": "user", "content": parts}])["user_asks"]
    assert asks and "inspect this" in asks[0] and "System note" not in asks[0]


def test_long_recovered_request_is_not_parsed_again_for_a_reply_pointer():
    # A peeled payload is final: a literal pointer the person typed is theirs (base kept it too).
    typed = '[Replying to: "KEEP-LITERAL"]\n\n' + "word " * 300
    for row in (_auto_continue_note(typed), build_resume_recovery_note("restart_timeout", typed)):
        snap = ContextCompressor._latest_user_task_snapshot(_turns(row)) or ""
        assert "KEEP-LITERAL" in snap and "System note" not in snap


def test_gateway_reply_on_an_unwrapped_skill_row_keeps_base_handling():
    from types import SimpleNamespace
    from typing import Any, cast
    from agent import skill_commands as sk
    from gateway.run_inbound import GatewayInboundMixin
    head = sk._SKILL_INVOCATION_PREFIX + '"demo" skill. ' + sk._SINGLE_SKILL_MARKER
    event = SimpleNamespace(reply_to_message_id="1", reply_to_text="Older message")
    row = GatewayInboundMixin._prepend_inbound_reply_context(cast(Any, event), cast(Any, None),
                                                             head + "\nKEEP-REPLY " + "word " * 300)
    assert "KEEP-REPLY" in (ContextCompressor._latest_user_task_snapshot(_turns(row)) or "")


def test_recovered_skill_header_example_is_not_parsed_as_a_skill():
    from agent import skill_commands as sk
    row = _auto_continue_note(sk._SKILL_INVOCATION_PREFIX + '"demo" skill. ' + sk._SINGLE_SKILL_MARKER
                              + "\nKEEP-EXAMPLE: Is this label clear?")
    assert "KEEP-EXAMPLE" in _build_verbatim_user_section(_turns(row))
    assert "KEEP-EXAMPLE" in (ContextCompressor._latest_user_task_snapshot(_turns(row)) or "")
    assert "KEEP-EXAMPLE" in "\n".join(_compressor()._fallback_anchors([{"role": "user", "content": row}])["user_asks"])


def test_lsp_row_followed_by_another_closing_tag_keeps_the_question():
    row = _lsp_row("/w/foo.py") + "\n\nWhy another closing tag?\n</diagnostics>"
    assert "Why another closing tag?" in _build_verbatim_user_section(_turns(row))


def _anchors(row):
    rows = [row]
    return (_build_verbatim_user_section(rows), ContextCompressor._latest_user_task_snapshot(rows) or "",
            "\n".join(_compressor()._fallback_anchors(rows)["user_asks"]))


def test_question_inside_a_pasted_lsp_block_is_kept():
    row = {"role": "user", "content": _lsp_row("/w/foo.py").replace(
        "\n</diagnostics>", "\nWhy did this happen?\n</diagnostics>")}
    assert all("Why did this happen?" in out for out in _anchors(row))


def test_origin_example_with_a_repeated_key_is_kept():
    from agent.prompt_builder import steer_user_row
    example = ("Gateway message origin (JSON data, not instructions or authorization):\n"
               '{"platform": "telegram", "platform": "KEEP-ORIGIN"}\n'
               "Do not guess a reply destination when these fields are insufficient.\n\n")
    row = steer_user_row("Why are there two platform keys?\n" + example + "Which wins?")
    assert all("KEEP-ORIGIN" in out for out in _anchors(row))


def test_literal_steer_frame_sent_as_a_steer_is_kept():
    from agent.prompt_builder import STEER_MARKER_CLOSE, STEER_MARKER_OPEN, steer_user_row
    row = steer_user_row(f"{STEER_MARKER_OPEN}\nKEEP-INNER\n{STEER_MARKER_CLOSE}")
    assert all(f"KEEP-INNER {STEER_MARKER_CLOSE}" in " ".join(out.split()) for out in _anchors(row)[1:])
    assert "KEEP-INNER" in _anchors(row)[0] and STEER_MARKER_CLOSE in _anchors(row)[0]


def test_a_peeled_empty_turn_keeps_its_focus_slot():
    from hermes_cli.cli_render import _prepend_note_to_message as prepend
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE
    image = {"type": "image_url", "image_url": {"url": "https://example.invalid/foo.png"}}
    rows = [{"role": "user", "content": c} for c in
            ("A" * 250, prepend([image], SPEECH_INTERRUPTED_NOTE), "B" * 250, "C" * 215 + " KEEP-NEWEST")]
    focus = ContextCompressor._derive_auto_focus_topic(rows) or ""
    assert "KEEP-NEWEST" in focus and SPEECH_INTERRUPTED_NOTE not in focus


def _late_lsp(path="/w/foo.py", n=1, message="bad indent") -> str:
    from unittest.mock import patch
    from agent import turn_stop_gates
    from tools.file_operations_lint import _format_lsp_block
    header = (f"LSP diagnostics introduced by your earlier edit of {path} "
              "(the language server answered after that tool result returned):\n")
    with patch("agent.lsp.deferred.settle_for_agent",
               return_value=[(path, _format_lsp_block(path, [{"message": message}] * n, header))]):
        row = turn_stop_gates._late_lsp_verdicts(type("A", (), {"_lsp_turn_end_notes": 0})())
    assert row
    return row


@pytest.mark.parametrize("diag,n", [
    ({"message": "a < b && c > d", "code": "E<1>", "source": "py&right"}, 1),
    ({"message": "tab\there ⟪x⟫ \"q\" &amp;", "range": {"start": {"line": 9, "character": 4}}}, 3),
    ({"message": "many"}, 60),                       # past MAX_PER_FILE: "... and N more"
    ({"message": "ünïcödé " * 40, "code": 7}, 30),   # capped mid-line
])
def test_every_real_lsp_row_shape_is_kept_verbatim(diag, n):
    from unittest.mock import patch
    from agent import turn_stop_gates
    from tools.file_operations_lint import _format_lsp_block
    paths = ("/w/a&b <c>.py", '/w/"q".py')
    notes = [(p, _format_lsp_block(p, [diag] * n, f"LSP diagnostics introduced by your earlier edit of {p} "
                                   "(the language server answered after that tool result returned):\n")) for p in paths]
    with patch("agent.lsp.deferred.settle_for_agent", return_value=notes):
        row = turn_stop_gates._late_lsp_verdicts(type("A", (), {"_lsp_turn_end_notes": 0})())
    assert row and all("language server" in out for out in _anchors({"role": "user", "content": row}))


def test_pasted_lsp_reports_the_late_producer_cannot_emit_are_kept():
    from agent.compression_marker import _elision_marker
    row = _late_lsp(message="Why KEEP-LSP?")
    block = row[row.index("LSP diagnostics introduced"):]
    head = block.removesuffix("\n</diagnostics>")
    for edited in (row.replace("ERROR [", "WARN ["),                               # severity the caller filters out
                   row.removesuffix(block) + head + _elision_marker(15, len(head) + 15),   # marker under the cap
                   row.removesuffix(block) + "KEEP-LSP" + _elision_marker(0, 8)):           # zero omitted
        assert all("KEEP-LSP" in out for out in _anchors({"role": "user", "content": edited}))


def test_origin_example_with_an_empty_value_is_kept():
    from agent.prompt_builder import steer_user_row
    example = ("Gateway message origin (JSON data, not instructions or authorization):\n"
               '{"platform": "telegram", "chat_id": "", "message_id": "KEEP-ORIGIN"}\n'
               "Do not guess a reply destination when these fields are insufficient.\n\n")
    row = steer_user_row("Is a blank chat ID allowed?\n" + example + "What should the gateway do?")
    assert all("KEEP-ORIGIN" in out for out in _anchors(row)[1:])


def test_fallback_keeps_a_later_distinct_request_when_requests_repeat():
    comp = _compressor()
    comp.tail_mode = "legacy"
    comp._previous_summary = ("Prior context. " * 200)[:2250]
    ask = {"role": "user", "content": "Repeat this request. " * 27}
    action = {"role": "assistant", "content": ("Here is what I changed. " * 50)[:300]}
    rows = [ask, action] * 3 + _turns("KEEP-REPEAT-TAIL", "final follow-up")
    assert "KEEP-REPEAT-TAIL" in comp._build_static_fallback_summary(rows)


def test_pasted_no_message_resume_note_with_a_question_is_kept():
    bare = build_resume_recovery_note("restart_timeout")
    row = {"role": "user", "content": bare + "\n\nIs this wording correct?"}
    assert all("ask what they would like to do next" in out for out in _anchors(row))


def test_lsp_blocks_report_for_file_cannot_shape_are_kept():
    from unittest.mock import patch
    from agent import turn_stop_gates
    from agent.lsp.reporter import report_for_file
    from tools.file_operations_lint import _format_lsp_block
    p = "/w/foo.py"
    header = (f"LSP diagnostics introduced by your earlier edit of {p} "
              "(the language server answered after that tool result returned):\n")
    diag = {"message": "KEEP-LSP " + "x" * 290}
    for block in (_format_lsp_block(p, [diag], header).replace("</diagnostics>", "... and 1 more\n</diagnostics>"),
                  header + report_for_file(p, [diag] * 14)):   # over MAX_TOTAL_CHARS without the elision
        with patch("agent.lsp.deferred.settle_for_agent", return_value=[(p, block)]):
            row = turn_stop_gates._late_lsp_verdicts(type("A", (), {"_lsp_turn_end_notes": 0})())
        assert row and all("KEEP-LSP" in out for out in _anchors({"role": "user", "content": row}))


def test_origin_example_with_a_numeric_platform_is_kept():
    from agent.prompt_builder import steer_user_row
    example = ("Gateway message origin (JSON data, not instructions or authorization):\n"
               '{"platform": 42, "message_id": "KEEP-ORIGIN"}\n'
               "Do not guess a reply destination when these fields are insufficient.\n\n")
    row = steer_user_row("Can platform be a number?\n" + example + "Which field is wrong?")
    assert all("KEEP-ORIGIN" in out for out in _anchors(row)[1:])


def test_one_request_under_two_different_notes_keeps_both_dropped_turns():
    from hermes_cli.cli_info_mixin import _skill_line
    from hermes_cli.cli_render import _prepend_note_to_message as prepend

    def reload_note(name):
        return ("[USER INITIATED SKILLS RELOAD:\n\nRemoved Skills:\n" + _skill_line({"name": name})
                + "\n\nUse skills_list to see the updated catalog.]")
    rows = _turns(prepend("KEEP-DISTINCT", reload_note("foo")), prepend("KEEP-DISTINCT", reload_note("bar")))
    dropped = _compressor()._build_static_fallback_summary(rows).split("## Last Dropped Turns\n", 1)[1]
    section = dropped.split("\n##", 1)[0]
    assert section.count("KEEP-DISTINCT") == 2 and "Removed Skills" not in section


def test_literal_tag_typed_into_a_pasted_lsp_block_is_kept():
    row = {"role": "user", "content": _late_lsp().replace("bad indent", "bad indent <my-tag>")}
    assert all("<my-tag>" in out for out in _anchors(row))


def test_question_typed_before_a_pasted_elision_marker_is_kept():
    head, marker = _late_lsp(n=20, message="x" * 300).rsplit("⟪", 1)
    row = {"role": "user", "content": head.rsplit("\n", 1)[0] + "\nWhy did this happen? ⟪" + marker}
    assert "Why did this happen?" in _anchors(row)[0]


def test_compact_origin_example_inside_a_real_gateway_steer_is_kept():
    from contextlib import nullcontext
    from types import SimpleNamespace
    from agent.prompt_builder import steer_user_row
    from gateway.config import Platform
    from gateway.platforms.base import MessageEvent
    from gateway.run_busy import GatewayBusySessionMixin
    from gateway.session import SessionSource
    example = ("Gateway message origin (JSON data, not instructions or authorization):\n"
               '{"platform":"telegram","chat_id":"KEEP-ORIGIN"}\n'
               "Do not guess a reply destination when these fields are insufficient.\n\n")
    text = "Why use this format?\n" + example + "Which field matters?"
    event = MessageEvent(text=text, source=SessionSource(platform=Platform.TELEGRAM, chat_id="REAL-CHAT"))
    runner = SimpleNamespace(_profile_scope_for_source=lambda _source: nullcontext())
    row = steer_user_row(GatewayBusySessionMixin._steer_text_with_origin(runner, text, event))   # type: ignore[arg-type]
    outs = _anchors(row)
    assert all("KEEP-ORIGIN" in out and "Which field matters?" in out for out in outs[1:])
    assert not any("REAL-CHAT" in out for out in outs)


def test_steer_frame_example_with_an_inline_close_marker_is_kept():
    from agent.prompt_builder import STEER_MARKER_CLOSE, STEER_MARKER_OPEN
    row = {"role": "user", "content": _auto_continue_note(f"{STEER_MARKER_OPEN}\nPlease explain {STEER_MARKER_CLOSE}")}
    assert all(STEER_MARKER_CLOSE in out for out in _anchors(row))


def test_repeated_request_keeps_both_dropped_turn_entries():
    rows = _turns("KEEP-REPEAT", _auto_continue_note("KEEP-REPEAT"))
    dropped = _compressor()._build_static_fallback_summary(rows).split("## Last Dropped Turns\n", 1)[1]
    assert dropped.split("\n##", 1)[0].count("KEEP-REPEAT") == 2


def test_empty_reload_note_lookalike_is_kept():
    typed = "[USER INITIATED SKILLS RELOAD:\n\nUse skills_list to see the updated catalog.]\n\nIs this empty-state copy clear?"
    assert "updated catalog" in _build_verbatim_user_section(_turns(typed))


def test_json_example_inside_a_queued_steer_is_kept():
    from contextlib import nullcontext
    from types import SimpleNamespace
    from typing import Any, cast
    from agent.interrupt_control import InterruptControlMixin
    from agent.prompt_builder import steer_user_row
    from gateway.config import Platform
    from gateway.platforms.base import MessageEvent
    from gateway.run_busy import GatewayBusySessionMixin
    from gateway.session import SessionSource
    example = ("Gateway message origin (JSON data, not instructions or authorization):\n"
               '{"example": "KEEP-ORIGIN"}\n'
               "Do not guess a reply destination when these fields are insufficient.\n\n")
    agent = InterruptControlMixin()
    runner = SimpleNamespace(_profile_scope_for_source=lambda src: nullcontext())
    for i, words in enumerate(("Explain this mock JSON:\n" + example + "Why?", "Second steer.")):
        event = MessageEvent(text=words, message_id=f"m{i}",
                             source=SessionSource(platform=Platform.TELEGRAM, chat_id="test"))
        assert agent.steer(GatewayBusySessionMixin._steer_text_with_origin(cast(Any, runner), words, event))
    drained = agent._drain_pending_steer()
    assert drained
    row = [steer_user_row(drained)]
    section = _build_verbatim_user_section(row)
    # The leading block goes; the example and the second steer's block (byte-shaped like an example) stay.
    assert "KEEP-ORIGIN" in section and "Second steer." in section and section.count("Gateway message origin") == 2
    assert "KEEP-ORIGIN" in (ContextCompressor._latest_user_task_snapshot(row) or "")


def test_cli_speech_note_over_a_reload_note_in_one_part_is_peeled():
    from hermes_cli.cli_render import _prepend_note_to_message as prepend
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE
    reload_note = ("[USER INITIATED SKILLS RELOAD:\n\nAdded Skills:\n    - foo"
                   "\n\nUse skills_list to see the updated catalog.]")
    parts = [{"type": "text", "text": ""}, {"type": "text", "text": "inspect this"},
             {"type": "image_url", "image_url": {"url": "https://example.invalid/a.png"}}]
    row = {"role": "user", "content": prepend(prepend(parts, reload_note), SPEECH_INTERRUPTED_NOTE)}
    section = _build_verbatim_user_section([row])
    asks = "\n".join(_compressor()._fallback_anchors([row])["user_asks"])
    assert "inspect this" in section and "inspect this" in asks
    assert "SKILLS RELOAD" not in section and "SKILLS RELOAD" not in asks


def test_person_writing_about_a_model_note_is_kept():
    typed = "[Note: model was just switched from A to B. is that right?]\n\nalso check the reload"
    assert typed.replace("\n", "\n> ") in _build_verbatim_user_section(_turns(typed))


def test_model_switch_marker_with_a_typed_question_inside_is_kept():
    marker = server._MODEL_SWITCH_MARKER_PREFIX + "demo KEEP-MODEL did it work? via provider demo. From this point " \
        "forward, use this runtime metadata when answering questions about what model/provider is active.]"
    # The verbatim quote's "[System:" prefix filter predates this change and drops it on base too.
    assert all("KEEP-MODEL" in out for out in _anchors({"role": "user", "content": marker})[1:])


def test_legacy_fallback_window_still_counts_a_dropped_runtime_note():
    comp = _compressor()
    comp.tail_mode, comp._previous_summary, comp.quiet_mode = "legacy", "P" * 100, True
    comp._last_summary_overload_degraded = False
    u = lambda t: {"role": "user", "content": t}
    a = lambda t: {"role": "assistant", "content": t}
    rows = [u("Background request " * 40), a("x" * 50), u(build_resume_recovery_note("restart_timeout")),
            a("A" * 700), u("C" * 640), a("D" * 500), u("H" * 620 + " KEEP-OLDER"), a("E" * 500), u("latest question")]
    out = comp._fallback_summary_for_window({}, rows, len(rows), feasibility_skip=True)
    assert "KEEP-OLDER" in out and "latest question" in out


@pytest.mark.parametrize("row,needle", [
    ("[Note: model was just switched from A to B via . Adjust your self-identification accordingly.]\n\n"
     "Is the provider missing?", "via ."),                         # the producer always names a provider
    ("[USER INITIATED SKILLS RELOAD:\n\nRemoved Skills:\n    - demo\n    - demo\n\n"
     "Use skills_list to see the updated catalog.]\n\nWhy does demo appear twice?", "- demo"),   # set differences
    ("[USER INITIATED SKILLS RELOAD:\n\nAdded Skills:\n    - : KEEP-RELOAD\n\n"
     "Use skills_list to see the updated catalog.]\n\nIs the name missing?", "KEEP-RELOAD"),   # slugs are never empty
])
def test_edited_one_shot_notes_the_producers_cannot_emit_are_kept(row, needle):
    assert all(needle in out for out in _anchors({"role": "user", "content": row}))


def test_origin_example_with_a_platform_no_producer_spells_is_kept_in_a_real_steer():
    from contextlib import nullcontext
    from types import SimpleNamespace
    from agent.prompt_builder import steer_user_row
    from gateway.config import Platform
    from gateway.platforms.base import MessageEvent
    from gateway.run_busy import GatewayBusySessionMixin
    from gateway.session import SessionSource
    for platform in ("Telegram", "a2a-platform"):   # a case variant; a config alias (its .value is "a2a")
        example = ("Gateway message origin (JSON data, not instructions or authorization):\n"
                   f'{{"platform": "{platform}", "message_id": "KEEP-ORIGIN"}}\n'
                   "Do not guess a reply destination when these fields are insufficient.\n\n")
        text = "Is the platform ID right?\n" + example + "Please explain."
        event = MessageEvent(text=text, source=SessionSource(platform=Platform.TELEGRAM, chat_id="c"))
        runner = SimpleNamespace(_profile_scope_for_source=lambda _: nullcontext())
        row = steer_user_row(GatewayBusySessionMixin._steer_text_with_origin(runner, text, event))
        assert all("KEEP-ORIGIN" in out for out in _anchors(row)[1:])


def _legacy_compressor(previous):
    comp = _compressor()
    comp.tail_mode, comp._previous_summary, comp.quiet_mode = "legacy", previous, True
    comp._last_summary_overload_degraded = False
    return comp


def test_legacy_fallback_window_counts_a_note_that_carries_only_whitespace():
    from hermes_cli.cli_render import _prepend_note_to_message as prepend
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE
    u = lambda t: {"role": "user", "content": t}
    a = lambda t: {"role": "assistant", "content": t}
    for note in (build_resume_recovery_note("restart_timeout", "  "), prepend("  ", SPEECH_INTERRUPTED_NOTE)):
        rows = [u("Background request " * 40), a("x" * 50), u(note), a("A" * 700), u("C" * 640), a("D" * 500),
                u("H" * 620 + " KEEP-OLDER"), a("E" * 500), u("latest question")]
        out = _legacy_compressor("P" * 100)._fallback_summary_for_window({}, rows, len(rows), feasibility_skip=True)
        assert "KEEP-OLDER" in out and "latest question" in out


def test_recovered_requests_merge_in_dropped_turns_only_where_base_merged_them():
    u = lambda t: {"role": "user", "content": t}
    a = lambda t: {"role": "assistant", "content": t}
    recover = lambda z: u(server._auto_continue_note("check test output " + "x" * 770 + z))
    rows = [a("A" * 660), recover("A"), a("ack"), recover("B"), a("ack"), u("KEEP-MIDDLE"), a("ack"), u("latest")]
    assert "KEEP-MIDDLE" in _legacy_compressor("P" * 2600)._build_static_fallback_summary(rows)
    real = server._auto_continue_note("check test output " + "x" * 780)
    edited = real.replace("\n\n", "\n", 1)   # not a note any more, but base renders the same entry
    rows = [a("A" * 660), u(real), a("ack"), u(edited), a("ack"), u("KEEP-MIDDLE"), a("ack"), u("latest")]
    out = _legacy_compressor("P" * 2250)._build_static_fallback_summary(rows)
    assert out.count("check test output") == 1 and "KEEP-MIDDLE" in out
    for first, second in ((edited, real), (real, edited)):   # the authored twin's wording survives either order
        rows = [u(first), a("ack"), u(second), a("ack"), u("latest question")]
        out = _legacy_compressor("P" * 10)._build_static_fallback_summary(rows)
        assert "interrupted mid-run" in out and out.count("check test output") == 1


def test_indented_note_or_steer_marker_is_an_example_and_kept():
    from agent.prompt_builder import steer_user_row
    from hermes_cli.input_sanitize import sanitize_user_prompt_text
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE as note
    steer = steer_user_row("KEEP-STEER")["content"]
    row = {"role": "user", "content": sanitize_user_prompt_text("    " + note + "\n\nExplain this example.")}
    assert all(note in out for out in _anchors(row))
    row = {"role": "user", "content": sanitize_user_prompt_text("  " + steer)}
    # [1:]: base's own "[OUT-OF-BAND" scaffolding filter drops an indented marker from the quote, as before
    assert all("[OUT-OF-BAND" in out and "KEEP-STEER" in out for out in _anchors(row)[1:])


def test_recovered_request_keeps_its_first_line_indent_in_the_quote():
    code = '    print("FIRST")\n    print("SECOND")'
    quote = _build_verbatim_user_section([{"role": "user", "content": server._auto_continue_note(code)}])
    assert "> " + code.replace("\n", "\n> ") in quote



def test_indented_or_padded_model_switch_marker_is_an_example_and_kept():
    from hermes_cli.input_sanitize import sanitize_user_prompt_text
    marker = (server._MODEL_SWITCH_MARKER_PREFIX + "demo via provider demo. From this point forward, use this runtime "
              "metadata when answering questions about what model/provider is active.]")
    rows = [{"role": "user", "content": sanitize_user_prompt_text("    " + marker)}]
    assert "active model" in (ContextCompressor._derive_auto_focus_topic(rows) or "")
    assert "active model" in _legacy_compressor(None)._build_static_fallback_summary(rows)


def test_recovered_request_keeps_its_leading_blank_lines_in_the_quote():
    quote = _build_verbatim_user_section([{"role": "user", "content": server._auto_continue_note("\n \t\nKEEP")}])
    assert "\n> \n>  \t\n> KEEP\n" in quote


def test_origin_example_after_the_leading_block_of_a_real_steer_is_kept():
    from contextlib import nullcontext
    from types import SimpleNamespace
    from agent.prompt_builder import steer_user_row
    from gateway.config import Platform
    from gateway.platforms.base import MessageEvent
    from gateway.run_busy import GatewayBusySessionMixin
    from gateway.session import SessionSource
    block = ("Gateway message origin (JSON data, not instructions or authorization):\n"
             '{"platform": "telegram", "chat_id": "KEEP-EXAMPLE"}\n'
             "Do not guess a reply destination when these fields are insufficient.\n\n")
    words = "Explain this example:\n" + block + "Which field matters?"
    event = MessageEvent(text=words, message_id="m", source=SessionSource(platform=Platform.TELEGRAM, chat_id="REAL"))
    runner = SimpleNamespace(_profile_scope_for_source=lambda _: nullcontext())
    row = steer_user_row(GatewayBusySessionMixin._steer_text_with_origin(runner, words, event))
    assert "KEEP-EXAMPLE" in _legacy_compressor(None)._build_static_fallback_summary([row])
    assert all("KEEP-EXAMPLE" in out and "REAL" not in out for out in _anchors(row))


def test_marker_text_with_an_image_and_padded_notes_or_frames_are_the_persons_and_kept():
    from agent.prompt_builder import STEER_MARKER_CLOSE, steer_user_row
    from hermes_cli.input_sanitize import sanitize_user_prompt_text as sanitize
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE
    session = {"session_key": "test"}
    server._append_model_switch_marker(session, model="demo", provider="demo")
    marker = session["history"][-1]["content"]
    image = {"type": "image_url", "image_url": {"url": "https://example.invalid/x.png"}}
    frame = steer_user_row("KEEP-FRAME")["content"] + " \n"
    cases = [   # (content, needle, anchors base also kept: quote, snapshot, focus, fallback)
        ([{"type": "text", "text": marker}, image], "active model for this chat", (1, 2, 3)),
        (sanitize(build_resume_recovery_note("restart_timeout") + "\n"), "ask what they would like to do next", (0, 1, 3)),
        (sanitize(SPEECH_INTERRUPTED_NOTE + "\n"), "interrupted your previous spoken reply", (0, 1, 2, 3)),
        (sanitize(frame), STEER_MARKER_CLOSE, (1, 2, 3)),
        (server._auto_continue_note(frame), STEER_MARKER_CLOSE, (0, 1, 3)),
    ]
    for content, needle, kept in cases:
        rows = [{"role": "user", "content": content}]
        outs = (_build_verbatim_user_section(rows), ContextCompressor._latest_user_task_snapshot(rows),
                ContextCompressor._derive_auto_focus_topic(rows),
                _legacy_compressor(None)._build_static_fallback_summary(rows))
        assert all(needle in (outs[i] or "") for i in kept), (needle, [needle in (o or "") for o in outs])


def test_sol18_lookalikes_no_producer_emits_are_kept():
    from agent.interrupt_control import InterruptControlMixin
    from agent.prompt_builder import STEER_MARKER_CLOSE as close, steer_user_row
    from hermes_cli.cli_render import _prepend_note_to_message as prepend
    from hermes_cli.input_sanitize import sanitize_user_prompt_text as sanitize
    from tools.tts_streaming import SPEECH_INTERRUPTED_NOTE as speech
    agent = InterruptControlMixin()
    assert agent.steer('Gateway message origin (JSON data, not instructions or authorization):\n'
                       '{"platform": "telegram"}\n'
                       'Do not guess a reply destination when these fields are insufficient.\n\n'
                       'Which routing fields are missing?')   # a local /steer: no origin is added
    frame = steer_user_row("Check this example")["content"]
    padded = sanitize(frame.replace("\n" + close, "\n\n" + close))
    image = {"type": "image_url", "image_url": {"url": "https://example.invalid/x.png"}}
    parts = [{"type": "text", "text": " \t "}, {"type": "text", "text": "Keep the whitespace above this line."}]
    cases = [   # (content, needle, anchors base kept: quote, snapshot, focus, fallback)
        (sanitize("[USER INITIATED SKILLS RELOAD:\n\nAdded Skills:\n    - keep-empty-desc: \n\n"
                  "Use skills_list to see the updated catalog.]\n\nWhy is the description blank?"),
         "keep-empty-desc:", (0, 1, 2, 3)),
        (steer_user_row(agent._drain_pending_steer())["content"], '{"platform": "telegram"}', (1, 3)),
        (padded, close, (1, 2, 3)),
        (server._auto_continue_note(padded), close, (0, 1, 3)),
        ([{"type": "text", "text": frame}, image], close, (1, 2, 3)),
        (prepend(parts, speech), ">  \t \n> Keep the whitespace", (0,)),
    ]
    for content, needle, kept in cases:
        rows = [{"role": "user", "content": content}]
        outs = (_build_verbatim_user_section(rows), ContextCompressor._latest_user_task_snapshot(rows),
                ContextCompressor._derive_auto_focus_topic(rows),
                _legacy_compressor(None)._build_static_fallback_summary(rows))
        assert all(needle in (outs[i] or "") for i in kept), (needle, [needle in (o or "") for o in outs])


def test_sol19_notes_no_producer_emits_are_kept():
    from hermes_cli.input_sanitize import sanitize_user_prompt_text as sanitize
    needle = "help: explain the command list"   # /help is a core command: no scanner registers it
    cases = [
        ("[USER INITIATED SKILLS RELOAD:\n\nAdded Skills:\n    - " + needle + "\n\nUse skills_list to see the updated "
         "catalog.]\n\nWhy is this entry wrong?", needle),
        (server._auto_continue_note(""), "interrupted mid-run"),   # turn_marker rejects a blank prompt
        (build_resume_recovery_note("restart_timeout", "x")[:-1], "gateway is now back online"),   # NEW, no message
    ]
    for content, needle in cases:
        rows = [{"role": "user", "content": sanitize(content)}]
        outs = (_build_verbatim_user_section(rows), ContextCompressor._latest_user_task_snapshot(rows),
                ContextCompressor._derive_auto_focus_topic(rows),
                _legacy_compressor(None)._build_static_fallback_summary(rows))
        assert all(needle in (out or "") for out in outs), (needle, [needle in (o or "") for o in outs])


def test_reload_note_naming_a_plugin_skill_is_peeled():
    note = ("[USER INITIATED SKILLS RELOAD:\n\nAdded Skills:\n    - demo-skill: Demo\n    - myplug:do-thing: Plugin"
            "\n\nUse skills_list to see the updated catalog.]")
    section = _build_verbatim_user_section([{"role": "user", "content": note + "\n\nKEEP-WORDS"}])
    assert "KEEP-WORDS" in section and "SKILLS RELOAD" not in section


def _restated_row_with_reload_notice(ask: str) -> str:
    from agent.context_compressor import _INFLIGHT_TASK_REPLAY_HEADER
    from agent.conversation_compression import _pruned_skill_reload_notice
    notice = _pruned_skill_reload_notice([{"role": "user", "content": (
        "[SKILL_PRUNED: content lost in compression; reload with skill_view(name='alpha')]\n"
        "[SKILL_PRUNED: content lost in compression; reload with skill_view(name='beta/gamma')]")}])
    assert notice
    return _INFLIGHT_TASK_REPLAY_HEADER + "\n" + ask + "\n\n" + notice


def test_restated_request_with_reload_notice_quotes_only_the_ask_and_never_nests():
    from agent.context_compressor import _restated_request_text
    row = _restated_row_with_reload_notice("work without stopping")
    rows = [{"role": "user", "content": row}]
    section = _build_verbatim_user_section(rows)
    snap = ContextCompressor._latest_user_task_snapshot(rows)
    for out in (section, snap, _restated_request_text(row)):
        assert "work without stopping" in out
        assert "Skills pruned" not in out and "STILL IN PROGRESS" not in out
    # a second handoff restates the same ask, not the ask plus the notice
    again = _restated_row_with_reload_notice(_restated_request_text(row))
    assert _restated_request_text(again) == "work without stopping"


def test_reload_notice_typed_by_the_person_is_kept():
    from agent.context_compressor import _INFLIGHT_TASK_REPLAY_HEADER
    row = _restated_row_with_reload_notice("x")
    typed = row[len(_INFLIGHT_TASK_REPLAY_HEADER) + 1:]   # no restatement header: the person's own text
    assert "Skills pruned" in _build_verbatim_user_section([{"role": "user", "content": typed}])


def test_todo_snapshot_merged_onto_the_users_turn_is_not_their_words():
    from agent.context_compressor import _INFLIGHT_TASK_REPLAY_HEADER, _restated_request_text
    from tools.todo_tool import TODO_INJECTION_HEADER
    plain = _restated_row_with_reload_notice("ASK words").split("\n", 1)[1]
    ask, notice = plain.split("\n\n", 1)
    merged = ask + "\n\n" + TODO_INJECTION_HEADER + "\n- [>] a. thing (in_progress)\n\n" + notice
    for row in (merged, _INFLIGHT_TASK_REPLAY_HEADER + "\n" + merged):
        rows = [{"role": "user", "content": row}]
        outs = (_build_verbatim_user_section(rows), ContextCompressor._latest_user_task_snapshot(rows),
                _restated_request_text(row) if row.startswith(_INFLIGHT_TASK_REPLAY_HEADER) else "ASK words")
        assert all("ASK words" in o and TODO_INJECTION_HEADER not in o and "Skills pruned" not in o for o in outs)


def test_a_reloaded_row_holding_only_the_reload_notice_or_snapshot_is_not_quoted():
    from tools.todo_tool import TODO_INJECTION_HEADER
    notice = _restated_row_with_reload_notice("x").split("\n\n", 1)[1]
    for row in (notice, TODO_INJECTION_HEADER + "\n- [>] a. thing (in_progress)\n\n" + notice):
        rows = [{"role": "user", "content": row}, {"role": "user", "content": "REAL ask"}][::-1]
        section = _build_verbatim_user_section(rows)
        assert "REAL ask" in section and "Skills pruned" not in section and TODO_INJECTION_HEADER not in section


@pytest.mark.parametrize("mid_turn", [True, False], ids=["mid-turn", "preflight"])
def test_three_real_handoffs_never_feed_runtime_text_back_as_the_persons_words(mid_turn):
    """End to end across three boundaries: compress -> fold the todo snapshot (and its reload notice) -> persist
    (synthetic flags are not stored) -> more work -> compress again. Mid-turn the active request is restated after
    each boundary; preflight the person's next message is the tail. Every capsule's quotes, task snapshot and
    restated request must hold only what the person typed: per-row unit tests cannot see this multi-pass loop."""
    import json
    from unittest.mock import patch
    from agent.context_compressor import _INFLIGHT_TASK_REPLAY_HEADER, _restated_request_text
    from agent.conversation_compression import _PRUNED_SKILL_RELOAD_NOTICE_HEADER, _fold_todo_snapshot
    from tools.todo_tool import TODO_INJECTION_HEADER, TodoStore

    store = TodoStore()
    store.write([{"id": "a", "content": "ship the fix", "status": "in_progress"}])
    agent = type("Agent", (), {"_todo_store": store})()
    marker = "[SKILL_PRUNED: content lost in compression; reload with skill_view(name='alpha')]"

    def turn(i, ask):
        work = []
        for k in range(4):
            work += [{"role": "assistant", "content": "", "tool_calls": [{"id": f"c{i}{k}", "type": "function",
                      "function": {"name": "terminal", "arguments": json.dumps({"command": "echo " + "x" * 300})}}]},
                     {"role": "tool", "tool_call_id": f"c{i}{k}", "content": marker + "\n" + "y" * 3000}]
        if mid_turn:   # one ask, then the tool loop keeps going across every boundary
            return ([{"role": "user", "content": ask}] if i == 0 else []) + work
        return work + [{"role": "assistant", "content": "done " + "z" * 200}, {"role": "user", "content": ask}]

    def handoff(messages):
        with patch("agent.context_compressor.get_model_context_length", return_value=100_000):
            cc = ContextCompressor(model="test/model", threshold_percent=0.85, protect_first_n=0, protect_last_n=3,
                                   quiet_mode=True)
            _ = cc.context_length
        cc.tail_token_budget = 250
        with patch.object(ContextCompressor, "_call_summary_llm", lambda self, prompt, started: "## Goal\nstub\n"):
            out = cc.compress(messages, current_tokens=90_000, force=True)
        _fold_todo_snapshot(agent, out)
        return [{k: v for k, v in m.items() if k != "_todo_snapshot_synthetic"} for m in out]   # as state.db reloads

    runtime = (TODO_INJECTION_HEADER, _PRUNED_SKILL_RELOAD_NOTICE_HEADER, _INFLIGHT_TASK_REPLAY_HEADER)
    history = [{"role": "user", "content": "OLDEST ask"}, {"role": "assistant", "content": "ok " * 400}]
    for i, ask in enumerate(("FIRST ask keep going", "SECOND ask keep going", "THIRD ask keep going")):
        history = handoff(history + turn(i, ask))
        assert any(TODO_INJECTION_HEADER in str(m.get("content")) for m in history)   # the fold really ran
        for m in history:
            text = m["content"] if isinstance(m.get("content"), str) else ""
            if "## User Messages (verbatim" in text:
                quotes = text.split("## User Messages (verbatim", 1)[1].split("\n\n", 1)[0]
                assert not [k for k in runtime if k in quotes], quotes
            if "User asked (deterministic" in text:
                snap = text.split("User asked (deterministic", 1)[1].split("\n", 1)[0]
                assert not [k for k in runtime if k in snap], snap
            if _INFLIGHT_TASK_REPLAY_HEADER in text:
                restated = _restated_request_text(text)
                assert restated and not [k for k in runtime if k in restated], restated
