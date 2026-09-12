"""OpenAI Realtime WebSocket adapter for Discord VC duplex.

Lives next to the Discord consumer (not under plugins/realtime_voice/).
Unit tests inject a websocket factory — this module never opens a network
connection unless that factory does.
"""

from __future__ import annotations

import base64
import json
import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from agent.realtime_voice import (
    HeardAudioBoundary,
    RealtimeEvent,
    RealtimeEventType,
    RealtimeSession,
    RealtimeVoiceProvider,
)

DEFAULT_MODEL = "gpt-realtime-2.1"
DEFAULT_URL = "wss://api.openai.com/v1/realtime"
PCM16_RATE = 24000

WebSocketFactory = Callable[[str, dict[str, str]], Awaitable[Any]]


def pcm48_stereo_to_24k_mono(pcm: bytes) -> bytes:
    """Discord capture (48 kHz stereo s16) → OpenAI Realtime pcm16 (24 kHz mono)."""
    if len(pcm) < 8:
        return b""
    out = bytearray()
    for i in range(0, len(pcm) - 7, 8):
        left0 = int.from_bytes(pcm[i:i + 2], "little", signed=True)
        right0 = int.from_bytes(pcm[i + 2:i + 4], "little", signed=True)
        left1 = int.from_bytes(pcm[i + 4:i + 6], "little", signed=True)
        right1 = int.from_bytes(pcm[i + 6:i + 8], "little", signed=True)
        sample = (left0 + right0 + left1 + right1) // 4
        out += sample.to_bytes(2, "little", signed=True)
    return bytes(out)


def pcm24_mono_to_48k_stereo(pcm: bytes) -> bytes:
    """OpenAI Realtime pcm16 (24 kHz mono) → Discord mixer (48 kHz stereo s16)."""
    if len(pcm) < 2:
        return b""
    out = bytearray()
    for i in range(0, len(pcm) - 1, 2):
        sample = pcm[i:i + 2]
        out += sample + sample + sample + sample  # 24k→48k and mono→stereo
    return bytes(out)


def _json_loads(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    if not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


class OpenAIRealtimeSession(RealtimeSession):
    """One OpenAI Realtime WS mapped onto RealtimeEvent."""

    def __init__(self, ws: Any, *, model: str, epoch: int = 0) -> None:
        self._ws = ws
        self._model = model
        self._epoch = epoch
        self._closed = False
        self._seq = 0
        self._session_id = ""
        self._current_item_id: str | None = None
        self._current_response_id: str | None = None
        self._audio_ms = 0
        self._function_buffers: dict[str, dict[str, Any]] = {}

    async def send_audio(self, pcm: bytes) -> None:
        encoded = base64.b64encode(pcm).decode("ascii")
        await self._send({"type": "input_audio_buffer.append", "audio": encoded})

    async def submit_tool_result(self, call_id: str, output: str) -> None:
        await self._send({
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output,
            },
        })

    async def submit_tool_group(self, results: list[tuple[str, str]]) -> None:
        await super().submit_tool_group(results)
        if results:
            await self._send({"type": "response.create"})

    async def truncate_response(self, boundary: HeardAudioBoundary) -> None:
        await self._send({
            "type": "conversation.item.truncate",
            "item_id": boundary.item_id,
            "content_index": 0,
            "audio_end_ms": boundary.audio_end_ms,
        })

    async def cancel_response(self) -> None:
        await self._send({"type": "response.cancel"})

    async def close(self) -> None:
        self._closed = True
        closer = getattr(self._ws, "close", None)
        if closer is not None:
            result = closer()
            if hasattr(result, "__await__"):
                await result

    def events(self) -> AsyncIterator[RealtimeEvent]:
        return self._events()

    async def _events(self) -> AsyncIterator[RealtimeEvent]:
        while not self._closed:
            raw = await self._recv()
            if raw is None:
                return
            payload = _json_loads(raw)
            if payload is None:
                continue
            event = self._normalize(payload)
            if event is not None:
                yield event

    async def configure(self, *, instructions: str, tools: list[dict[str, Any]],
                        voice: str | None, vad: str) -> None:
        turn_detection: dict[str, Any]
        if vad == "semantic_vad":
            turn_detection = {"type": "semantic_vad"}
        elif vad == "manual":
            turn_detection = None  # type: ignore[assignment]
        else:
            turn_detection = {"type": "server_vad"}
        session: dict[str, Any] = {
            "modalities": ["audio", "text"],
            "instructions": instructions,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "tools": tools,
            "tool_choice": "auto",
        }
        if turn_detection is not None:
            session["turn_detection"] = turn_detection
        if voice:
            session["voice"] = voice
        await self._send({"type": "session.update", "session": session})

    async def _send(self, payload: dict[str, Any]) -> None:
        send = self._ws.send
        result = send(json.dumps(payload))
        if hasattr(result, "__await__"):
            await result

    async def _recv(self) -> Any:
        recv = getattr(self._ws, "recv", None)
        if recv is None:
            return None
        try:
            result = recv()
            if hasattr(result, "__await__"):
                result = await result
            return result
        except Exception:
            return None

    def _identity(self, **extra: Any) -> dict[str, Any]:
        self._seq += 1
        ident = {
            "event_id": extra.pop("event_id", None) or uuid.uuid4().hex,
            "cancellation_epoch": self._epoch,
            "producer_sequence": self._seq,
            "item_id": extra.pop("item_id", self._current_item_id),
            "response_id": extra.pop("response_id", self._current_response_id),
            "provider_session_id": self._session_id or None,
        }
        ident.update(extra)
        return ident

    def _normalize(self, payload: dict[str, Any]) -> RealtimeEvent | None:
        kind = str(payload.get("type") or "")
        event_id = str(payload.get("event_id") or uuid.uuid4().hex)
        if kind == "session.created":
            session = payload.get("session") or {}
            self._session_id = str(session.get("id") or "")
            return RealtimeEvent(type=RealtimeEventType.SESSION_CONNECTED, **self._identity(event_id=event_id))
        if kind in {"input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped"}:
            started = kind.endswith("started")
            return RealtimeEvent(
                type=RealtimeEventType.TURN_STARTED if started else RealtimeEventType.TURN_ENDED,
                **self._identity(event_id=event_id, item_id=payload.get("item_id")),
            )
        if kind in {
            "conversation.item.input_audio_transcription.delta",
            "conversation.item.input_audio_transcription.completed",
        }:
            text = str(payload.get("delta") or payload.get("transcript") or "")
            final = kind.endswith("completed")
            turn_id = str(payload.get("item_id") or "input")
            return RealtimeEvent(
                type=RealtimeEventType.INPUT_TRANSCRIPT,
                text=text,
                final=final,
                **self._identity(event_id=event_id, turn_id=turn_id, item_id=turn_id,
                                 revision=1 if final else 0),
            )
        if kind in {"response.audio.delta", "response.output_audio.delta"}:
            b64 = payload.get("delta") or ""
            try:
                pcm = base64.b64decode(b64)
            except Exception:
                pcm = b""
            item_id = str(payload.get("item_id") or self._current_item_id or "audio")
            response_id = str(payload.get("response_id") or self._current_response_id or "")
            self._current_item_id = item_id
            self._current_response_id = response_id or self._current_response_id
            start = self._audio_ms
            self._audio_ms += max(0, len(pcm) // (PCM16_RATE * 2) * 1000) or (len(pcm) * 1000 // (PCM16_RATE * 2) if pcm else 0)
            return RealtimeEvent.audio(
                pcm,
                **self._identity(event_id=event_id, item_id=item_id, response_id=response_id or None,
                                 audio_start_ms=start, audio_end_ms=self._audio_ms),
            )
        if kind in {"response.audio.done", "response.output_audio.done"}:
            return RealtimeEvent(type=RealtimeEventType.AUDIO_DONE, **self._identity(event_id=event_id))
        if kind == "response.created":
            response = payload.get("response") or {}
            self._current_response_id = str(response.get("id") or payload.get("response_id") or "")
            self._audio_ms = 0
            return RealtimeEvent(type=RealtimeEventType.TURN_STARTED, **self._identity(event_id=event_id))
        if kind == "response.function_call_arguments.delta":
            call_id = str(payload.get("call_id") or "")
            buf = self._function_buffers.setdefault(call_id, {"name": payload.get("name") or "", "arguments": ""})
            buf["arguments"] += str(payload.get("delta") or "")
            if payload.get("name"):
                buf["name"] = payload["name"]
            return None
        if kind == "response.function_call_arguments.done":
            call_id = str(payload.get("call_id") or "")
            raw_args = payload.get("arguments") or self._function_buffers.get(call_id, {}).get("arguments") or "{}"
            name = str(payload.get("name") or self._function_buffers.get(call_id, {}).get("name") or "")
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
            except json.JSONDecodeError:
                arguments = {"_raw": raw_args}
            self._function_buffers.pop(call_id, None)
            return RealtimeEvent.tool_call(
                call_id, name, arguments if isinstance(arguments, dict) else {"_raw": arguments},
                **self._identity(event_id=event_id, tool_group_id=self._current_response_id),
            )
        if kind == "response.done":
            return RealtimeEvent(type=RealtimeEventType.RESPONSE_COMPLETED, **self._identity(event_id=event_id))
        if kind == "response.cancelled":
            return RealtimeEvent(type=RealtimeEventType.RESPONSE_CANCELLED, **self._identity(event_id=event_id))
        if kind == "error":
            err = payload.get("error") or {}
            return RealtimeEvent(
                type=RealtimeEventType.ERROR,
                text=str(err.get("code") or "provider_error"),
                **self._identity(event_id=event_id),
            )
        return None


class OpenAIRealtimeProvider(RealtimeVoiceProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        vad: str = "server_vad",
        base_url: str = DEFAULT_URL,
        websocket_factory: WebSocketFactory | None = None,
        voice: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._vad = vad
        self._base_url = base_url.rstrip("/")
        self._websocket_factory = websocket_factory
        self._default_voice = voice

    @property
    def name(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI Realtime"

    @property
    def advertised_capabilities(self) -> frozenset[str]:
        caps = {"server_vad", "truncate", "transcript_replace", "binary_frames"}
        if self._vad == "semantic_vad":
            caps.add("semantic_vad")
        return frozenset(caps)

    def is_available(self) -> bool:
        return bool(self._api_key or os.getenv("OPENAI_API_KEY"))

    async def open_session(self, *, instructions: str, tools: list[dict[str, Any]],
                           voice: str | None = None) -> RealtimeSession:
        factory = self._websocket_factory
        if factory is None:
            raise RuntimeError("OpenAI Realtime websocket factory is not configured")
        key = self._api_key or os.getenv("OPENAI_API_KEY") or ""
        url = f"{self._base_url}?model={self._model}"
        headers = {
            "Authorization": f"Bearer {key}",
            "OpenAI-Beta": "realtime=v1",
        }
        ws = await factory(url, headers)
        session = OpenAIRealtimeSession(ws, model=self._model)
        await session.configure(
            instructions=instructions,
            tools=tools,
            voice=voice or self._default_voice,
            vad=self._vad,
        )
        return session
