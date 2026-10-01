"""Probe (evidence only, NOT part of the commit): what `first_chunk_at - started_at`
measures in the post_api_request payload when a provider attempt is retried.

Copy to tests/agent/ in a worktree and run with scripts/run_tests.sh. It drives the
real conversation loop with a mocked provider client, records every
pre_api_request / post_api_request payload, and checks the two retry shapes:

1. main-loop retry: the first attempt raises a retryable transport error, the loop
   backs off and the second attempt streams a reply;
2. stream reconnect: inside one attempt, the first stream dies before any chunk and
   the streaming helper reconnects after its own backoff.

In both, `started_at` stays at the first try's start, so the difference also counts
the failed try and the backoff, while the real first-byte latency of the attempt
that answered is small.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from run_agent import AIAgent
from tests.agent.test_run_agent import _make_tool_defs

FAILED_TRY_S = 0.2
BACKOFF_S = 0.3


def _chunk(content=None, finish_reason=None, model=None):
    delta = SimpleNamespace(content=content, tool_calls=None, reasoning_content=None, reasoning=None)
    return SimpleNamespace(choices=[SimpleNamespace(index=0, delta=delta, finish_reason=finish_reason)],
                           model=model, usage=None)


def _reply():
    return iter([_chunk(content="Hello"), _chunk(content=" world", finish_reason="stop", model="m")])


@pytest.fixture()
def agent():
    with (
        patch("model_tools.get_tool_definitions", return_value=_make_tool_defs("web_search")),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        a = AIAgent(api_key="test-key-1234567890", base_url="https://openrouter.ai/api/v1",
                    quiet_mode=True, skip_context_files=True, skip_memory=True)
        a.client = MagicMock()
        a._cached_system_prompt = "You are helpful."
        a._use_prompt_caching = False
        a.compression_enabled = False
        a.save_trajectories = False
        a.stream_delta_callback = lambda _text: None  # force the streaming path
        return a


def _run(agent):
    calls = []

    def _record(name, **kw):
        calls.append((name, kw))
        return []

    with (
        patch("hermes_cli.lifecycle.has_hook", side_effect=lambda n: n in {"pre_api_request", "post_api_request"}),
        patch("hermes_cli.lifecycle.invoke_hook", side_effect=_record),
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("hi")
    pre = [kw for n, kw in calls if n == "pre_api_request"]
    post = [kw for n, kw in calls if n == "post_api_request"]
    return result, pre, post


def _report(label, pre, post, answered_at):
    p = post[0]
    print(f"\nPROBE {label}: pre_api_request events={len(pre)} "
          f"started_at(pre)={[round(x['started_at'], 3) for x in pre]} started_at(post)={p['started_at']:.3f} "
          f"first_chunk_at-started_at={p['first_chunk_at'] - p['started_at']:.3f}s "
          f"first_chunk_at-answering_try_start={p['first_chunk_at'] - answered_at:.3f}s "
          f"api_duration={p['api_duration']:.3f}s")


@patch("run_agent.AIAgent._create_request_openai_client")
@patch("run_agent.AIAgent._close_request_openai_client")
def test_main_loop_retry_keeps_first_started_at(_close, create, agent, monkeypatch):
    monkeypatch.setattr("agent.retry_utils.jittered_backoff", lambda *a, **k: BACKOFF_S)
    client = MagicMock()
    client.chat.completions.create.side_effect = lambda **_kw: _reply()
    create.return_value = client
    real = agent._interruptible_streaming_api_call
    tries = []

    def _flaky(api_kwargs, **kw):
        tries.append(time.time())
        if len(tries) == 1:
            time.sleep(FAILED_TRY_S)
            raise ConnectionError("upstream reset before first byte")
        return real(api_kwargs, **kw)

    with patch.object(agent, "_interruptible_streaming_api_call", side_effect=_flaky):
        result, pre, post = _run(agent)

    assert result["final_response"] == "Hello world"
    assert len(tries) == 2 and len(post) == 1
    p = post[0]
    _report("main-loop retry", pre, post, tries[1])
    # pre_api_request fires per try, and every try (and the success) carries the same started_at.
    assert len(pre) == 2
    assert pre[0]["started_at"] == pre[1]["started_at"] == p["started_at"] <= tries[0]
    # The difference spans the failed try + backoff; the answering try's own first byte was fast.
    assert p["first_chunk_at"] - p["started_at"] >= FAILED_TRY_S + BACKOFF_S
    assert p["first_chunk_at"] - tries[1] < FAILED_TRY_S
    assert p["api_duration"] >= FAILED_TRY_S + BACKOFF_S


@patch("run_agent.AIAgent._create_request_openai_client")
@patch("run_agent.AIAgent._close_request_openai_client")
def test_stream_reconnect_keeps_first_started_at(_close, create, agent, monkeypatch):
    monkeypatch.setattr("agent.retry_utils.jittered_backoff", lambda *a, **k: BACKOFF_S)
    opened = []

    def _dead():
        raise ConnectionError("upstream closed before first byte")
        yield  # pragma: no cover

    def _open(**_kw):
        opened.append(time.time())
        return _dead() if len(opened) == 1 else _reply()

    client = MagicMock()
    client.chat.completions.create.side_effect = _open
    create.return_value = client

    result, pre, post = _run(agent)

    assert result["final_response"] == "Hello world"
    assert len(opened) == 2 and len(post) == 1
    p = post[0]
    _report("stream reconnect", pre, post, opened[1])
    assert len(pre) == 1  # one attempt; the reconnect happens inside the streaming helper
    assert p["started_at"] <= opened[0]
    assert p["first_chunk_at"] - p["started_at"] >= BACKOFF_S
    assert p["first_chunk_at"] >= opened[1]
    assert p["first_chunk_at"] - opened[1] < BACKOFF_S
