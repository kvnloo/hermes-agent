"""Recovery-ledger contract for oversized finalized ``edit_message`` replies.

``edit_message(finalize=True)`` must record the delivery in the SQLite
``discord_messages`` recovery ledger via ``_record_discord_response`` so
missed-message backfill can mark the user's source message
``status='responded', replied=1`` and advance the per-channel recovery
cursor past it. Every finalize delivery path honored this contract
except the two ``_edit_overflow_split`` early returns (pre-flight and
reactive 50035) — they returned without recording the ledger, leaving
the row incomplete and the cursor un-advanced. When
``DISCORD_MISSED_MESSAGE_BACKFILL`` was enabled this caused wasteful
re-scans (any ``reply_to_mode``) and, under ``reply_to_mode: off``,
duplicate agent turns on reconnect.

These tests pin the contract for both overflow branches and guard the
adjacent paths (partial-overflow success, first-chunk failure, mid-stream
non-finalize, and the no-``reply_to`` no-op) against regression.
"""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import PlatformConfig


# The gateway conftest installs the discord mock at import time, so we can
# import the adapter directly (the approved plugin-adapter import pattern).
from plugins.platforms.discord.adapter import DiscordAdapter  # noqa: E402


MAX = DiscordAdapter.MAX_MESSAGE_LENGTH  # 2000


class FakeChannel:
    def __init__(self, channel_id=555):
        self.id = channel_id
        self.parent_id = None
        self.name = "c"
        self.guild = SimpleNamespace(id=777, name="g")

    def get_partial_message(self, mid):
        return self._msg

    async def send(self, *, content, reference=None):
        if self._send_side_effect is not None:
            res = self._send_side_effect(content, reference)
            if res is not None:
                return res
        sent = SimpleNamespace(
            id=self._next_id,
            content=content,
            reference=reference,
            to_reference=MagicMock(return_value=SimpleNamespace(kind="ref")),
            channel=self,
        )
        self._next_id += 1
        return sent


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("DISCORD_MISSED_MESSAGE_BACKFILL", "true")
    a = DiscordAdapter(PlatformConfig(enabled=True, token="***"))
    a._client = SimpleNamespace(
        user=SimpleNamespace(id=999, bot=True, display_name="Hermes", name="hermes"),
        get_channel=lambda _cid: None,
        fetch_channel=AsyncMock(),
    )
    a._ready_event.set()
    return a


def _wire(adapter, *, original_id=42, send_side_effect=None):
    channel = FakeChannel()
    channel._next_id = 9000
    channel._send_side_effect = send_side_effect
    edits = []
    msg = SimpleNamespace(
        id=original_id,
        edit=AsyncMock(side_effect=lambda *, content: edits.append(content)),
        to_reference=MagicMock(return_value=SimpleNamespace(kind="ref")),
    )
    channel._msg = msg
    adapter._client.get_channel = lambda _cid: channel
    adapter._client.fetch_channel = AsyncMock(return_value=channel)
    return channel, edits


def _seed_source_message(adapter, *, message_id="91", channel_id=555):
    """Insert the user source-message row the ledger will mark complete."""
    channel = SimpleNamespace(
        id=channel_id, parent_id=None, name="c",
        guild=SimpleNamespace(id=777, name="g"),
    )
    message = SimpleNamespace(
        id=int(message_id),
        content="please reply",
        author=SimpleNamespace(id=42, bot=False, display_name="Emo", name="emo"),
        channel=channel,
        guild=channel.guild,
        created_at=datetime.now(timezone.utc),
        attachments=[],
        mentions=[],
        reference=None,
    )
    adapter._record_discord_message_seen(message, status="processing")
    return message


_OVERFLOW_ERROR = RuntimeError(
    "400 Bad Request (error code: 50035): Invalid Form Body\n"
    "In content: Must be 2000 or fewer in length."
)


# --------------------------------------------------------------------------- #
# Baseline — in-place finalize still records (no regression)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_in_place_finalize_records_ledger(adapter):
    _seed_source_message(adapter)
    channel, edits = _wire(adapter)
    result = await adapter.edit_message(
        "555", "42", "short final", finalize=True,
        metadata={"reply_to_message_id": "91", "notify": True},
    )
    assert result.success is True
    assert result.continuation_message_ids == ()
    assert adapter._discord_message_is_persistently_complete("91") is True
    assert adapter._discord_recovery_cursor("555") == "91"


# --------------------------------------------------------------------------- #
# Pre-flight overflow — the hot path for verbose final replies
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_preflight_overflow_finalize_records_ledger(adapter):
    _seed_source_message(adapter)
    channel, edits = _wire(adapter)
    big = "q" * (MAX + 4000)
    result = await adapter.edit_message(
        "555", "42", big, finalize=True,
        metadata={"reply_to_message_id": "91", "notify": True},
    )
    assert result.success is True
    assert result.continuation_message_ids, "expected the overflow split path"
    assert adapter._discord_message_is_persistently_complete("91") is True
    assert adapter._discord_recovery_cursor("555") == "91"


# --------------------------------------------------------------------------- #
# Reactive 50035 overflow — pre-flight passed, Discord still rejected
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_reactive_overflow_finalize_records_ledger(adapter):
    _seed_source_message(adapter)
    edits = []
    calls = []

    def edit_effect(*, content):
        calls.append(content)
        if len(calls) == 1:
            raise _OVERFLOW_ERROR
        edits.append(content)

    msg = SimpleNamespace(
        id=42, edit=AsyncMock(side_effect=edit_effect),
        to_reference=MagicMock(return_value=SimpleNamespace(kind="ref")),
    )
    channel = FakeChannel()
    channel._next_id = 9000
    channel._send_side_effect = None
    channel._msg = msg
    adapter._client.get_channel = lambda _cid: channel
    adapter._client.fetch_channel = AsyncMock(return_value=channel)

    result = await adapter.edit_message(
        "555", "42", "u" * 1500, finalize=True,
        metadata={"reply_to_message_id": "91", "notify": True},
    )
    assert result.success is True
    assert adapter._discord_message_is_persistently_complete("91") is True
    assert adapter._discord_recovery_cursor("555") == "91"


# --------------------------------------------------------------------------- #
# Partial-overflow success — still mark ledger to prevent duplicate re-dispatch
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_partial_overflow_finalize_records_ledger(adapter):
    _seed_source_message(adapter)

    # channel.send always raises so a continuation chunk fails both the
    # reference and the no-reference retry → _edit_overflow_split returns
    # success=True with a partial_overflow raw_response.
    def send_always_fail(content, reference=None):
        raise RuntimeError("connection reset")

    channel, edits = _wire(adapter, send_side_effect=send_always_fail)
    big = "q" * (MAX + 4000)  # multiple chunks
    result = await adapter.edit_message(
        "555", "42", big, finalize=True,
        metadata={"reply_to_message_id": "91", "notify": True},
    )
    assert result.success is True, "partial overflow reports success by design"
    assert result.raw_response.get("partial_overflow") is True
    # The user saw chunk 1 in place — a duplicate re-dispatch would re-send it.
    assert adapter._discord_message_is_persistently_complete("91") is True
    assert adapter._discord_recovery_cursor("555") == "91"


# --------------------------------------------------------------------------- #
# First-chunk edit fails — do NOT mark responded; leave it retryable
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_overflow_finalize_failure_leaves_row_unresponded(adapter):
    _seed_source_message(adapter)
    # msg.edit raises a NON-overflow error on the first chunk edit inside
    # _edit_overflow_split → it returns success=False (a real adapter problem).
    def edit_effect(*, content):
        raise RuntimeError("boom: not an overflow error")

    msg = SimpleNamespace(
        id=42, edit=AsyncMock(side_effect=edit_effect),
        to_reference=MagicMock(return_value=SimpleNamespace(kind="ref")),
    )
    channel = FakeChannel()
    channel._next_id = 9000
    channel._send_side_effect = None
    channel._msg = msg
    adapter._client.get_channel = lambda _cid: channel
    adapter._client.fetch_channel = AsyncMock(return_value=channel)

    result = await adapter.edit_message(
        "555", "42", "q" * (MAX + 4000), finalize=True,
        metadata={"reply_to_message_id": "91", "notify": True},
    )
    assert result.success is False
    assert adapter._discord_message_is_persistently_complete("91") is False
    # Cursor must not advance past a failed delivery.
    assert adapter._discord_recovery_cursor("555") is None


# --------------------------------------------------------------------------- #
# Mid-stream (finalize=False) — never records the final-delivery ledger
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_midstream_overflow_does_not_record_final(adapter):
    _seed_source_message(adapter)
    channel, edits = _wire(adapter)
    result = await adapter.edit_message(
        "555", "42", "q" * (MAX + 4000), finalize=False,
        metadata={"reply_to_message_id": "91", "notify": False},
    )
    assert result.success is True
    assert result.continuation_message_ids == ()
    # finalize=False must not mark the turn complete — the reply is still streaming.
    assert adapter._discord_message_is_persistently_complete("91") is False
    assert adapter._discord_recovery_cursor("555") is None


# --------------------------------------------------------------------------- #
# No reply_to — _record_discord_response is a no-op (unchanged behavior)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_overflow_finalize_without_reply_to_skips_ledger(adapter):
    channel, edits = _wire(adapter)
    result = await adapter.edit_message(
        "555", "42", "q" * (MAX + 4000), finalize=True,
        metadata={"notify": True},
    )
    assert result.success is True
    assert result.continuation_message_ids
    # No row was seeded and no reply_to was provided → nothing to mark complete.
    assert adapter._discord_message_is_persistently_complete("91") is False


# --------------------------------------------------------------------------- #
# Off-event-loop contract: the ledger write does not block edit_message's return
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_overflow_finalize_offloads_ledger_write(adapter, monkeypatch):
    _seed_source_message(adapter)
    channel, edits = _wire(adapter)
    import time

    def slow_record(**_kwargs):
        time.sleep(0.1)

    monkeypatch.setattr(adapter, "_record_discord_response", slow_record)
    sending = asyncio.create_task(adapter.edit_message(
        "555", "42", "q" * (MAX + 4000), finalize=True,
        metadata={"reply_to_message_id": "91", "notify": True},
    ))
    await asyncio.sleep(0.01)
    assert sending.done() is False, "edit_message must stay non-blocking while the ledger write is offloaded"
    assert (await sending).success is True


# --------------------------------------------------------------------------- #
# End-to-end backfill decision — reply_to_mode: off must not re-dispatch
# --------------------------------------------------------------------------- #


async def _async_gen(messages):
    for m in messages:
        yield m


@pytest.mark.asyncio
async def test_overflow_finalize_prevents_redispatch_under_reply_to_off(adapter):
    """Under reply_to_mode: off + backfill enabled, a finalized oversized
    reply must mark the ledger so `_should_backfill_discord_message` returns
    False — preventing a duplicate agent turn on reconnect.

    reply_to_mode: off drops the reply reference, so the history-scan
    mitigation in `_message_has_non_down_bot_response` cannot mask a missing
    ledger write; the persistently-complete row is the only thing standing
    between the user's message and a re-dispatch. The 10-min processing claim
    is staled out so the decision falls through to that check (mirrors a
    reconnect long after the original processing started).
    """
    import datetime as _dt

    adapter._reply_to_mode = "off"

    channel, edits = _wire(adapter)
    user_message = SimpleNamespace(
        id=91,
        content="please reply at length",
        author=SimpleNamespace(id=42, bot=False, display_name="Emo", name="emo"),
        channel=channel,
        guild=channel.guild,
        created_at=datetime.now(timezone.utc),
        attachments=[],
        mentions=[],
        reference=None,
        thread=None,
        type=None,
    )
    adapter._record_discord_message_seen(user_message, status="processing")

    # Expire the 10-minute processing claim so the backfill decision cannot
    # shortcut on it — it must rely on the persistently-complete row state.
    stale = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=11)).isoformat()

    def _stale_claim(conn):
        conn.execute(
            "UPDATE discord_messages SET updated_at=? WHERE message_id=?",
            (stale, "91"),
        )

    adapter._with_discord_recovery_db(_stale_claim)

    # Channel history surfaces the in-place-edited placeholder — a bot message
    # with NO reference back to the user (the reply_to_mode: off case).
    placeholder = SimpleNamespace(
        id=42, content="...",
        author=SimpleNamespace(id=999, bot=True),
        reference=None,
        created_at=datetime.now(timezone.utc),
    )
    channel.history = lambda **kw: _async_gen([placeholder])

    result = await adapter.edit_message(
        "555", "42", "q" * (MAX + 4000), finalize=True,
        metadata={"reply_to_message_id": "91", "notify": True},
    )
    assert result.success is True
    assert adapter._discord_message_is_persistently_complete("91") is True

    # The fix's payoff: backfill does NOT re-dispatch the user's message,
    # even under reply_to_mode: off (no reference to mask a missing ledger).
    assert await adapter._should_backfill_discord_message(user_message) is False

