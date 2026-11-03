"""Normalize process_manage log and wait bounds at the registry seam (#141988).

The tool schema says integer, but JSON calls can supply numeric strings. Keep
the established log semantics: omitted offset reads the tail; explicit zero
starts at the first line. Negative offset handling is a separate issue (#146914).
"""


def coerce_int(value: int | float | str | None, *, name: str, default: int | None) -> int | None:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer (got {value!r})")
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be an integer (got {value!r})") from None


def select_log_lines(
    lines: list[str], offset: int | float | str | None, limit: int | float | str | None,
) -> tuple[list[str], bool]:
    """Return the selected lines and whether the final output has been observed."""
    page_offset = coerce_int(offset, name="offset", default=None)
    page_limit = coerce_int(limit, name="limit", default=200)
    if page_limit is None or page_limit < 1:
        raise ValueError(f"limit must be positive (got {page_limit})")

    total = len(lines)
    if page_offset is None:
        selected = lines[-page_limit:]
        return selected, bool(selected) or total == 0

    selected = lines[page_offset:page_offset + page_limit]
    stop = slice(page_offset, page_offset + page_limit).indices(total)[1]
    return selected, total == 0 or (bool(selected) and stop == total)
