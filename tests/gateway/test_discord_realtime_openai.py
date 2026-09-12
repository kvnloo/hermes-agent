"""OpenAI Realtime adapter: documented protocol, DI websocket, no live network."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator

import pytest

from agent.realtime_voice import RealtimeEventType
from plugins.platforms.discord.realtime_openai import (
    OpenAIRealtimeProvider,
    pcm24_mono_to_48k_stereo,
    pcm48_stereo_to_24k_mono,
)


class FakeWebSocket:
    def __init__(self, incoming: list[dict] | None = None) -> None:
        self.sent: list[dict] = []
        self._incoming = list(incoming or [])
        self.closed = False

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))

    async def recv(self):
        if not self._incoming:
            raise asyncio.CancelledError()
        return json.dumps(self._incoming.pop(0))

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_openai_session_maps_documented_events_and_sends_pcm16():
    pcm24 = b"\x01\x00" * 24
    ws = FakeWebSocket([
        {"type": "session.created", "event_id": "s1", "session": {"id": "sess_1"}},
        {
            "type": "conversation.item.input_audio_transcription.delta",
            "event_id": "t1", "item_id": "item_in", "delta": "hel",
        },
        {
            "type": "conversation.item.input_audio_transcription.completed",
            "event_id": "t2", "item_id": "item_in", "transcript": "hello",
        },
        {
            "type": "response.output_audio.delta",
            "event_id": "a1", "item_id": "item_out", "response_id": "resp_1",
            "delta": base64.b64encode(pcm24).decode("ascii"),
        },
        {
            "type": "response.function_call_arguments.done",
            "event_id": "f1", "call_id": "call_1", "name": "terminal",
            "arguments": "{\"command\": \"pwd\"}", "response_id": "resp_1",
        },
        {"type": "response.done", "event_id": "d1"},
    ])

    async def factory(url: str, headers: dict[str, str]):
        assert "gpt-realtime-2.1" in url
        assert headers["Authorization"].startswith("Bearer ")
        return ws

    provider = OpenAIRealtimeProvider(
        api_key="sk-test", model="gpt-realtime-2.1", vad="server_vad",
        websocket_factory=factory,
    )
    session = await provider.open_session(instructions="Hermes owns tools", tools=[{"name": "terminal"}], voice="verse")
    await session.send_audio(b"\x00\x01" * 8)
    events = []
    try:
        async for event in session.events():
            events.append(event)
    except asyncio.CancelledError:
        pass

    assert ws.sent[0]["type"] == "session.update"
    assert ws.sent[0]["session"]["turn_detection"] == {"type": "server_vad"}
    assert ws.sent[0]["session"]["tools"] == [{"name": "terminal"}]
    assert ws.sent[1]["type"] == "input_audio_buffer.append"
    kinds = [e.type for e in events]
    assert RealtimeEventType.SESSION_CONNECTED in kinds
    assert RealtimeEventType.INPUT_TRANSCRIPT in kinds
    assert RealtimeEventType.AUDIO in kinds
    assert RealtimeEventType.TOOL_CALL in kinds
    tool = next(e for e in events if e.type is RealtimeEventType.TOOL_CALL)
    assert tool.call_id == "call_1"
    assert tool.tool_name == "terminal"
    assert tool.arguments == {"command": "pwd"}
    final = [e for e in events if e.type is RealtimeEventType.INPUT_TRANSCRIPT and e.final]
    assert final[0].text == "hello"


@pytest.mark.asyncio
async def test_truncate_uses_heard_ms_not_generated_ms():
    ws = FakeWebSocket([])

    async def factory(_url: str, _headers: dict[str, str]):
        return ws

    provider = OpenAIRealtimeProvider(api_key="sk-test", websocket_factory=factory)
    session = await provider.open_session(instructions="", tools=[])
    from agent.realtime_voice import HeardAudioBoundary
    await session.truncate_response(HeardAudioBoundary("item_out", 240, "resp_1", 1))
    await session.cancel_response()
    kinds = [row["type"] for row in ws.sent]
    assert "conversation.item.truncate" in kinds
    trunc = next(row for row in ws.sent if row["type"] == "conversation.item.truncate")
    assert trunc["audio_end_ms"] == 240
    assert trunc["item_id"] == "item_out"
    assert "response.cancel" in kinds


def test_pcm_roundtrip_integer_ratio():
    stereo = b"\x10\x00\x10\x00\x20\x00\x20\x00" * 4
    mono = pcm48_stereo_to_24k_mono(stereo)
    assert len(mono) == len(stereo) // 4
    back = pcm24_mono_to_48k_stereo(mono)
    assert len(back) == len(mono) * 4
