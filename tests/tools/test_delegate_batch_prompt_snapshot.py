"""Batch child prompts keep one workspace context snapshot across construction."""
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from tools.delegate_tool import _build_children


class TestBatchPromptSnapshot(unittest.TestCase):
    def test_workspace_rules_do_not_drift_during_construction(self):
        """Two children must share the rules read before AGENTS.md changes."""
        with TemporaryDirectory() as directory:
            rules = Path(directory) / "AGENTS.md"
            rules.write_text("VERSION_ONE: shared rule. CONTEXT: appears in AGENTS.md.\n", encoding="utf-8")
            parent = MagicMock()
            parent.base_url = "https://openrouter.ai/api/v1"
            parent.api_key = "test-key"
            parent.provider = "openrouter"
            parent.api_mode = "chat_completions"
            parent.model = "test-model"
            parent.platform = "cli"
            parent.providers_allowed = None
            parent.providers_ignored = None
            parent.providers_order = None
            parent.provider_sort = None
            parent._session_db = None
            parent._delegate_depth = 0
            parent._active_children = []
            parent._active_children_lock = threading.Lock()
            parent._print_fn = None
            parent.tool_progress_callback = None
            parent.thinking_callback = None

            prompts = []

            def make_child(**kwargs):
                prompts.append(kwargs["ephemeral_system_prompt"])
                if len(prompts) == 1:
                    rules.write_text("VERSION_TWO: changed during batch construction.\n", encoding="utf-8")
                return MagicMock()

            creds = {"provider": None, "base_url": None, "api_key": None, "api_mode": None, "model": None}
            tasks = [
                {"goal": "Task A", "context": "per-child alpha"},
                {"goal": "Task B", "context": "per-child beta"},
            ]
            with (
                patch("run_agent.AIAgent", side_effect=make_child),
                patch("tools.delegate_tool._resolve_workspace_hint", return_value=directory),
            ):
                children, error = _build_children(
                    tasks, [None, None], creds, top_role="leaf", max_iterations=3,
                    parent_agent=parent, routing_cfg={}, live_deleg_id=None, live_writers=[],
                )

        self.assertIsNone(error)
        self.assertEqual(len(children), 2)
        self.assertEqual(len(prompts), 2)
        prefix_a, context_a = prompts[0].rsplit("\n\nCONTEXT:\n", 1)
        prefix_b, context_b = prompts[1].rsplit("\n\nCONTEXT:\n", 1)
        self.assertEqual(prefix_a, prefix_b)
        self.assertIn("VERSION_ONE", prefix_a)
        self.assertIn("CONTEXT: appears in AGENTS.md", prefix_a)
        self.assertNotIn("VERSION_TWO", prefix_b)
        self.assertEqual(context_a, "per-child alpha")
        self.assertEqual(context_b, "per-child beta")
        self.assertNotIn("Task A", prompts[0])
        self.assertNotIn("Task B", prompts[1])
