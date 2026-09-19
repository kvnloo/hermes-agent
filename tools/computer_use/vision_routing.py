"""Vision-routing decisions for ``computer_use`` capture results. ``capture`` (mode som|vision) returns a
``_multimodal`` screenshot envelope as the tool result. A text-only main model, or a provider that rejects multimodal
tool results, turns that into a hard 400/404 — even with a working ``auxiliary.vision`` model in config. This module
decides: multimodal envelope, or pre-analyse via aux vision so the main model only ever sees text?

Uses the shared two-axis resolver (:func:`tools.vision_tools.resolve_native_tool_result_pixels`):

    native iff model_can_understand_images AND transport_accepts_tool_result_images
           AND NOT veto AND NOT explicit aux override

``supports_vision`` is NOT generalized as transport acceptance. Unknown fails closed
toward aux routing (one extra LLM call) rather than a hard 400 on the main model.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def _explicit_aux_vision_override(cfg: Optional[Dict[str, Any]]) -> bool:
    """True when ``auxiliary.vision`` carries a non-default user override; mirrors ``agent.image_routing`` so the capture
    and user-attached-image paths agree. ``provider: "auto"``, blanks or a missing block are *not* explicit."""
    aux = cfg.get("auxiliary") if isinstance(cfg, dict) else None
    vision = aux.get("vision") if isinstance(aux, dict) else None
    if not isinstance(vision, dict):
        return False
    provider = str(vision.get("provider") or "").strip().lower()
    return provider not in ("", "auto") or any(str(vision.get(k) or "").strip() for k in ("model", "base_url"))

def _lookup_user_declared_supports_vision(provider: str, model: str, cfg: Optional[Dict[str, Any]]) -> Optional[bool]:
    """Config-declared ``supports_vision`` for the active route (None on failure)."""
    try:
        from agent.image_routing import _supports_vision_override
        return _supports_vision_override(cfg, provider, model)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("computer_use vision_routing: config override lookup failed: %s", exc)
        return None

def _models_dev_supports_vision(provider: str, model: str, cfg: Optional[Dict[str, Any]]) -> Optional[bool]:
    """Raw models.dev capability lookup — fallback when ``agent.image_routing`` is unavailable."""
    from agent.models_dev import get_model_capabilities
    caps = get_model_capabilities(provider, model)
    return None if caps is None else caps.supports_vision

def _lookup_supports_vision(provider: str, model: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[bool]:
    """Config/models.dev ``supports_vision`` for *(provider, model)*; prefers
    ``agent.image_routing._lookup_supports_vision``. Any lookup error → None (caller fails closed to aux)."""
    if not provider or not model:
        return None
    try:
        from agent.image_routing import _lookup_supports_vision as lookup
    except Exception:
        lookup = _models_dev_supports_vision
    try:
        return lookup(provider, model, cfg)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("computer_use vision_routing: caps lookup failed for %s:%s — %s", provider, model, exc)
        return None

def _provider_accepts_multimodal_tool_result(provider: str, model: str) -> Optional[bool]:
    """Whether *provider*+*model* carries images inside tool-result messages; reuses ``tools.vision_tools`` to stay in
    lockstep with the ``vision_analyze`` fast path. None on import failure so callers fall back to aux, not guess."""
    if not provider:
        return None
    try:
        from tools.vision_tools import _supports_media_in_tool_results
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("computer_use vision_routing: tool-result support lookup failed: %s", exc)
        return None
    return bool(_supports_media_in_tool_results(provider, model))

def should_route_capture_to_aux_vision(provider: str, model: str, cfg: Optional[Dict[str, Any]]) -> bool:
    """True iff the screenshot should be pre-analysed via aux vision; False keeps the multimodal envelope.

    Uses the same two-axis resolver as ``vision_analyze``
    (:func:`tools.vision_tools.resolve_native_tool_result_pixels`): native pixels
    only when model vision AND tool-result transport are positively known.
    """
    from tools.vision_tools import resolve_native_tool_result_pixels
    return not resolve_native_tool_result_pixels(provider, model, cfg).native


__all__ = ["should_route_capture_to_aux_vision"]
