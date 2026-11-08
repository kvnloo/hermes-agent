"""Write refusals name why a full read was incomplete (issue #150889)."""

import json
from unittest.mock import patch

import pytest

from tools.file_tools import clear_file_ops_cache
from tools.registry import registry


def _call(name, path, task_id, **kwargs):
    return json.loads(registry.dispatch(
        name, {"path": str(path), **kwargs}, task_id=task_id))


@pytest.mark.parametrize("condition, expected", [
    ("unstable", "unstable read snapshot"),
    ("redacted", "redacted content"),
    ("budget", "character budget truncation"),
])
def test_full_read_refusal_names_actual_reason(tmp_path, condition, expected):
    path = tmp_path / f"{condition}.txt"
    original = "first\nsecond\nthird\n"
    path.write_text(original, encoding="utf-8")
    task_id = f"read-reason-{condition}"
    try:
        if condition == "unstable":
            # The file still renders fully, but snapshot metadata is unavailable.
            with patch("tools.file_tools._file_metadata", return_value=None):
                read = _call("read_file", path, task_id)
        elif condition == "redacted":
            with patch("tools.file_tools.redact_sensitive_text",
                       side_effect=lambda value, **_: value.replace("second", "[redacted]")):
                read = _call("read_file", path, task_id)
        else:
            with patch("tools.file_tools._get_max_read_chars", return_value=10):
                read = _call("read_file", path, task_id)

        assert "error" not in read, read
        if condition == "budget":
            assert read.get("truncated_by") == "bytes", read
            assert not read.get("truncated_lines"), read
        else:
            assert not read.get("truncated"), read
            assert not read.get("next_offset"), read

        refused = _call("write_file", path, task_id, content="replacement\n")
        assert refused.get("stale_write_blocked") is True, refused
        assert expected in refused["error"], refused
        assert "was last read with offset/limit pagination" not in refused["error"]
        assert path.read_text(encoding="utf-8") == original
    finally:
        clear_file_ops_cache(task_id)


def test_actual_pagination_still_identifies_remaining_pages(tmp_path):
    path = tmp_path / "paged.txt"
    path.write_text("first\nsecond\nthird\n", encoding="utf-8")
    task_id = "read-reason-paged"
    try:
        read = _call("read_file", path, task_id, offset=2, limit=1)
        assert "error" not in read, read
        refused = _call("write_file", path, task_id, content="replacement\n")
        assert refused.get("stale_write_blocked"), refused
        assert "offset/limit pagination" in refused["error"], refused
        assert path.read_text(encoding="utf-8") == "first\nsecond\nthird\n"
    finally:
        clear_file_ops_cache(task_id)
