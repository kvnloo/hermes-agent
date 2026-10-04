"""Gateway override pool recovery through a real AIAgent and synthetic HTTP responses."""

import json
import time
from pathlib import Path

import httpx

from gateway.run import GatewayRunner


def test_override_turn_retries_rotated_credential_before_fallback(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text(
        "model:\n  provider: openai-codex\n  default: unavailable-model\n"
        "auth:\n  adopt_external_logins: false\n"
    )
    rows = [
        {"id": f"seat-{i}", "label": f"seat-{i}", "priority": i,
         "auth_type": "api_key", "source": "manual",
         "access_token": f"synthetic-key-{i}",
         "model_cooldowns": {"unavailable-model": time.time() + 3600}}
        for i in range(2)
    ]
    (home / "auth.json").write_text(json.dumps({"credential_pool": {"openai-codex": rows}}))
    from hermes_cli import config
    config._LOAD_CONFIG_CACHE.clear()
    config._RAW_CONFIG_CACHE.clear()
    runner = object.__new__(GatewayRunner)
    runner._session_model_overrides = {"session": {
        "model": "supported-model", "provider": "openai-codex",
        "api_key": rows[0]["access_token"], "api_mode": "codex_responses",
        "base_url": "https://chatgpt.com/backend-api/codex",
    }}
    calls = []

    def send(client, request, **kwargs):
        if not request.url.path.endswith(("/responses", "/chat/completions")):
            return httpx.Response(404, request=request, json={"error": "synthetic metadata miss"})
        body = json.loads(request.content)
        key = request.headers.get("authorization")
        calls.append((body["model"], key, str(request.url)))
        if key == "Bearer synthetic-key-0":
            return httpx.Response(429, request=request, json={"error": {
                "type": "usage_limit_reached", "code": "usage_limit_reached",
                "message": "The usage limit has been reached", "reset_at": time.time() + 3600,
            }})
        if body["model"] == "fallback-model":
            chunk = {"id": "fallback", "object": "chat.completion.chunk", "created": 0,
                "model": "fallback-model", "choices": [{"index": 0, "finish_reason": "stop",
                    "delta": {"role": "assistant", "content": "Fallback answered"}}]}
            return httpx.Response(200, request=request, headers={"content-type": "text/event-stream"},
                content=("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode())
        response = {
            "id": "synthetic-response", "object": "response", "created_at": 0,
            "model": body["model"], "status": "completed", "usage": None,
            "output": [{"id": "synthetic-message", "type": "message", "role": "assistant",
                "status": "completed", "content": [{"type": "output_text", "text": "Recovered",
                    "annotations": []}]}],
        }
        events = [{"type": "response.output_item.done", "output_index": 0,
                   "item": response["output"][0]},
                  {"type": "response.completed", "response": response}]
        return httpx.Response(200, request=request, headers={"content-type": "text/event-stream"},
            content="".join("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n"
                            for event in events).encode())

    # The final synchronous transport door also captures metadata and fallback clients.
    async def unexpected_async(client, request, **kwargs):
        raise AssertionError("Unexpected async request in synchronous turn proof")

    monkeypatch.setattr(httpx.Client, "send", send)
    monkeypatch.setattr(httpx.AsyncClient, "send", unexpected_async)
    model, runtime = runner._resolve_session_agent_runtime(session_key="session")
    monkeypatch.setattr("model_tools.get_tool_definitions", lambda **kwargs: [])
    monkeypatch.setattr("model_tools.check_toolset_requirements", lambda: {})
    from run_agent import AIAgent
    agent = AIAgent(
        model=model, **runtime, quiet_mode=True, skip_context_files=True, skip_memory=True,
        save_trajectories=False, max_iterations=4,
        fallback_model=[{"provider": "custom", "model": "fallback-model",
                         "base_url": "http://127.0.0.1:19103/v1", "api_key": "synthetic-fallback"}],
    )
    try:
        result = agent.run_conversation("Hello")
    finally:
        agent.client.close()
        agent._close_cached_request_openai_client(reason="test_cleanup")
    assert result["completed"] is True
    assert result["final_response"] == "Recovered"
    assert calls[0][0:2] == (model, "Bearer synthetic-key-0")
    assert calls[-1][0:2] == (model, "Bearer synthetic-key-1")
    assert all(m == model for m, _, _ in calls), calls
    assert all(url.startswith(runtime["base_url"]) for _, _, url in calls), calls
    assert agent._fallback_activated is False
    assert runtime["credential_pool"].select(model="unavailable-model") is None
