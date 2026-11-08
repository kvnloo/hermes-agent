"""Regression for NousResearch/hermes-agent#150822: native Gemini stream aborts."""

import json
import socket
from types import SimpleNamespace

import httpx
import pytest

import run_agent
from agent.agent_runtime_helpers import force_close_tcp_sockets
from agent.chat_completion_helpers import _StreamingCall
from agent.gemini_native_adapter import GeminiNativeClient


def _event(text, *, token=None, finish=None):
    candidate = {"content": {"role": "model", "parts": [{"text": text}]}}
    if token:
        candidate["continuationToken"] = token
    if finish:
        candidate["finishReason"] = finish
    return {"candidates": [candidate]}


def test_native_gemini_stream_abort_tracks_hops_and_stops_checkpoint_resend():
    pool_reader, pool_writer = socket.socketpair()
    first_reader, first_writer = socket.socketpair()
    second_reader, second_writer = socket.socketpair()
    try:
        class Response:
            status_code = 200
            headers = {}

            def __init__(self, reader, events):
                self.extensions = {"network_stream": SimpleNamespace(_sock=reader)}
                self.events = events

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def close(self):
                raise AssertionError("monitor must not close a response")

            def iter_text(self):
                for event in self.events:
                    if event is None:
                        raise httpx.ReadError("aborted socket read")
                    yield f"data: {json.dumps(event)}\n\n"

        responses = [
            Response(first_reader, [_event("first", token="hop1", finish="CONTINUATION")]),
            Response(second_reader, [_event("second", token="ckpt2"), None]),
        ]

        class HTTP:
            def __init__(self):
                connection = SimpleNamespace(_network_stream=SimpleNamespace(_sock=pool_reader))
                self._transport = SimpleNamespace(
                    _pool=SimpleNamespace(_connections=[connection], _requests=[]))
                self._mounts = {}
                self.requests = []

            def stream(self, method, url, json=None, headers=None, timeout=None):
                self.requests.append(json)
                return responses[len(self.requests) - 1]

            def close(self):
                pass

        http = HTTP()
        client = GeminiNativeClient(api_key="AQ.test", http_client=http)
        assert force_close_tcp_sockets(client) == 1
        pool_writer.settimeout(2)
        assert pool_writer.recv(1) == b""

        agent = run_agent.AIAgent(
            api_key="test-key", base_url="http://127.0.0.1:1/v1", model="m",
            provider="custom", quiet_mode=True, skip_context_files=True,
            skip_memory=True, enabled_toolsets=[], max_iterations=1,
        )
        call = _StreamingCall(
            agent, {"model": "m", "messages": [{"role": "user", "content": "hi"}]}, None)
        call._start_stream_attempt()
        call._new_diag()
        stream = client.chat.completions.create(
            model="gemini-4-argon", messages=[{"role": "user", "content": "hi"}],
            stream=True, max_tokens=65_536)
        call._chat_stream_created(stream)
        assert call._attempt_stream_response is None

        next(stream)
        assert call._attempt_stream_response is responses[0]
        next(stream)
        assert call._attempt_stream_response is responses[1]
        assert http.requests[1]["continuationToken"] == "hop1"

        call._request_cancelled["value"] = True
        call._cancel_current_stream_attempt("stream_interrupt_abort")
        call._shutdown_stale_attempt_socket(responses[1])
        second_writer.settimeout(2)
        assert second_writer.recv(1) == b""
        with pytest.raises(httpx.ReadError):
            next(stream)
        assert len(http.requests) == 2
    finally:
        for sock in (pool_reader, pool_writer, first_reader, first_writer, second_reader, second_writer):
            sock.close()
