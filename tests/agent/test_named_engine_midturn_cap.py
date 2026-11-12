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


@pytest.mark.parametrize("cycles", [1, 2], ids=["first-crossing", "rearmed-crossing"])
@pytest.mark.parametrize("mode", ["simulated", "committed", "streamed-committed"])
@pytest.mark.parametrize("platform", ["cli", "web"])
@pytest.mark.parametrize("preamble_chars", [0, 9_000], ids=["short", "long-preamble"])
def test_named_engine_compacts_at_cap_midturn(tmp_path, monkeypatch, platform, preamble_chars, mode, cycles):
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
    agent._disable_streaming = mode != "streamed-committed"
    agent.stream_delta_callback = lambda _text: None
    agent._use_prompt_caching = False
    agent._compression_feasibility_checked = True
    agent.tool_delay = 0
    agent.save_trajectories = False
    agent.max_compression_attempts = 1
    compactions = []
    real_compact = agent._compress_context

    def compact(messages, system_message, **kwargs):
        compactions.append(kwargs)
        if mode != "simulated":
            return real_compact(messages, system_message, **kwargs)
        agent.context_compressor.awaiting_real_usage_after_compression = True
        agent.context_compressor._verify_compaction_cleared_threshold = True
        agent.context_compressor.last_prompt_tokens = -1
        from agent.usage_anchor import set_usage_anchor
        set_usage_anchor(agent, None)
        return list(messages), "System"

    request_compaction_counts = []

    def provider_call(**kwargs):
        request_compaction_counts.append(len(compactions))
        call_number = agent.client.chat.completions.create.call_count
        response = _response(
            tool=call_number < cycles * 2,
            prompt_tokens=180_001 if call_number % 2 else 10_000,
        )
        for call in response.choices[0].message.tool_calls or []:
            call.id = f"call_cap_{call_number}"
        if mode == "streamed-committed":
            message = response.choices[0].message
            delta = SimpleNamespace(
                role="assistant", content=message.content, reasoning_content=None,
                tool_calls=[SimpleNamespace(index=i, **vars(call))
                            for i, call in enumerate(message.tool_calls or [])] or None,
            )
            return iter([SimpleNamespace(
                id="claude-native", model=response.model, usage=response.usage,
                choices=[SimpleNamespace(delta=delta, finish_reason=response.choices[0].finish_reason)],
            )])
        return response

    agent.client.chat.completions.create.side_effect = provider_call
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"history {i} " * 100}
        for i in range(30)
    ]
    try:
        with (
            patch.object(agent, "_compress_context", side_effect=compact),
            patch.object(agent.context_compressor, "_generate_summary", return_value="Prior work is complete."),
            patch.object(agent, "_build_system_prompt", return_value="System"),
            patch("model_tools.handle_function_call", return_value='{"result":"ok"}'),
            patch.object(agent, "_save_trajectory"),
            patch.object(agent, "_cleanup_task_resources"),
        ):
            result = agent.run_conversation("search then finish", conversation_history=history)
        assert result["final_response"] == "done", result
        assert request_compaction_counts == [(i + 1) // 2 for i in range(cycles * 2)], (
            "180k cap missed before the next provider request"
        )
        assert len(compactions) == cycles
        assert all(call["trigger"] == "post_tool" for call in compactions)
        assert all(180_000 <= call["approx_tokens"] < 190_000 for call in compactions)
        assert agent.context_compressor.threshold_tokens == 180_000
        assert agent.context_compressor.last_prompt_tokens == 10_000
        assert not agent.context_compressor.awaiting_real_usage_after_compression
        assert agent.client.chat.completions.create.call_count == cycles * 2
        if mode != "simulated":
            assert agent.context_compressor.compression_count == cycles
            assert agent.session_id == "midturn-cap"
            assert any(not row["active"] for row in db.get_messages(agent.session_id, include_inactive=True))
            reloaded = db.get_messages_as_conversation(agent.session_id)
            assert len(reloaded) < len(history)
            assert any("Prior work is complete." in str(row.get("content")) for row in reloaded)
    finally:
        db.close()
