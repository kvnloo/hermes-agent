from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch
import json
import sys

from run_agent import AIAgent

def _mock_response(*, usage: dict, content: str = "done"):
    msg = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=msg, finish_reason="stop")
    return SimpleNamespace(
        choices=[choice],
        model="test/model",
        usage=SimpleNamespace(**usage),
    )

def _make_agent(session_db, *, platform: str):
    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            session_db=session_db,
            session_id=f"{platform}-session",
            platform=platform,
        )
    agent.client = MagicMock()
    agent.client.chat.completions.create.return_value = _mock_response(
        usage={
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
        }
    )
    return agent

def test_run_conversation_persists_tokens_for_telegram_sessions():
    session_db = MagicMock()
    agent = _make_agent(session_db, platform="telegram")

    result = agent.run_conversation("hello")

    assert result["final_response"] == "done"
    # Per-call deltas are enqueued for the SessionDB background writer
    # (queue_token_counts) rather than written inline on the turn thread.
    session_db.queue_token_counts.assert_called_once()
    assert session_db.queue_token_counts.call_args.args[0] == "telegram-session"

def test_session_search_lazily_opens_db_when_entrypoint_did_not_pass_one(monkeypatch):
    sentinel_db = object()
    captured = {}

    class FakeSessionDB:
        def __new__(cls):
            return sentinel_db

    hermes_state = ModuleType("hermes_state")
    hermes_state.SessionDB = FakeSessionDB
    monkeypatch.setitem(sys.modules, "hermes_state", hermes_state)
    hermes_state_registry = ModuleType("hermes_state_registry")
    hermes_state_registry.acquire = lambda db_path=None: sentinel_db
    monkeypatch.setitem(sys.modules, "hermes_state_registry", hermes_state_registry)

    session_search_mod = ModuleType("tools.session_search_tool")

    def fake_session_search(**kwargs):
        captured.update(kwargs)
        return json.dumps({"success": True, "results": []})

    session_search_mod.session_search = fake_session_search
    monkeypatch.setitem(sys.modules, "tools.session_search_tool", session_search_mod)

    agent = _make_agent(None, platform="acp")
    result = json.loads(agent._invoke_tool(
        "session_search",
        {"query": "Hermes", "detail": "full"},
        "task-id",
    ))

    assert result["success"] is True
    assert captured["db"] is sentinel_db
    assert captured["query"] == "Hermes"
    assert captured["detail"] == "full"
    assert agent._session_db is sentinel_db


def test_openrouter_reported_cost_persists_as_actual_for_telegram():
    """Regression for #152288: the billed response must reach the token queue.

    A real non-CLI agent receives an OpenRouter usage object with model_dump,
    as the OpenAI SDK response does. The DB delta must record billed dollars
    in actual_cost_usd, not mark them as a model-table estimate.
    """
    import model_tools  # register model-provider profiles via normal discovery

    session_db = MagicMock()
    agent = _make_agent(session_db, platform="telegram")
    agent.provider = "openrouter"
    agent.model = "deepseek/deepseek-v4.1-flash-1017"
    response = agent.client.chat.completions.create.return_value
    response.usage.model_dump = lambda: {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
        "cost": 0.125,
    }

    result = agent.run_conversation("hello")

    assert result["final_response"] == "done"
    session_db.queue_token_counts.assert_called_once()
    session_id, = session_db.queue_token_counts.call_args.args
    delta = session_db.queue_token_counts.call_args.kwargs
    assert session_id == "telegram-session"
    assert delta["billing_provider"] == "openrouter"
    assert delta["actual_cost_usd"] == 0.125
    assert delta["estimated_cost_usd"] is None
    assert delta["cost_status"] == "actual"
    assert delta["cost_source"] == "provider_generation_api"
