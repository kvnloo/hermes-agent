"""Tests for acp_adapter.tools — tool kind mapping and ACP content building."""


import json

import pytest

from acp_adapter.edit_approval import EditProposal
from acp_adapter.tools import (
    build_tool_complete,
    build_tool_start,
    build_tool_title,
    extract_locations,
    get_tool_kind,
    make_tool_call_id,
)
from acp.schema import (
    FileEditToolCallContent,
    ContentToolCallContent,
    ToolCallLocation,
    ToolCallStart,
    ToolCallProgress,
)


# ---------------------------------------------------------------------------
# TOOL_KIND_MAP coverage
# ---------------------------------------------------------------------------


COMMON_HERMES_TOOLS = ["read_file", "search_files", "terminal", "patch", "write_file", "process"]


class TestToolKindMap:










    def test_unknown_tool_returns_other_kind(self):
        assert get_tool_kind("nonexistent_tool_xyz") == "other"


# ---------------------------------------------------------------------------
# make_tool_call_id
# ---------------------------------------------------------------------------


class TestMakeToolCallId:


    def test_ids_are_unique(self):
        ids = {make_tool_call_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# build_tool_title
# ---------------------------------------------------------------------------


class TestBuildToolTitle:

    def test_terminal_title_truncates_long_command(self):
        long_cmd = "x" * 200
        title = build_tool_title("terminal", {"command": long_cmd})
        assert len(title) < 120
        assert "..." in title





    def test_unknown_tool_uses_name(self):
        title = build_tool_title("some_new_tool", {"foo": "bar"})
        assert title == "some_new_tool"

    @pytest.mark.parametrize(
        "tool_name, args",
        [
            ("terminal", {"command": "git status --short"}),
            ("read_file", {"path": "/etc/hosts", "offset": 10}),
            ("search_files", {"pattern": "TODO", "path": "src"}),
            ("web_search", {"query": "hermes agent acp"}),
            ("execute_code", {"code": "\nfrom hermes_tools import terminal\nprint('done')"}),
            ("skill_view", {"name": "github", "file_path": "references/x.md"}),
        ],
    )
    def test_title_derives_from_display_preview(self, tool_name, args):
        """ACP titles are the shared agent.display preview, not a parallel per-tool table."""
        from agent.display import build_tool_preview

        assert build_tool_preview(tool_name, args, max_len=80) in build_tool_title(tool_name, args)


# ---------------------------------------------------------------------------
# build_tool_start
# ---------------------------------------------------------------------------


class TestBuildToolStart:
    def test_build_tool_start_for_patch(self):
        """patch start should not duplicate the edit-approval diff."""
        args = {
            "path": "src/main.py",
            "old_string": "print('hello')",
            "new_string": "print('world')",
        }
        result = build_tool_start("tc-1", "patch", args)
        assert isinstance(result, ToolCallStart)
        assert result.kind == "edit"
        assert len(result.content) >= 1
        item = result.content[0]
        assert isinstance(item, ContentToolCallContent)
        assert "src/main.py" in item.content.text


    def test_auto_approved_edit_start_shows_diff_content(self):
        """Auto-approved edit starts need the diff because no approval card exists."""
        args = {"path": "/tmp/acp.txt", "old_string": "old", "new_string": "new"}
        result = build_tool_start(
            "tc-auto-edit",
            "patch",
            args,
            edit_diff=EditProposal("patch", "/tmp/acp.txt", "old\n", "new\n", args),
        )

        assert isinstance(result, ToolCallStart)
        assert result.kind == "edit"
        assert len(result.content) == 1
        item = result.content[0]
        assert isinstance(item, FileEditToolCallContent)
        assert item.path == "/tmp/acp.txt"
        assert item.old_text == "old\n"
        assert item.new_text == "new\n"







    def test_build_tool_start_for_browser_navigate(self):
        """browser_navigate should emit a polished start event."""
        args = {"url": "https://x.com"}
        result = build_tool_start("tc-browser-start", "browser_navigate", args)
        assert isinstance(result, ToolCallStart)
        assert "https://x.com" in result.title
        assert result.kind == "fetch"
        assert "https://x.com" in result.content[0].content.text
        assert result.raw_input is None








# ---------------------------------------------------------------------------
# build_tool_complete
# ---------------------------------------------------------------------------


class TestBuildToolComplete:
    def test_build_tool_complete_for_terminal(self):
        """Completed terminal call should include output text."""
        result = build_tool_complete("tc-2", "terminal", "total 42\ndrwxr-xr-x 2 root root 4096 ...")
        assert isinstance(result, ToolCallProgress)
        assert result.status == "completed"
        assert len(result.content) >= 1
        content_item = result.content[0]
        assert isinstance(content_item, ContentToolCallContent)
        assert "total 42" in content_item.content.text
        assert result.raw_output is None








    def test_build_tool_complete_marks_returncode_nonzero_as_failed(self):
        result = build_tool_complete("tc-fail", "execute_code", '{"output": "bad", "returncode": 2}')
        assert result.status == "failed"








    def test_build_tool_complete_for_search_files_formats_matches(self):
        result = build_tool_complete(
            "tc-search",
            "search_files",
            '{"total_count":2,"matches":[{"path":"README.md","line":3,"content":"TODO: fix this"},{"path":"src/app.py","line":9,"content":"needle"}],"truncated":true}\n\n[Hint: Results truncated. Use offset=12 to see more.]',
        )
        text = result.content[0].content.text
        assert "README.md:3" in text
        assert "TODO: fix this" in text
        assert "Results truncated" in text
        assert result.raw_output is None







    def test_build_tool_complete_generically_formats_unknown_json_dict_without_raw_output(self):
        result = build_tool_complete(
            "tc-recall-search",
            "memory_archive_search",
            '{"results":[{"id":"obs-1","status":"active","content":"Recall should render as a readable summary."}],"trust":"lower-trust archive evidence"}',
        )
        text = result.content[0].content.text
        assert "lower-trust archive evidence" in text
        assert "Recall should render as a readable summary" in text
        assert "{\"results\"" not in text
        assert result.raw_output is None

    def test_build_tool_complete_forwards_an_mcp_servers_own_result_as_raw_output(self):
        # What T3's html_render returns through Hermes' MCP handler: the display stays a summary, and
        # rawOutput carries the server's text so the client can mount the board.
        inner = '{"htmlRender":{"attachmentId":"t-1-html","title":"/stats","height":1100}}'
        result = build_tool_complete(
            "tc-render", "mcp__editor_t3_code_b9248901__html_render", json.dumps({"result": inner}),
        )
        assert result.raw_output == {"content": [{"type": "text", "text": inner}]}
        assert "htmlRender" in result.content[0].content.text
        structured = build_tool_complete(
            "tc-app", "mcp__srv__tool", json.dumps({"result": "ok", "structuredContent": {"n": 1}}),
        )
        assert structured.raw_output == {"content": [{"type": "text", "text": "ok"}], "structuredContent": {"n": 1}}

    @pytest.mark.parametrize("tool_name,payload", [
        ("mcp__srv__tool", '{"error": "MCP tool returned an error"}'),
        ("mcp__srv__tool", '{"result": {"not": "text"}}'),
        ("memory_archive_search", '{"result": "x"}'),
    ])
    def test_build_tool_complete_keeps_errors_and_non_mcp_results_out_of_raw_output(self, tool_name, payload):
        assert build_tool_complete("tc", tool_name, payload).raw_output is None

    def test_mcp_calls_name_their_server_and_an_editor_lent_server_by_the_editors_name(self):
        # T3 recognises its own tools (and mounts html_render boards) by _meta.serverId = t3_code.
        start = build_tool_start("tc", "mcp__editor_t3_code_b9248901__html_render", {"html": "<p>x</p>"})
        assert start.field_meta == {"serverId": "t3_code", "toolName": "html_render"}
        done = build_tool_complete("tc", "mcp__editor_t3_code_b9248901__html_render", '{"result": "{}"}')
        assert done.field_meta == {"serverId": "t3_code", "toolName": "html_render"}
        assert build_tool_start("tc", "mcp__github__create_issue", {}).field_meta == {
            "serverId": "github", "toolName": "create_issue"}
        assert build_tool_start("tc", "terminal", {"command": "ls"}).field_meta is None
        assert "_meta" not in build_tool_complete("tc", "terminal", "ok").model_dump(by_alias=True, exclude_none=True)









# ---------------------------------------------------------------------------
# extract_locations
# ---------------------------------------------------------------------------


class TestExtractLocations:
    def test_extract_locations_with_path(self):
        args = {"path": "src/app.py", "offset": 42}
        locs = extract_locations(args)
        assert len(locs) == 1
        assert isinstance(locs[0], ToolCallLocation)
        assert locs[0].path == "src/app.py"
        assert locs[0].line == 42

    def test_extract_locations_without_path(self):
        args = {"command": "echo hi"}
        locs = extract_locations(args)
        assert locs == []
