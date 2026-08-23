"""OX1000 C2 — pre-warmed command-policy block for Kanban workers.

Evidence (OX1000 F1/F9): approval-gate blocks and repeated identical
commands / same-file patch loops dominate wasted worker turns. A concise,
byte-stable command-policy section is appended to ``KANBAN_GUIDANCE`` so
every dispatched worker starts with the retry/read-hygiene contract
instead of discovering it by failing.

Invariants:
- The block is a module-level constant: deterministic content, no
  timestamps or session-specific values, so it never threatens prompt
  caching.
- It only ever rides on the existing kanban-worker injection point
  (``KANBAN_GUIDANCE``, resolved once at agent init when the dispatcher
  spawned this process). Non-Kanban sessions never see it.
- Gated by ``kanban.worker_command_policy`` in config.yaml (default
  False) so boards outside the zer0 canary opt in explicitly.

Instrumentation: :func:`command_policy_hash` gives a stable digest of
the active policy text so tests and local measurement scripts can
compare policy presence across runs without any outbound telemetry.
"""
from __future__ import annotations

import hashlib

# OX1000 C2 command policy — all four clauses from the fixed design.
KANBAN_COMMAND_POLICY = (
    "# Command policy (pre-warmed)\n"
    "\n"
    "You run in single-query mode with no user present to approve blocked\n"
    "commands, so avoid known-blocked shapes entirely:\n"
    "1. **File creation.** Never use heredocs, `python -c`, shell `-c`\n"
    "   wrappers, `echo`, or `cat` to create or overwrite files. Use\n"
    "   `write_file` / `patch` for files; run ordinary commands directly.\n"
    "2. **Command loops.** If an identical terminal command has failed or\n"
    "   been blocked 4 times in this session, stop retrying it. Replan\n"
    "   with a different mechanism (different tool, different approach).\n"
    "3. **Patch loops.** After 2 patch failures on the same file, re-read\n"
    "   the file's exact current contents before editing again. The third\n"
    "   attempt must replace the enclosing unit or whole file — never a\n"
    "   third replay of a stale patch.\n"
    "4. **Read hygiene.** Do not re-read an unchanged file or range when\n"
    "   you already have its contents; reuse your earlier result unless\n"
    "   freshness materially matters (the file may have just changed).\n"
)

# Config key under `kanban:` that gates the policy injection.
WORKER_COMMAND_POLICY_CONFIG_KEY = "worker_command_policy"


def worker_command_policy_enabled(config: dict | None) -> bool:
    """Return True when ``kanban.worker_command_policy`` is truthy.

    Accepts a full loaded config dict (reads the ``kanban`` section) or a
    bare kanban-section dict. Missing/invalid input → False (default-off).
    """
    if not isinstance(config, dict):
        return False
    section = config.get("kanban", config)
    if not isinstance(section, dict):
        return False
    return bool(section.get(WORKER_COMMAND_POLICY_CONFIG_KEY, False))


def load_worker_command_policy_enabled() -> bool:
    """Resolve the gate from the profile's config.yaml (read-only)."""
    try:
        from hermes_cli.config import load_config_readonly

        return worker_command_policy_enabled(load_config_readonly())
    except Exception:
        return False


def command_policy_hash(policy_text: str | None = None) -> str:
    """Stable SHA-256 hex digest of the policy block (first 16 chars).

    Deterministic instrumentation for tests and measurement scripts:
    equal policy text → equal hash across runs and machines. No network,
    no state.
    """
    if policy_text is None:
        policy_text = KANBAN_COMMAND_POLICY
    return hashlib.sha256(policy_text.encode("utf-8")).hexdigest()[:16]
