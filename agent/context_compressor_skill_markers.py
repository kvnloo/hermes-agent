"""The skill prune marker (the ONE canonical reload signal compaction leaves for a pruned skill) and the
name checks shared by the compressor's emit, re-inject and reload-notice sites."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Ghost-skill defense: the ONE canonical prune marker; emit sites and presence
# checks must use the same string so they cannot drift.
# Ghost-skill defense (#32106): when compaction reduces an old ``skill_view`` result to a 1-line metadata
# summary, the model still believes the skill is loaded even though its instructions are gone. The marker
# below is the ONE canonical prune signal — ``_skill_pruned_marker()`` builds it and every presence check
# matches against the same string, so the emit side and the check side can never drift apart (the original
# PR #44166 emitted ``[SKILL_PRUNED:`` but presence-checked ``[SKILL_PRUNED]``, making re-injection fire
# even when the marker had survived).
SKILL_PRUNED_MARKER_PREFIX = "[SKILL_PRUNED:"
# Bounds the re-injected "## Pruned Skills" block; newest-referenced win.
_MAX_PRUNED_SKILL_MARKERS = 20


def _skill_pruned_marker(skill_name: str) -> str:
    """Return the canonical prune marker for *skill_name* (shared by emit and check sites)."""
    return (
        f"{SKILL_PRUNED_MARKER_PREFIX} content lost in compression; "
        f"reload with skill_view(name='{skill_name}')]"
    )


# Anchored on the shared prefix so marker wording changes stay in sync.
_SKILL_PRUNED_MARKER_RE = re.compile(
    re.escape(SKILL_PRUNED_MARKER_PREFIX) + r"[^\]]*?reload with skill_view\(name='([^']+)'\)",
)


_SKILL_PRUNED_MARKER_LINE_RE = re.compile(_SKILL_PRUNED_MARKER_RE.pattern + r"\]?[ \t]*\n?")


def _extract_pruned_skill_names(text: str) -> list[str]:
    """Return skill names referenced by prune markers in *text*, in order."""
    return list(dict.fromkeys(m.group(1) for m in _SKILL_PRUNED_MARKER_RE.finditer(text or "")))


def _resolvable_skill_names(names: list[str]) -> list[str]:
    """*names* that skill_view can still load (#131487). If the skill lookup itself fails, every name is kept:
    a missed reload loses the policy, a stale one costs one failed call."""
    try:
        from tools.skills_tool import skill_name_resolves
        return [name for name in names if skill_name_resolves(name)]
    except Exception:
        logger.debug("Could not validate pruned skill markers", exc_info=True)
        return list(names)


def _validated_pruned_skill_names(text: str) -> list[str]:
    """Pruned skill names in *text* that skill_view can still load."""
    return _resolvable_skill_names(_extract_pruned_skill_names(text))
