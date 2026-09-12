"""Discord VC duplex consumer: admission, barge-in, fallback, coordinator wiring."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from agent.realtime_voice import RealtimeEvent, RealtimeEventType
from agent.realtime_voice_coordinator import RealtimeVoiceCoordinator, RealtimeVoiceMetrics

logger = logging.getLogger(__name__)

DEGRADED_LEGACY = "DEGRADED_LEGACY"
BACKCHANNEL_MS = 300
BYTES_PER_MS_48K_STEREO = 192  # 48000 * 2ch * 2bytes / 1000

FallbackFn = Callable[..., Awaitable[Any]]
TranscriptSink = Callable[[str, str], None]


def load_discord_duplex_config(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Read ``voice.discord_duplex``; missing keys inherit defaults. Never reads HERMES_* flags."""
    defaults = {
        "enabled": False,
        "provider": "openai",
        "model": "gpt-realtime-2.1",
        "vad": "server_vad",
        "max_ingress_seconds": 2.0,
        "max_playback_seconds": 1.0,
        "max_pending_tools": 8,
        "reconnect_deadline_seconds": 5.0,
        "api_key": None,
    }
    if config is None:
        try:
            from hermes_cli.config import load_config
            config = load_config() or {}
        except Exception:
            config = {}
    voice = (config or {}).get("voice") or {}
    raw = voice.get("discord_duplex") or {}
    if not isinstance(raw, dict):
        raw = {}
    merged = dict(defaults)
    merged.update({k: raw[k] for k in defaults if k in raw})
    return merged


def is_discord_duplex_enabled(config: Optional[dict[str, Any]] = None) -> bool:
    cfg = load_discord_duplex_config(config)
    return bool(cfg.get("enabled"))


def classify_overlap(
    pcm: bytes,
    *,
    playing: bool,
    echo_window: bool,
    duration_ms: int,
    rms: Optional[int] = None,
    echo_rms: int = 400,
    takeover_rms: int = 1200,
) -> str:
    """Acoustic admission: echo | backchannel | takeover | speech | none."""
    if not pcm:
        return "none"
    if rms is None:
        rms = _pcm_rms(pcm)
    if playing and echo_window and rms < takeover_rms:
        return "echo"
    if playing and duration_ms < BACKCHANNEL_MS:
        return "backchannel"
    if playing and rms >= takeover_rms:
        return "takeover"
    if rms < echo_rms:
        return "none"
    return "speech"


def _pcm_rms(pcm: bytes) -> int:
    if len(pcm) < 2:
        return 0
    total = 0
    count = 0
    for i in range(0, len(pcm) - 1, 2):
        sample = int.from_bytes(pcm[i:i + 2], "little", signed=True)
        total += sample * sample
        count += 1
    if not count:
        return 0
    return int((total / count) ** 0.5)


@dataclass
class DuplexPlaybackClock:
    item_id: str | None = None
    event: RealtimeEvent | None = None


@dataclass
class DiscordDuplexConsumer:
    """Surface-side duplex: capture stays live, mixer is the heard clock, fallback is legacy."""

    coordinator: RealtimeVoiceCoordinator
    mixer: Any
    fallback: FallbackFn
    transcript_sink: Optional[TranscriptSink] = None
    max_ingress_seconds: float = 2.0
    max_playback_seconds: float = 1.0
    metrics: RealtimeVoiceMetrics | None = None
    degraded: bool = False
    degrade_reason: str | None = None
    finalized_turns: dict[str, str] = field(default_factory=dict)
    _clock: DuplexPlaybackClock = field(default_factory=DuplexPlaybackClock)
    _ingress_bytes: int = 0

    def mark_degraded(self, reason: str) -> None:
        if self.degraded:
            return
        self.degraded = True
        self.degrade_reason = reason
        (self.metrics or self.coordinator.metrics).mark("fallback_start")
        logger.warning("%s discord duplex falling back to legacy path (%s)", DEGRADED_LEGACY, reason)

    async def ingest_capture(
        self,
        pcm: bytes,
        *,
        playing: bool,
        echo_window: bool,
        duration_ms: int,
        user_id: int,
        guild_id: int,
        authorized: bool,
    ) -> str:
        """Admit one capture chunk. Returns the classification."""
        if self.degraded:
            return "degraded"
        if not authorized:
            return "unauthorized"
        kind = classify_overlap(pcm, playing=playing, echo_window=echo_window, duration_ms=duration_ms)
        metrics = self.metrics or self.coordinator.metrics
        if kind == "echo":
            return kind
        if kind == "backchannel":
            return kind
        if kind == "takeover":
            await self.local_barge_in()
            return kind
        if kind != "speech":
            return kind
        bound = int(self.max_ingress_seconds * 48000 * 2 * 2)
        if self._ingress_bytes + len(pcm) > bound:
            self.mark_degraded("ingress_overflow")
            await self.fallback(guild_id=guild_id, user_id=user_id, pcm_data=pcm, reason="ingress_overflow")
            metrics.mark("fallback_ready")
            return "overflow"
        try:
            from plugins.platforms.discord.realtime_openai import pcm48_stereo_to_24k_mono
            await self.coordinator.send_audio(pcm48_stereo_to_24k_mono(pcm))
            self._ingress_bytes += len(pcm)
        except Exception as exc:
            self.mark_degraded(f"send_audio:{type(exc).__name__}")
            await self.fallback(guild_id=guild_id, user_id=user_id, pcm_data=pcm, reason=str(exc))
            metrics.mark("fallback_ready")
            return "fallback"
        return kind

    async def local_barge_in(self) -> None:
        """Local-first: stop mixer, emit heard receipt, then coordinator cancel/truncate."""
        mixer = self.mixer
        if mixer is not None and hasattr(mixer, "stop_speech"):
            mixer.stop_speech()
        (self.metrics or self.coordinator.metrics).mark("local_playback_silent")
        event = self._clock.event
        if event is not None and mixer is not None:
            self.coordinator.report_audio_heard(event, audio_end_ms=int(getattr(mixer, "played_through_ms", 0)))
        await self.coordinator.cancel_response()
        if mixer is not None and hasattr(mixer, "reset_playback_cursor"):
            mixer.reset_playback_cursor()
        self._clock = DuplexPlaybackClock()

    async def handle_provider_event(self, event: RealtimeEvent) -> None:
        if event.type is RealtimeEventType.AUDIO:
            await self._queue_playback(event)
        elif event.type in {RealtimeEventType.INPUT_TRANSCRIPT, RealtimeEventType.TRANSCRIPT} and event.final:
            turn_id = event.turn_id or "legacy"
            text = event.text or ""
            if turn_id in self.finalized_turns and self.finalized_turns[turn_id] != text:
                logger.warning("transcript reconciliation fault for turn %s", turn_id)
                return
            self.finalized_turns[turn_id] = text
            if self.transcript_sink is not None:
                self.transcript_sink(turn_id, text)
        elif event.type is RealtimeEventType.ERROR:
            self.mark_degraded(event.text or "provider_error")

    async def _queue_playback(self, event: RealtimeEvent) -> None:
        mixer = self.mixer
        if mixer is None:
            return
        pcm = event.audio_bytes or b""
        from plugins.platforms.discord.realtime_openai import pcm24_mono_to_48k_stereo
        stereo = pcm24_mono_to_48k_stereo(pcm)
        queued = mixer.queued_speech_ms() if hasattr(mixer, "queued_speech_ms") else 0
        if queued / 1000.0 > self.max_playback_seconds:
            self.mark_degraded("playback_overflow")
            return
        if self._clock.item_id != event.item_id:
            mixer.reset_playback_cursor()
            self._clock = DuplexPlaybackClock(item_id=event.item_id, event=event)
        else:
            self._clock.event = event
        mixer.play_speech(stereo)
        (self.metrics or self.coordinator.metrics).mark("first_audio_queued")

    def should_pause_receiver(self) -> bool:
        """Legacy half-duplex pauses capture during play; duplex never does."""
        return self.degraded


def openai_api_key_from_config(cfg: dict[str, Any]) -> str | None:
    duplex = cfg.get("discord_duplex") if "discord_duplex" in cfg else cfg
    key = (duplex or {}).get("api_key") if isinstance(duplex, dict) else None
    if key:
        return str(key)
    return os.getenv("OPENAI_API_KEY")
