"""HCMP: a configured engine must not silently become the stock 500k compressor.

Drive a complete tool turn with DirectSDK-shaped cached usage and a real
user-engine import. A long plugin preamble previously hid the engine contract
from discovery, so the post-tool trigger missed the plugin's 180k cap.
"""

from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from hermes_state import SessionDB
from run_agent import AIAgent


_ENGINE = dedent('''
    from agent.context_compressor import ContextCompressor

    class Capped(ContextCompressor):
        @property
        def name(self):
            return "midturn_cap"

    def register(ctx):
        ctx.register_context_engine(Capped(
            model="", threshold_percent=0.85, threshold_tokens_cap=180_000,
            protect_first_n=1, protect_last_n=2, quiet_mode=True,
        ))
''')


def _response(*, tool, prompt_tokens):
    calls = [SimpleNamespace(
        id="call_cap", type="function",
        function=SimpleNamespace(name="web_search", arguments='{"query":"cap"}'),
    )] if tool else None
    # The DirectSDK adapter reports total prompt tokens including both cache buckets.
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=1, total_tokens=prompt_tokens + 1,
        prompt_tokens_details=SimpleNamespace(cached_tokens=prompt_tokens - 2_000),
        cache_creation_input_tokens=1_000,
    )
    return SimpleNamespace(
        model="claude-test", usage=usage,
        choices=[SimpleNamespace(
            finish_reason="tool_calls" if tool else "stop",
            message=SimpleNamespace(
                content=None if tool else "done", reasoning=None,
                reasoning_content=None, tool_calls=calls,
            ),
        )],
    )


@pytest.mark.parametrize("platform", ["cli", "web"])
@pytest.mark.parametrize("preamble_chars", [0, 9_000], ids=["short", "long-preamble"])
def test_named_engine_compacts_at_cap_midturn(tmp_path, monkeypatch, platform, preamble_chars):
    home = tmp_path / "home"
    plugin = home / "plugins" / "midturn_cap"
    plugin.mkdir(parents=True)
    (plugin / "__init__.py").write_text('"""' + "x" * preamble_chars + '"""\n' + _ENGINE)
    (home / "config.yaml").write_text(
        "model:\n  context_length: 1000000\n"
        "context:\n  engine: midturn_cap\n"
        "compression:\n  enabled: true\n  threshold: 0.5\n  in_place: true\n"
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    db = SessionDB(db_path=home / "state.db")
    tool_def = {"type": "function", "function": {
        "name": "web_search", "description": "Search",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
    }}
    with (
        patch("model_tools.get_tool_definitions", return_value=[tool_def]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
        patch("agent.model_metadata.get_model_context_length", return_value=1_000_000),
        patch("agent.context_compressor.get_model_context_length", return_value=1_000_000),
    ):
        agent = AIAgent(
            api_key="test-only", base_url="http://localhost:1/v1", provider="custom",
            model="claude-test", platform=platform, quiet_mode=True,
            skip_memory=True, skip_context_files=True, max_iterations=4,
            session_db=db, session_id="midturn-cap",
        )
    agent.provider = "claude-subscription-directsdk-experimental"
    agent.client = MagicMock()
    agent._cached_system_prompt = "System"
    agent._disable_streaming = True
    agent._use_prompt_caching = False
    agent._compression_feasibility_checked = True
    agent.tool_delay = 0
    agent.save_trajectories = False
    compactions = []

    def compact(messages, system_message, **kwargs):
        compactions.append(kwargs)
        agent.context_compressor.awaiting_real_usage_after_compression = True
        agent.context_compressor._verify_compaction_cleared_threshold = True
        agent.context_compressor.last_prompt_tokens = -1
        from agent.usage_anchor import set_usage_anchor
        set_usage_anchor(agent, None)
        return list(messages), "System"

    request_compaction_counts = []

    def provider_call(**kwargs):
        request_compaction_counts.append(len(compactions))
        if agent.client.chat.completions.create.call_count == 1:
            return _response(tool=True, prompt_tokens=180_001)
        return _response(tool=False, prompt_tokens=10_000)

    agent.client.chat.completions.create.side_effect = provider_call
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"history {i}"}
        for i in range(30)
    ]
    try:
        with (
            patch.object(agent, "_compress_context", side_effect=compact),
            patch("model_tools.handle_function_call", return_value='{"result":"ok"}'),
            patch.object(agent, "_save_trajectory"),
            patch.object(agent, "_cleanup_task_resources"),
        ):
            result = agent.run_conversation("search then finish", conversation_history=history)
        assert result["final_response"] == "done", result
        assert request_compaction_counts == [0, 1], "180k cap missed before the next provider request"
        assert len(compactions) == 1
        assert compactions[0]["trigger"] == "post_tool"
        assert 180_000 <= compactions[0]["approx_tokens"] < 190_000
        assert agent.context_compressor.threshold_tokens == 180_000
        assert agent.context_compressor.last_prompt_tokens == 10_000
        assert not agent.context_compressor.awaiting_real_usage_after_compression
        assert agent.client.chat.completions.create.call_count == 2
    finally:
        db.close()
