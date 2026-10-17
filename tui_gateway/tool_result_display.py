"""Bounded display copies of tool results; never mutate provider history or SQLite."""

from __future__ import annotations

import json

# One budget for live completions and history. Keep JSON structure (exit codes,
# paths, counts, etc.) while bounding text, fan-out and nesting independently.
TOOL_RESULT_TEXT_BUDGET = 32_768
TOOL_RESULT_NODE_BUDGET = 1_024
_TRUNCATED = "\n[tool result truncated]\n"
_TAIL_FIELDS = frozenset({"output", "stdout", "stderr"})


def bounded_tool_result(value: object) -> object:
    """Preserve small results byte-for-byte, including JSON-encoded stored content."""
    encoded = isinstance(value, str)
    parsed = value
    if encoded:
        try:
            parsed = json.loads(value)
        except (ValueError, RecursionError):
            pass
    remaining_text = TOOL_RESULT_TEXT_BUDGET
    remaining_nodes = TOOL_RESULT_NODE_BUDGET

    def visit(item, field="", depth=0):
        nonlocal remaining_text, remaining_nodes
        remaining_nodes -= 1
        if isinstance(item, str):
            keep = min(len(item), remaining_text)
            remaining_text -= keep
            if keep == len(item):
                return item
            return (_TRUNCATED + item[-keep:] if keep else _TRUNCATED) if field in _TAIL_FIELDS else item[:keep] + _TRUNCATED
        if depth >= 12 or remaining_nodes <= 0:
            return "[tool result truncated]"
        if isinstance(item, dict):
            out = {}
            # Scalar status metadata must survive even when a large body uses the budget.
            entries = sorted(item.items(), key=lambda pair: isinstance(pair[1], (str, dict, list)))
            for key, child in entries:
                if remaining_nodes <= 0 or len(out) >= 256:
                    out["_truncated"] = True
                    break
                out[str(key)[:256]] = visit(child, str(key), depth + 1)
            return out
        if isinstance(item, list):
            out = []
            for child in item:
                if remaining_nodes <= 0 or len(out) >= 256:
                    out.append("[tool result truncated]")
                    break
                out.append(visit(child, field, depth + 1))
            return out
        return item

    bounded = visit(parsed)
    if bounded == parsed:
        return value
    return json.dumps(bounded, ensure_ascii=False) if encoded and parsed is not value else bounded
