"""``hermes doctor`` → Context Health: what every session carries before the first message.

Read-only and prompt-neutral: nothing here changes the bytes sent to a model. It reports the
failures that otherwise only show up as a slower, dumber agent: a configured context engine that
silently falls back to the built-in compressor, a memory store too full to accept new entries,
and the size of the fixed prompt prefix (``hermes prompt-size`` has the per-skill/toolset detail).
"""

from __future__ import annotations

from hermes_cli.doctor_report import (
    Finding,
    check_bool,
    check_info,
    check_ok,
    check_warn,
    doctor_check,
    warn_on_error,
)

# Warn before the memory tool starts refusing writes (it rejects at 100%).
MEMORY_FULL_RATIO = 0.9


def _context_engine_row(cfg: dict, f: Finding) -> None:
    ctx = cfg.get("context")
    name = (ctx.get("engine") if isinstance(ctx, dict) else None) or "compressor"
    if name == "compressor":
        check_ok("Context engine: built-in compressor")
        return
    from plugins.context_engine import find_engine_dir

    if check_bool(
        find_engine_dir(name) is not None,
        f"Context engine: {name}",
        (
            f"Context engine '{name}' is configured but not discoverable",
            "(sessions silently use the built-in compressor)",
        ),
        fail=True,
    ):
        return
    f.manual_issues.append(
        f"context.engine '{name}' does not resolve: install it under plugins/{name}/ with "
        f"register_context_engine (or a ContextEngine subclass) in its __init__.py, "
        f"or run: hermes config set context.engine compressor"
    )


def _memory_rows(cfg: dict, f: Finding) -> None:
    from tools.memory_tool_store import MemoryStore

    mem = cfg.get("memory")
    mem = mem if isinstance(mem, dict) else {}
    store = MemoryStore(
        int(mem.get("memory_char_limit", 2200)), int(mem.get("user_char_limit", 1375))
    )
    store.load_from_disk()
    for target, label in (("memory", "MEMORY.md"), ("user", "USER.md")):
        used, limit = store._char_count(target), store._char_limit(target)
        if limit <= 0:
            continue
        text = f"{label} {used:,}/{limit:,} chars ({used * 100 // limit}%)"
        if used < limit * MEMORY_FULL_RATIO:
            check_ok(text)
            continue
        check_warn(
            text, "(new entries will be refused; consolidate or remove stale ones)"
        )
        f.manual_issues.append(
            f"{label} is {used * 100 // limit}% full: consolidate it, or raise "
            f"memory.{'user' if target == 'user' else 'memory'}_char_limit"
        )


def _prompt_prefix_row() -> None:
    from hermes_cli.prompt_size import compute_prompt_breakdown

    data = compute_prompt_breakdown("cli")
    fixed = data["system_prompt"]["bytes"] + data["tools"]["json_bytes"]
    check_info(
        f"Fixed prefix per request: {fixed / 1024:.1f} KB (system prompt "
        f"{data['system_prompt']['bytes'] / 1024:.1f} KB, skills index "
        f"{data['skills_index']['bytes'] / 1024:.1f} KB, {data['tools']['count']} tool schemas "
        f"{data['tools']['json_bytes'] / 1024:.1f} KB); details: hermes prompt-size"
    )


@doctor_check(on_error="Context health check failed: {e}")
def _check_context_health(should_fix: bool, f: Finding) -> None:
    from hermes_cli.config import load_config

    cfg = load_config()
    _context_engine_row(cfg, f)
    with warn_on_error("Memory store unreadable: {e}"):
        _memory_rows(cfg, f)
    with warn_on_error("Prompt size unavailable: {e}"):
        _prompt_prefix_row()
