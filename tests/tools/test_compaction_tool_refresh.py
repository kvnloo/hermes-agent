"""Compaction rebuilds dynamic tool schemas (forever-session fix, #95681 arc).

Forever-sessions (Bot Mode, gateway channels) never restart; compaction is
the only boundary where the prompt cache is already broken, so it is the
one sanctioned point for a tool-snapshot rebuild. These tests pin:
- the production compaction refresh publishes schema edits under a stable name
- preserve_prefix=True keeps the schema already sent (between-turns refresh)
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class _Agent:
    quiet_mode = True
    enabled_toolsets = ["image_gen"]
    disabled_toolsets = None


def _defs(desc):
    return [{"type": "function", "function": {
        "name": "image_generate", "description": desc,
        "parameters": {"type": "object", "properties": {}},
    }}]


class TestToolSnapshotRefresh(unittest.TestCase):
    def _agent_with(self, desc):
        agent = _Agent()
        agent.tools = _defs(desc)
        agent.valid_tool_names = {"image_generate"}
        agent._tool_snapshot_generation = 0
        return agent

    def _refresh(self, agent, new_desc, **kw):
        from agent.conversation_compression import _refresh_agent_tool_definitions
        from tools.mcp_tool_agent import refresh_agent_mcp_tools

        with patch("model_tools.get_tool_definitions",
                   return_value=_defs(new_desc)), \
             patch("tools.mcp_tool_agent._reinject_post_build_tools",
                   return_value=set()):
            if kw.pop("compaction", False):
                return _refresh_agent_tool_definitions(agent)
            return refresh_agent_mcp_tools(agent, **kw)

    def test_compaction_publishes_same_name_schema_edit(self):
        agent = self._agent_with("old capabilities text")
        self._refresh(agent, "new capabilities text", compaction=True)
        self.assertIn("new capabilities",
                      agent.tools[0]["function"]["description"])

    def test_content_change_ignored_when_prefix_preserved(self):
        """Between-turns refresh keeps the schema already sent."""
        agent = self._agent_with("old capabilities text")
        self._refresh(agent, "new capabilities text", preserve_prefix=True)
        self.assertIn("old capabilities",
                      agent.tools[0]["function"]["description"])

    def test_identical_content_keeps_identity(self):
        agent = self._agent_with("same text")
        before = agent.tools
        self._refresh(agent, "same text", compaction=True)
        self.assertIs(agent.tools, before)




if __name__ == "__main__":
    unittest.main()
