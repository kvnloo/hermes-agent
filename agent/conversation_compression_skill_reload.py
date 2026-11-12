"""Pruned-skill reload notice: tell the model to reload skills whose bodies a compaction pruned to markers."""

from __future__ import annotations

from typing import Any

from agent.conversation_compression_scaffolding import _message_text

# Compaction re-injects the todo list verbatim but prunes skills to markers, so
# couple them: tell the model to reload pruned skills BEFORE acting on tasks.
# Lives after TODO_INJECTION_HEADER so it strips with the snapshot next time.
_PRUNED_SKILL_RELOAD_NOTICE_HEADER = "[Skills pruned during compression — reload before acting on these tasks]"


def _strip_stale_block_text(text: str) -> str:
    """*text* without stale snapshot blocks. A todo block runs to the end of the text (it carries the notice
    when both exist); a notice that rode alone is one paragraph, so user text merged after it stays."""
    from tools.todo_tool import TODO_INJECTION_HEADER
    todo, notice = text.find(TODO_INJECTION_HEADER), text.find(_PRUNED_SKILL_RELOAD_NOTICE_HEADER)
    if todo != -1 and (notice == -1 or todo < notice):
        return text[:todo].rstrip()
    if notice == -1:
        return text
    end = text.find("\n\n", notice)
    head, tail = text[:notice].rstrip(), text[end:].strip() if end != -1 else ""
    return _strip_stale_block_text(f"{head}\n\n{tail}" if head and tail else head or tail)


def _pruned_skill_reload_notice(compressed: list, *, with_todos: bool = True) -> str:
    """Reload notice for skills whose bodies were pruned, or ``""``.
    Scans ``[SKILL_PRUNED: ...]`` markers in the post-compression transcript; first-seen order, deduplicated,
    capped at ``_MAX_PRUNED_SKILL_MARKERS``. ``with_todos=False`` words it for a boundary with no task list."""
    from agent.context_compressor import _MAX_PRUNED_SKILL_MARKERS, _extract_pruned_skill_names
    names: list = []
    for message in compressed:
        if not isinstance(message, dict):
            continue
        for name in _extract_pruned_skill_names(_message_text(message)):
            if name not in names:
                names.append(name)
    del names[_MAX_PRUNED_SKILL_MARKERS:]
    if not names:
        return ""
    calls = "; ".join(f"skill_view(name='{name}')" for name in names)
    if not with_todos:
        return (
            f"{_PRUNED_SKILL_RELOAD_NOTICE_HEADER}\n"
            "The skill instructions loaded before this compression boundary were pruned. Before "
            f"continuing work that depends on these skills, reload them first: {calls}."
        )
    return (
        f"{_PRUNED_SKILL_RELOAD_NOTICE_HEADER}\n"
        "The task list above crossed the compression boundary verbatim, but "
        "the skill instructions that governed it were pruned. Before "
        f"executing any preserved task that depends on these skills, reload "
        f"them first: {calls}. After reloading, re-check that each pending "
        "task is still justified — findings recorded before the boundary may have invalidated it."
    )


def _standalone_reload_notice(agent: Any, compressed: list) -> str:
    """No todo list: the reload notice rides alone. Refresh, never stack — notices left by earlier boundaries
    are stripped (a notice-only row is deleted) before the new one is returned for the caller to fold in."""
    from agent.conversation_compression import _replace_message_content, _strip_stale_todo_snapshot
    notice = _pruned_skill_reload_notice(compressed, with_todos=False)
    if not notice:
        return ""
    for i in range(len(compressed) - 1, -1, -1):
        message = compressed[i]
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        old = message.get("content")
        new = _strip_stale_todo_snapshot(old)
        if new == old:
            continue
        if message.get("_todo_snapshot_synthetic") and not _message_text({"role": "user", "content": new}).strip():
            del compressed[i]
        else:
            _replace_message_content(message, new)
    agent._repair_message_sequence(compressed)
    return notice


def _salvage_reduce_todo_snapshot(out: list[dict[str, Any]]) -> None:
    """Last-resort shrink: drop the synthetic todo snapshot, keeping only a pruned-skill reload notice if present."""
    for i in range(len(out) - 1, -1, -1):
        msg = out[i]
        if not isinstance(msg, dict) or not (msg.get("_todo_snapshot_synthetic") and msg.get("role") == "user"):
            continue
        content = msg.get("content")
        notice_idx = content.find(_PRUNED_SKILL_RELOAD_NOTICE_HEADER) if isinstance(content, str) else -1
        if notice_idx >= 0:
            msg["content"] = content[notice_idx:]
        else:
            del out[i]
        return
