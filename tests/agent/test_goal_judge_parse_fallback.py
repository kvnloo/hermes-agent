"""Regression for NousResearch/hermes-agent#150886 (reported by 8ullyMaguire).

An HTTP-200 coding-router tool call is not a goal-judge verdict. When a task
fallback is configured, the same auxiliary request must try it before /goal
records a parse failure; exhaustion still participates in the auto-pause guard.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from unittest.mock import MagicMock, patch

import pytest

from agent import auxiliary_client as aux
from hermes_cli.goals import judge_goal


@pytest.fixture(autouse=True)
def _fresh_aux_health():
    aux._reset_aux_unhealthy_cache()
    yield
    aux._reset_aux_unhealthy_cache()


def _client(base_url, content):
    client = MagicMock()
    client.base_url = base_url
    reply = MagicMock()
    reply.choices = [MagicMock()]
    reply.choices[0].message.content = content
    reply.choices[0].message.tool_calls = None
    client.chat.completions.create.return_value = reply
    return client


def _judge_through_configured_chain(fallback_content):
    primary = _client("http://localhost:1/v1", "<tool_call>read<param_key>filePath</param_key>")
    backup = _client("http://localhost:2/v1", fallback_content)
    chain = [{"provider": "custom", "model": "strict", "base_url": backup.base_url}]
    with (
        patch.object(aux, "_resolve_task_provider_model", return_value=("auto", None, None, None, None)),
        patch.object(aux, "_get_cached_client", return_value=(primary, "router-combo")),
        patch.object(aux, "_get_auxiliary_task_config", return_value={"fallback_chain": chain}),
        patch.object(aux, "_try_configured_fallback_chain", side_effect=[
            (backup, "strict", "fallback_chain[0](custom)"), (None, None, ""),
        ]),
        patch.object(aux, "_try_main_fallback_chain", return_value=(None, None, "")),
        patch.object(aux, "_try_payment_fallback", return_value=(None, None, "")),
    ):
        verdict = judge_goal("ship the feature", "feature shipped")
    return verdict, primary, backup


def test_malformed_primary_uses_goal_judge_chain_before_pausing():
    result, primary, backup = _judge_through_configured_chain(
        '{"verdict":"done","reason":"verified"}'
    )
    assert result == ("done", "verified", False, None, False)
    assert primary.chat.completions.create.call_count == 1
    assert backup.chat.completions.create.call_count == 1


def test_exhausted_chain_is_still_a_parse_failure_not_transport_failure():
    result, primary, backup = _judge_through_configured_chain(
        "<tool_call>another invalid reply</tool_call>"
    )
    assert result[0] == "continue"
    assert "fallbacks exhausted" in result[1]
    assert result[2:] == (True, None, False)
    assert primary.chat.completions.create.call_count == 1
    assert backup.chat.completions.create.call_count == 1


@pytest.fixture
def judge_endpoint(monkeypatch, tmp_path):
    """Exercise config, SDK transport, validation and fallback selection without a paid API."""
    from hermes_cli import _early_recovery

    # A linked checkout's metadata can live under the protected installation home.
    monkeypatch.setattr(_early_recovery, "_git_dir", lambda _root: tmp_path / ".git")
    requests, replies = [], {}
    monkeypatch.setenv("NO_PROXY", "localhost")
    aux.shutdown_cached_clients()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, payload))
            response = {
                "id": "chatcmpl-judge", "object": "chat.completion", "created": 1,
                "model": payload["model"],
                "choices": [{
                    "index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": replies[payload["model"]]},
                }],
            }
            if payload.get("stream"):
                response["object"] = "chat.completion.chunk"
                response["choices"][0]["delta"] = response["choices"][0].pop("message")
                body = f"data: {json.dumps(response)}\n\ndata: [DONE]\n\n".encode()
                content_type = "text/event-stream"
            else:
                body = json.dumps(response).encode()
                content_type = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("localhost", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{server.server_port}/v1", requests, replies
    finally:
        aux.shutdown_cached_clients()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


_VALID = '{"verdict":"done","reason":"verified"}'
_BAD = "<tool_call>not a verdict</tool_call>"


@pytest.mark.parametrize("contents,chain,expected_models,done", [
    ({"primary": _BAD, "strict": _VALID}, ["strict"], ["primary", "strict"], True),
    ({"primary": _BAD, "strict": _BAD, "rescue": _VALID},
     ["strict", "rescue"], ["primary", "strict", "rescue"], True),
    ({"primary": _BAD, "strict": _BAD}, ["strict"], ["primary", "strict"], False),
    ({"primary": _BAD}, [], ["primary"], False),
    ({"primary": _VALID}, ["strict"], ["primary"], True),
], ids=["backup", "ordered-walk", "exhausted", "no-chain", "valid-primary"])
def test_judge_config_to_http_verdict(tmp_path, monkeypatch, judge_endpoint,
                                     contents, chain, expected_models, done):
    base_url, requests, replies = judge_endpoint
    replies.update(contents)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    route = {"provider": "custom", "model": "primary", "base_url": base_url}
    config = {
        "model": {**route, "default": "primary"},
        "auxiliary": {
            "free_only": True,
            "goal_judge": {
                **route, "timeout": 5,
                "fallback_chain": [
                    {"provider": "custom", "model": model, "base_url": base_url}
                    for model in chain
                ],
            },
        },
    }
    # JSON is YAML-compatible and keeps this fixture independent of a serializer.
    (tmp_path / "config.yaml").write_text(json.dumps(config))

    result = judge_goal("ship the feature", "feature shipped")

    assert [payload["model"] for _, payload in requests] == expected_models, result
    assert all(path == "/v1/chat/completions" for path, _ in requests)
    if done:
        assert result == ("done", "verified", False, None, False)
    else:
        assert result[0] == "continue"
        assert result[2:] == (True, None, False)
        if chain:
            assert "fallbacks exhausted" in result[1]
