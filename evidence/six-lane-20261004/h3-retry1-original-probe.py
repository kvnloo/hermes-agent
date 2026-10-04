"""Consumer probe for the intermediate-4xx chain report in #132410."""
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from openai import APIConnectionError, NotFoundError

from run_agent import AIAgent


@pytest.mark.parametrize("primary_unreachable", [False, True])
def test_intermediate_missing_model_advances_to_last_configured_route(primary_unreachable):
    routes = [
        {"provider": "custom", "model": model, "base_url": f"http://127.0.0.1:{port}/v1", "api_key": "synthetic-key"}
        for model, port in [("missing-model", 19101), ("healthy-model", 19102)]
    ]
    with patch("model_tools.get_tool_definitions", return_value=[]), patch("model_tools.check_toolset_requirements", return_value={}):
        agent = AIAgent(
            api_key="synthetic-key", base_url="http://127.0.0.1:19100/v1", provider="custom",
            model="primary-model", quiet_mode=True, skip_context_files=True, skip_memory=True,
            save_trajectories=False, fallback_model=routes,
        )
    agent._api_max_retries = 1
    calls = []

    def complete(**api_kwargs):
        calls.append(agent.model)
        if primary_unreachable and agent.model == "primary-model":
            raise APIConnectionError(request=httpx.Request("POST", str(agent.base_url)))
        if agent.model != "healthy-model":
            response = httpx.Response(404, request=httpx.Request("POST", str(agent.base_url)))
            raise NotFoundError("model not found", response=response, body={"error": {"message": "model not found"}})
        message = SimpleNamespace(content="Recovered", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")], model=agent.model, usage=None)

    with patch("openai.resources.chat.completions.Completions.create", side_effect=complete):
        result = agent.run_conversation("Hello")
    assert calls[-2:] == ["missing-model", "healthy-model"]
    assert calls[:-2] and set(calls[:-2]) == {"primary-model"}
    assert result["completed"] is True
    assert result["final_response"] == "Recovered"
