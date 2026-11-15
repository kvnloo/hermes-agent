"""HTTP-level regression for the /v1/runs execute_code approval bridge (#155981).

The notifier-backed run must remain answerable even though api_server is normally
an unattended platform. This exercises the actual event and approval endpoints,
rather than calling the approval guard with a synthetic notifier.
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter
from tests.waiting import async_wait_until
from tools import approval, approval_context


async def _next_event(response, event_name: str) -> dict:
    """Read SSE frames until the requested event (ignoring the initial comment)."""
    for _ in range(12):
        frame = await asyncio.wait_for(response.content.readuntil(b"\n\n"), timeout=5)
        for line in frame.decode().splitlines():
            if line.startswith("data: "):
                event = json.loads(line.removeprefix("data: "))
                if event.get("event") == event_name:
                    return event
    pytest.fail(f"No {event_name} event in 12 SSE frames")


@pytest.mark.asyncio
async def test_execute_code_waits_for_run_approval_http_round_trip(monkeypatch):
    monkeypatch.setattr(approval, "_YOLO_MODE_FROZEN", False)
    # Leave unattended_mode and timeout at the shipped defaults (deny and
    # the regular human-decision timeout); only select manual approval mode.
    monkeypatch.setattr(
        approval_context, "_get_approval_config", lambda: {"mode": "manual"}
    )
    monkeypatch.setenv("HERMES_EXEC_ASK", "1")
    for name in (
        "HERMES_CRON_SESSION", "HERMES_SINGLE_QUERY_SESSION",
        "HERMES_GATEWAY_SESSION", "HERMES_INTERACTIVE",
    ):
        monkeypatch.delenv(name, raising=False)

    agent = MagicMock()
    agent.session_prompt_tokens = 0
    agent.session_completion_tokens = 0
    agent.session_total_tokens = 0
    result = {}

    def run_conversation(**_kwargs):
        result["decision"] = approval.check_execute_code_guard(
            "print('run with approval')", "local"
        )
        return {"final_response": "approved" if result["decision"]["approved"] else "blocked"}

    agent.run_conversation.side_effect = run_conversation
    adapter = APIServerAdapter(PlatformConfig(enabled=True, extra={}))
    app = web.Application()
    app["api_server_adapter"] = adapter
    app.router.add_post("/v1/runs", adapter._handle_runs)
    app.router.add_get("/v1/runs/{run_id}", adapter._handle_get_run)
    app.router.add_get("/v1/runs/{run_id}/events", adapter._handle_run_events)
    app.router.add_post("/v1/runs/{run_id}/approval", adapter._handle_run_approval)

    with patch.object(adapter, "_create_agent", return_value=agent):
        async with TestClient(TestServer(app)) as client:
            started = await client.post("/v1/runs", json={"input": "run Python"})
            assert started.status == 202
            run_id = (await started.json())["run_id"]

            await async_wait_until(
                lambda: adapter._run_statuses.get(run_id, {}).get("status") == "waiting_for_approval",
                timeout=8, what="execute_code to request approval instead of immediately denying",
            )
            status = await (await client.get(f"/v1/runs/{run_id}")).json()
            assert status["status"] == "waiting_for_approval"

            stream = await client.get(f"/v1/runs/{run_id}/events")
            try:
                event = await _next_event(stream, "approval.request")
                assert event["run_id"] == run_id
                assert "execute_code" in event["command"]
                assert "once" in event["choices"]

                answer = await client.post(
                    f"/v1/runs/{run_id}/approval", json={"choice": "once"}
                )
                assert answer.status == 200
                assert (await answer.json())["resolved"] == 1

                await async_wait_until(
                    lambda: adapter._run_statuses.get(run_id, {}).get("status") == "completed",
                    timeout=8, what="approved run to finish",
                )
                assert result["decision"]["approved"] is True
                completed = await (await client.get(f"/v1/runs/{run_id}")).json()
                assert completed["output"] == "approved"
            finally:
                stream.close()
