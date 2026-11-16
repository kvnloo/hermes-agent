"""Tests for AIAgent._repair_tool_call — tool-name normalization.

Regression guard for #14784: Claude-style models sometimes emit
class-like tool-call names (``TodoTool_tool``, ``Patch_tool``,
``BrowserClick_tool``, ``PatchTool``). Before the fix they returned
"Unknown tool" even though the target tool was registered under a
snake_case name. The repair routine now normalizes CamelCase,
strips trailing ``_tool`` / ``-tool`` / ``tool`` suffixes (up to
twice to handle double-tacked suffixes like ``TodoTool_tool``), and
falls back to fuzzy match.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


VALID = {
    "todo",
    "patch",
    "browser_click",
    "browser_navigate",
    "web_search",
    "read_file",
    "write_file",
    "terminal",
    "execute_code",
    "session_search",
}


@pytest.fixture
def repair():
    """Bind the real helper without importing AIAgent's bootstrap and home I/O."""
    from agent.agent_runtime_helpers import repair_tool_call

    stub = SimpleNamespace(valid_tool_names=VALID)
    return repair_tool_call.__get__(stub)


class TestExistingBehaviorStillWorks:
    """Pre-existing repairs must keep working (no regressions)."""

    def test_lowercase_already_matches(self, repair):
        assert repair("browser_click") == "browser_click"







class TestClassLikeEmissions:
    """Regression coverage for #14784 — CamelCase + _tool suffix variants."""

    def test_camel_case_no_suffix(self, repair):
        assert repair("BrowserClick") == "browser_click"









class TestEdgeCases:
    """Edge inputs that must not crash or produce surprising results."""

    def test_empty_string(self, repair):
        assert repair("") is None





class TestVolcEngineXmlPollution:
    """Regression coverage for #33007 — VolcEngine ``api/plan`` endpoint
    leaks raw XML attribute fragments into ``tool_use.name``.

    Observed in production with the ``anthropic_messages`` API mode:

        terminal" parameter="command" string="true
        execute_code" parameter="code" string="true
        session_search" parameter="session_id" string="true

    The fix trims at the first ``"``/``'``/``<``/``>`` so the rest of
    the repair pipeline can resolve the cleaned name to a real tool.
    """

    def test_terminal_with_xml_attribute_pollution(self, repair):
        # Exact pattern from the bug report (terminal call).
        polluted = 'terminal" parameter="command" string="true'
        assert repair(polluted) == "terminal"




    def test_tool_name_with_trailing_quote_only(self, repair):
        # Minimal leak — just a stray trailing quote, no full attribute.
        assert repair('terminal"') == "terminal"



    def test_clean_tool_name_unaffected_by_sanitizer(self, repair):
        # Pure passthrough — no XML/quote chars, no change.
        assert repair("execute_code") == "execute_code"
        assert repair("session_search") == "session_search"

    def test_space_separated_name_still_normalizes(self, repair):
        # Critical: the XML strip must NOT consume whitespace, or the
        # legitimate ``"write file" -> write_file`` repair path breaks.
        assert repair("write file") == "write_file"


    def test_leading_quote_falls_through_to_fuzzy_match(self, repair):
        # Sanitizer only trims when the XML char is at idx > 0 — a
        # name that *starts* with a quote is left untouched so the
        # rest of the pipeline (fuzzy match at 0.7 cutoff) can still
        # recover the obvious target.
        assert repair('"terminal"') == "terminal"


class TestAnthropicOAuthContextEngineNames:
    """#149710: OAuth wire names must resolve tools injected only into this agent."""

    @pytest.mark.parametrize("tool_name", ["notes", "history"])
    def test_prefixed_agent_local_tool_resolves(self, tool_name):
        from agent.agent_runtime_helpers import repair_tool_call

        agent = SimpleNamespace(valid_tool_names={tool_name})
        assert repair_tool_call(agent, f"mcp__{tool_name}") == tool_name

    def test_native_wire_name_keeps_precedence(self):
        from agent.agent_runtime_helpers import repair_tool_call

        agent = SimpleNamespace(valid_tool_names={"notes", "mcp__notes"})
        assert repair_tool_call(agent, "mcp__notes") == "mcp__notes"

    def test_agent_local_tool_survives_oauth_round_trip(self):
        from agent.agent_runtime_helpers import repair_tool_call
        from agent.transports.anthropic import AnthropicTransport
        from tools.registry import registry

        assert registry.get_entry("notes") is None
        transport = AnthropicTransport()
        request = transport.build_kwargs(
            model="claude-sonnet-4-6",
            messages=[{"role": "user", "content": "Read my notes"}],
            tools=[{"type": "function", "function": {
                "name": "notes", "description": "Read context-engine notes",
                "parameters": {"type": "object", "properties": {}},
            }}],
            is_oauth=True,
        )
        wire_name = request["tools"][0]["name"]
        assert wire_name == "mcp__notes"
        response = SimpleNamespace(
            content=[SimpleNamespace(type="tool_use", id="call_notes", name=wire_name, input={})],
            stop_reason="tool_use",
        )
        normalized = transport.normalize_response(response, strip_tool_prefix=True)
        call = normalized.tool_calls[0]
        assert call.id == "call_notes"
        assert call.arguments == "{}"
        agent = SimpleNamespace(valid_tool_names={"notes"})
        assert repair_tool_call(agent, call.name) == "notes"
