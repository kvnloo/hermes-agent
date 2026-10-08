"""Solstice inference transport: Gemini's per-user-quota methods with bearer auth.

Provider discovery runs in deliberately minimal interpreters such as the PM
runtime. Keep the heavy native Gemini transport lazy so merely registering the
profile does not require ``httpx``; actual inference still loads the canonical
adapter and inherits every request/stream/error fix from it.
"""

from __future__ import annotations

from typing import Any

INFERENCE_BASE_URL = "https://generativelanguage.googleapis.com/v1alpha"

_SOLSTICE_CLIENT_CLASS: type[Any] | None = None


def solstice_client_class() -> type[Any]:
    """Return the cached Solstice transport, importing runtime dependencies on first use."""
    global _SOLSTICE_CLIENT_CLASS

    if _SOLSTICE_CLIENT_CLASS is not None:
        return _SOLSTICE_CLIENT_CLASS

    from agent.gemini_native_adapter import GeminiNativeClient, gemini_http_error

    class SolsticeClient(GeminiNativeClient):
        """Gemini native client on the per-user-quota RPC methods."""

        GENERATE_METHOD, STREAM_METHOD = "generateContentPerUserQuota", "streamGenerateContentPerUserQuota"
        MISSING_KEY_ERROR = "Solstice needs a signed-in account. Run `hermes auth add solstice`."

        def __init__(self, *, base_url: Any = None, **kwargs: Any) -> None:
            # No base means this endpoint, never the generic Gemini default (a different API surface).
            super().__init__(base_url=base_url or INFERENCE_BASE_URL, **kwargs)

        def _auth_headers(self) -> dict[str, str]:
            return {"Authorization": f"Bearer {self.api_key}"}

        def _http_error(self, response: Any, body_text: Any = None) -> Any:
            # The API-key remedies (free tier, Standard key, wrong key surface) do not apply to a bearer.
            return gemini_http_error(response, body_text=body_text, base_url=self.base_url, key_guidance=False)

    # Keep diagnostics and reprs identical to the former module-level class.
    SolsticeClient.__qualname__ = "SolsticeClient"
    _SOLSTICE_CLIENT_CLASS = SolsticeClient
    return SolsticeClient


def __getattr__(name: str) -> Any:
    """Preserve the historical ``transport.SolsticeClient`` import lazily."""
    if name == "SolsticeClient":
        return solstice_client_class()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["INFERENCE_BASE_URL", "SolsticeClient", "solstice_client_class"]
