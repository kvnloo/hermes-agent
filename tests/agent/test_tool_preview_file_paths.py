"""File-edit previews distinguish long paths (NousResearch/hermes-agent#150135)."""

import pytest

from agent.display import build_tool_preview, prepare_tool_preview


@pytest.mark.parametrize("tool_name", ["write_file", "patch"])
def test_long_path_file_edits_remain_distinct_in_compact_rows(tool_name: str) -> None:
    directory = "/Users/danielgindin/.hermes/profiles/red/cache/scratch"
    names = ("omlx_write_path_check.py", "apply_thinking_budget.py")
    paths = [f"{directory}/{name}" for name in names]

    previews = [
        build_tool_preview(tool_name, {"path": path}, max_len=48)
        for path in paths
    ]
    assert previews[0].startswith(names[0])
    assert previews[1].startswith(names[1])
    assert previews[0] != previews[1]

    rows = [
        prepare_tool_preview(tool_name, {"path": path}, fallback=tool_name, max_len=48)
        for path in paths
    ]
    assert [row.text for row in rows] == previews
    assert all(row.truncated for row in rows)
    assert directory in build_tool_preview(tool_name, {"path": paths[0]}, max_len=0)
