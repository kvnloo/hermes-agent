"""Memory-provider initialization context shared by agent startup consumers."""

from contextlib import suppress
from typing import Any, Dict

from hermes_constants import get_hermes_home


def _memory_provider_init_kwargs(agent, platform) -> Dict[str, Any]:
    """Scoping kwargs for ``MemoryManager.initialize_all`` (status_callback is CLI-only:
    gateway status travels a different path and the indicator no-ops without it)."""
    from agent.agent_init import _GATEWAY_IDENTITY_PARAMS

    kwargs = {
        "session_id": agent.session_id,
        "platform": platform or "cli",
        "hermes_home": str(get_hermes_home()),
        # platform="cron" (scheduler) / "subagent" (delegate_task) → providers skip writes (MemoryProvider.initialize).
        "agent_context": platform if platform in ("cron", "subagent") else "primary",
    }
    if kwargs["platform"] == "cli":
        kwargs["warning_callback"] = agent._emit_warning
        kwargs["status_callback"] = agent._emit_status
    # Session title (e.g. honcho derives chat-scoped session keys from it).
    if agent._session_db:
        with suppress(Exception):
            _st = agent._session_db.get_session_title(agent.session_id)
            if _st:
                kwargs["session_title"] = _st
                _source = agent._session_db.get_session_title_source(agent.session_id)
                if _source:
                    kwargs["session_title_source"] = _source
    # Gateway user/chat identity for per-user scoping (gateway_session_key: stable per-chat
    # Honcho session isolation).
    for _ident in _GATEWAY_IDENTITY_PARAMS:
        _val = getattr(agent, f"_{_ident}")
        if _val:
            kwargs[_ident] = _val
    if agent.session_cwd:
        kwargs["cwd"] = agent.session_cwd
    # Profile identity for per-profile provider scoping
    with suppress(Exception):
        from hermes_cli.profiles import get_active_profile_name
        kwargs["agent_identity"] = get_active_profile_name()
        kwargs["agent_workspace"] = "hermes"
    return kwargs
