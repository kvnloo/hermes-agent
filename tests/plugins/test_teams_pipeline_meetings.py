from __future__ import annotations

from pathlib import Path

import pytest

from plugins.teams_pipeline.meetings import (
    TeamsMeetingArtifactNotFoundError,
    TeamsMeetingError,
    TeamsMeetingNotFoundError,
    download_transcript_text,
    fetch_preferred_transcript_text,
    resolve_meeting_reference,
)
from plugins.teams_pipeline.models import MeetingArtifact, TeamsMeetingRef
from tools.microsoft_graph_client import MicrosoftGraphAPIError


class FakeGraphClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def get_json(self, path, *, params=None):
        self.calls.append((path, params))
        return self.payload


@pytest.mark.anyio
async def test_join_url_can_use_organizer_scoped_graph_lookup():
    client = FakeGraphClient({"value": [{"id": "meeting-1", "joinWebUrl": "https://teams.microsoft.com/meet/code"}]})

    meeting = await resolve_meeting_reference(
        client,
        join_web_url="https://teams.microsoft.com/meet/code",
        organizer_user_id="organizer-1",
    )

    assert meeting.meeting_id == "meeting-1"
    assert meeting.organizer_user_id == "organizer-1"
    assert client.calls == [
        (
            "/users/organizer-1/onlineMeetings",
            {"$filter": "JoinWebUrl eq 'https://teams.microsoft.com/meet/code'"},
        )
    ]


@pytest.mark.anyio
async def test_transcript_download_requests_graph_vtt_content():
    class FakeDownloadClient:
        def __init__(self):
            self.calls = []

        async def download_to_file(self, path, destination, *, headers=None):
            self.calls.append((path, headers))
            Path(destination).write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<v Speaker>Hello</v>\n",
                encoding="utf-8",
            )
            return {"content_type": "text/vtt"}

    client = FakeDownloadClient()
    meeting = TeamsMeetingRef(
        meeting_id="meeting-1",
        organizer_user_id="organizer-1",
    )
    transcript = MeetingArtifact(
        artifact_type="transcript",
        artifact_id="transcript-1",
        display_name="transcript.vtt",
    )

    text = await download_transcript_text(client, meeting, transcript)

    assert text.startswith("WEBVTT")
    assert client.calls == [
        (
            "/users/organizer-1/onlineMeetings/meeting-1/transcripts/transcript-1/content",
            {"Accept": "text/vtt"},
        )
    ]


def _transcript_payload(transcript_id="tx-1", *, status="running"):
    return {
        "id": transcript_id,
        "displayName": "meeting.vtt",
        "status": status,
        "lastModifiedDateTime": "2026-05-01T00:00:00Z",
    }


class _ContentNotFoundClient:
    """Transcript listing succeeds; the transcript /content endpoint 404s."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def collect_paginated(self, path, *, params=None, headers=None):
        self.calls.append(("list", path))
        return [self.payload]

    async def download_to_file(self, path, destination, *, headers=None):
        self.calls.append(("download", path, headers))
        raise MicrosoftGraphAPIError(404, "GET", path, "Not found")


@pytest.mark.anyio
async def test_transcript_content_404_returns_none_none_not_raises():
    """A 404 from the transcript content endpoint must fall back, not hard-fail."""
    client = _ContentNotFoundClient(_transcript_payload("tx-404"))
    meeting = TeamsMeetingRef(meeting_id="meeting-1", organizer_user_id="organizer-1")

    artifact, text = await fetch_preferred_transcript_text(client, meeting)

    assert artifact is None
    assert text is None
    # The transcript content endpoint was hit (not just the listing).
    assert ("download", "/users/organizer-1/onlineMeetings/meeting-1/transcripts/tx-404/content", {"Accept": "text/vtt"}) in client.calls


@pytest.mark.anyio
async def test_download_transcript_text_non_404_error_still_wraps_as_meeting_error():
    """A non-404 Graph failure from the content download still surfaces as a meeting error."""

    class ErrorDownloadClient:
        async def download_to_file(self, path, destination, *, headers=None):
            raise MicrosoftGraphAPIError(
                500, "GET", path, "Internal Server Error", payload={"error": {"code": "InternalError"}}
            )

    client = ErrorDownloadClient()
    meeting = TeamsMeetingRef(meeting_id="meeting-1", organizer_user_id="organizer-1")
    transcript = MeetingArtifact(
        artifact_type="transcript",
        artifact_id="transcript-1",
        display_name="transcript.vtt",
    )

    # A 500 must not be swallowed as an artifact-not-found fallback signal.
    with pytest.raises(TeamsMeetingError) as exc_info:
        await download_transcript_text(client, meeting, transcript)

    assert not isinstance(exc_info.value, TeamsMeetingArtifactNotFoundError)
    assert not isinstance(exc_info.value, TeamsMeetingNotFoundError)
