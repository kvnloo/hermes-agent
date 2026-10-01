"""Factory-only port of NousResearch/hermes-agent#53806's own tests, with two drift adaptations (marked).

Same as chs_c53806_own_tests.py (verbatim port of compression commit e560abd758), minus the agent-init
test (its agent/agent_init.py hunk is not in the hand-port), with the two DRIFT ADAPTATION edits below.

The two test methods below come from that commit's hunk in
tests/run_agent/test_compression_boundary_hook.py; main moved that file to
tests/agent/test_compression_boundary_hook.py, where the hunk no longer applies textually.
``_make_agent`` is copied from main's tests/agent/test_compression_boundary_hook.py (same helper
the carrier's hunk extended). Not part of any commit offered upstream.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestCarrier53806OwnTestsAdapted:
    def _make_agent(self, session_db):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            from run_agent import AIAgent
            agent = AIAgent(
                api_key="test-key",
                base_url="https://openrouter.ai/api/v1",
                model="test/model",
                quiet_mode=True,
                session_db=session_db,
                session_id="original-session",
                skip_context_files=True,
                skip_memory=True,
            )
            # ROTATION fallback — pin in_place=False regardless of default (#38763).
            agent.compression_in_place = False
            return agent

    def test_pre_context_compression_plugin_hook_fires_before_compress(self):
        """Plugins can persist task-state before compression drops middle turns."""
        from hermes_state import SessionDB

        with tempfile.TemporaryDirectory() as tmpdir:
            db = SessionDB(db_path=Path(tmpdir) / "test.db")
            agent = self._make_agent(db)
            compressor = MagicMock()
            compressor.compress.return_value = [{"role": "user", "content": "summary"}]
            compressor.compression_count = 1
            compressor.last_prompt_tokens = 0
            compressor.last_completion_tokens = 0
            compressor._last_summary_error = None
            compressor._last_compress_aborted = False
            agent.context_compressor = compressor
            messages = [{"role": "user", "content": "important task context"}]

            with patch("hermes_cli.plugins.invoke_hook") as invoke_hook:
                agent._compress_context(messages, "sys", approx_tokens=123, task_id="task-1")

            pre_calls = [
                c for c in invoke_hook.call_args_list
                if c.args and c.args[0] == "pre_context_compression"
            ]
            assert pre_calls, f"pre_context_compression hook did not fire: {invoke_hook.call_args_list!r}"
            call = pre_calls[0]
            assert call.kwargs["session_id"] == "original-session"
            assert call.kwargs["task_id"] == "task-1"
            assert call.kwargs["approx_tokens"] == 123
            # DRIFT ADAPTATION: main hands the hook the transcript with the session store's row metadata
            # attached (_db_persisted, _row_id, message_uid, timestamp, _db_row_snapshot); compare role/content.
            assert [(m["role"], m["content"]) for m in call.kwargs["conversation_history"]] == [
                (m["role"], m["content"]) for m in messages
            ]

    def test_plugin_on_session_start_called_with_compression_boundary(self):
        """Generic plugins get the same compression boundary signal as context engines."""
        from hermes_state import SessionDB

        with tempfile.TemporaryDirectory() as tmpdir:
            db = SessionDB(db_path=Path(tmpdir) / "test.db")
            agent = self._make_agent(db)
            compressor = MagicMock()
            compressor.compress.return_value = [{"role": "user", "content": "summary"}]
            compressor.compression_count = 1
            compressor.last_prompt_tokens = 0
            compressor.last_completion_tokens = 0
            compressor._last_summary_error = None
            compressor._last_compress_aborted = False
            agent.context_compressor = compressor
            original_sid = agent.session_id

            with patch("hermes_cli.plugins.invoke_hook") as invoke_hook:
                # DRIFT ADAPTATION: a 1-message compaction no longer commits on main; 10 messages, as in
                # main's own test_on_session_start_called_with_compression_boundary.
                agent._compress_context([{"role": "user", "content": f"m{i}"} for i in range(10)], "sys", approx_tokens=100)

            start_calls = [
                c for c in invoke_hook.call_args_list
                if c.args and c.args[0] == "on_session_start"
                and c.kwargs.get("boundary_reason") == "compression"
            ]
            assert start_calls, f"plugin on_session_start compression boundary did not fire: {invoke_hook.call_args_list!r}"
            call = start_calls[-1]
            assert call.kwargs["session_id"] == agent.session_id
            assert call.kwargs["old_session_id"] == original_sid
