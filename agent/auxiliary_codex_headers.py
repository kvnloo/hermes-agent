"""Cache-affinity request headers for Codex auxiliary Responses calls (#148675)."""

from typing import Any


def add_aux_codex_cache_headers(
    kwargs: dict[str, Any], *, is_codex_backend: bool,
    session_id: str, cache_scope: str,
) -> None:
    """Use physical session identity and the main transport's stable cache key."""
    if not is_codex_backend:
        return
    from agent.transports.codex import (
        _bounded_prompt_cache_key,
        _cache_scope_from_session_id,
        _merge_extra_headers,
    )

    affinity = kwargs.get("prompt_cache_key") or _bounded_prompt_cache_key(
        _cache_scope_from_session_id(cache_scope or session_id)
    )
    headers = {key: str(value) for key, value in (
        ("session_id", session_id), ("x-client-request-id", affinity),
    ) if value}
    if headers:
        _merge_extra_headers(kwargs, **headers)
