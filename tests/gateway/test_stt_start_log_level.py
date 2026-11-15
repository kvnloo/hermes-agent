"""The voice-transcription start marker is an INFO line: a hung STT call (slow local-model init on
the gateway host) otherwise leaves INFO logs ending at ``Cached user voice`` with no trace that
transcription ever started."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from gateway.config import GatewayConfig
from gateway.platforms.helpers import hash_for_log

VOICE_NOTE = Path(__file__).resolve().parents[1] / "fixtures" / "audio" / "voice_note.ogg"


@pytest.mark.asyncio
async def test_transcription_start_is_logged_at_info_before_stt_runs(tmp_path, caplog):
    from gateway.run import GatewayRunner

    clip = tmp_path / "audio_3f20dbc49b73.ogg"
    clip.write_bytes(VOICE_NOTE.read_bytes())
    runner = GatewayRunner.__new__(GatewayRunner)
    runner.config = GatewayConfig(stt_enabled=True)
    runner._has_setup_skill = lambda: False
    seen_before_stt = []

    def fake_stt(path, *_args):
        seen_before_stt.append([r.getMessage() for r in caplog.records if r.levelno >= logging.INFO])
        return {"success": True, "transcript": "hola", "provider": "local"}

    with caplog.at_level(logging.INFO, logger="gateway.run"), \
            patch("tools.transcription_tools.transcribe_audio", side_effect=fake_stt):
        result, transcripts = await runner._enrich_message_with_transcription("", [str(clip)])

    assert transcripts == ["hola"]
    assert seen_before_stt == [[f"Transcribing user voice: {hash_for_log(str(clip))}"]]
    assert str(clip) not in "\n".join(seen_before_stt[0])
    assert '"hola"' in result
