"""Quick-command skill alias parsing for the gateway slash consumer."""

def alias_skill_target(config: dict, base: str, arg: str, is_skill):
    """Resolve a quick-command alias whose target is a profile skill command to
    ``(target_base, combined_arg)`` for command.dispatch; None otherwise.

    A quick-command alias to a skill must not reach the slash worker: the worker
    runs the CLI non-interactively, where a loaded skill is queued onto
    ``_pending_input`` that only the interactive REPL drains, so the skill is
    silently dropped (#106063). Rewriting to the resolved skill mirrors the
    messaging gateway's ``_hm_expand_alias_quick_command`` — the target's own
    args are prepended to the user's args, and dispatch routes through the same
    skill stage a direct ``/skill`` already uses."""
    qc = config.get("quick_commands", {}).get(base)
    if not isinstance(qc, dict) or qc.get("type") != "alias":
        return None
    target = str(qc.get("target", "")).strip()
    target_tokens = target.lstrip("/").split()
    if not target_tokens:
        return None
    target_base = target_tokens[0].lower()
    # Rewrite only when the target is definitively a skill. ``None`` (the scan
    # raised) is not a "yes": leaving the alias unrewritten falls through to the
    # gate below, which handles the fail-open case, rather than dispatching a
    # command that may not be a skill at all.
    if is_skill(target_base) is not True:
        return None
    combined_arg = " ".join(target_tokens[1:] + ([arg] if arg else [])).strip()
    return target_base, combined_arg
