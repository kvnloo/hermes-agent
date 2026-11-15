"""Tests for acp_adapter.tools — tool kind mapping and ACP content building."""


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







    @pytest.mark.parametrize(
        "tool_name, args",
        [
            ("browser_exec", {"code": "print('hello')"}),
            ("browser_cdp", {"method": "Page.enable"}),
            ("browser_dialog", {"action": "accept"}),
            ("browser_vault", {"action": "list"}),
        ],
    )
    def test_browser_tools_start_as_execute(self, tool_name, args):
        event = build_tool_start("tc-browser-start", tool_name, args)
        assert isinstance(event, ToolCallStart)
        assert event.kind == "execute"
        assert event.raw_input is None


# ---------------------------------------------------------------------------
# build_tool_complete
# ---------------------------------------------------------------------------


class TestBuildToolComplete:
    def test_browser_exec_completion_keeps_stdout_and_failure_details(self):
        success = build_tool_complete(
            "tc-browser", "browser_exec",
            '{"success":true,"exit_code":0,"output":"Page title: Example","workspace":"/tmp/browser"}',
        )
        assert success.kind == "execute"
        assert success.status == "completed"
        assert "Page title: Example" in success.content[0].content.text
        assert "Workspace: /tmp/browser" in success.content[0].content.text
        assert "**output:**" not in success.content[0].content.text
        assert success.raw_output is None

        failure = build_tool_complete(
            "tc-browser-failed", "browser_exec",
            '{"success":false,"exit_code":1,"output":"Traceback","stderr":"SyntaxError: bad code"}',
        )
        assert failure.kind == "execute"
        assert failure.status == "failed"
        assert "Traceback" in failure.content[0].content.text
        assert "SyntaxError: bad code" in failure.content[0].content.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("success", [True, False])
    async def test_browser_exec_live_and_replayed_updates_keep_output(self, success):
        """Browser results survive live projection, replay, and ACP JSON serialization."""
        import json
        from unittest.mock import AsyncMock

        from acp_adapter.gateway_server import GatewayACPAgent
        from acp_adapter.server import _history_replay_updates

        args = {"code": "print('Page title: Example')"}
        payload = {
            "success": success,
            "exit_code": 0 if success else 1,
            "output": "Page title: Example" if success else "Traceback",
            "workspace": "/tmp/browser",
            "screenshot_path": "/tmp/browser/screen.png",
        }
        if not success:
            payload["stderr"] = "SyntaxError: bad code"
        result = json.dumps(payload)
        agent = GatewayACPAgent()
        agent._snapshots["s"] = {}
        agent._gateway = AsyncMock()
        agent._conn = AsyncMock()
        for event_type, extra in (
            ("tool.start", {}),
            ("tool.complete", {"result": result, "is_error": not success}),
        ):
            await agent._project({
                "session_id": "s", "admission_id": "a", "type": event_type,
                "payload": {"tool_call_id": "browser-1", "tool_name": "browser_exec", "args": args, **extra},
            })
        live = [call.kwargs["update"] for call in agent._conn.session_update.await_args_list]
        replay = list(_history_replay_updates([
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "browser-1", "type": "function",
                "function": {"name": "browser_exec", "arguments": json.dumps(args)},
            }]},
            {"role": "tool", "tool_call_id": "browser-1", "tool_name": "browser_exec", "content": result},
        ]))
        assert [type(update) for update in live] == [ToolCallStart, ToolCallProgress]
        assert [update.model_dump(by_alias=True, exclude_none=True) for update in live] == [
            update.model_dump(by_alias=True, exclude_none=True) for update in replay
        ]
        start, complete = [type(update).model_validate_json(update.model_dump_json(by_alias=True)) for update in live]
        assert start.kind == complete.kind == "execute"
        assert start.raw_input is complete.raw_output is None
        assert complete.status == ("completed" if success else "failed")
        text = complete.content[0].content.text
        for expected in (payload["output"], "Workspace: /tmp/browser", "Screenshot: /tmp/browser/screen.png"):
            assert expected in text
        if not success:
            assert "stderr: SyntaxError: bad code" in text
            assert "browser_exec failed (exit 1)" in text

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
