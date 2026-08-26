"""Profile-scoped registry for realtime voice providers."""

from __future__ import annotations

import threading
from typing import Optional

from agent.realtime_voice import RealtimeVoiceProvider
from hermes_constants import hermes_home_key

_providers: dict[str, RealtimeVoiceProvider] = {}
_scoped_providers: dict[str, dict[str, RealtimeVoiceProvider]] = {}
_lock = threading.Lock()


def _key(provider_name: str) -> str:
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise ValueError("realtime voice provider name must be a non-empty string")
    return provider_name.strip().lower()


def register_provider(
    provider: RealtimeVoiceProvider, *, scope: Optional[str] = None
) -> None:
    if not isinstance(provider, RealtimeVoiceProvider):
        raise TypeError(
            "register_provider() expects a RealtimeVoiceProvider instance, "
            f"got {type(provider).__name__}"
        )
    name = _key(provider.name)
    with _lock:
        target = (
            _providers if scope is None else _scoped_providers.setdefault(scope, {})
        )
        target[name] = provider


def get_provider(
    name: str, *, scope: Optional[str] = None
) -> RealtimeVoiceProvider | None:
    if not isinstance(name, str) or not name.strip():
        return None
    name = name.strip().lower()
    with _lock:
        return _scoped_providers.get(scope or hermes_home_key(), {}).get(
            name
        ) or _providers.get(name)


def resolve_provider(
    name: str, *, scope: Optional[str] = None
) -> RealtimeVoiceProvider:
    provider = get_provider(name, scope=scope)
    if provider is None:
        raise LookupError(f"Realtime voice provider {name!r} is not registered")
    if not provider.is_available():
        raise RuntimeError(f"Realtime voice provider {name!r} is unavailable")
    return provider


def snapshot_registration(
    name: str, *, scope: Optional[str] = None
) -> RealtimeVoiceProvider | None:
    name = _key(name)
    with _lock:
        target = _providers if scope is None else _scoped_providers.get(scope, {})
        return target.get(name)


def restore_registration(
    name: str,
    current: RealtimeVoiceProvider,
    previous: RealtimeVoiceProvider | None,
    *,
    scope: Optional[str] = None,
) -> bool:
    name = _key(name)
    with _lock:
        target = (
            _providers if scope is None else _scoped_providers.setdefault(scope, {})
        )
        if target.get(name) is not current:
            return False
        if previous is None:
            target.pop(name, None)
        else:
            target[name] = previous
        if scope is not None and not target:
            _scoped_providers.pop(scope, None)
    return True


def _reset_for_tests() -> None:
    with _lock:
        _providers.clear()
        _scoped_providers.clear()
