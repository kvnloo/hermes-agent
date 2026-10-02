"""Tests for tui_gateway.loop_noise — the WS peer-hangup teardown filter (#50005)."""

from __future__ import annotations

import asyncio

import pytest

from tui_gateway.loop_noise import (
    _is_benign_teardown,
    install_loop_noise_filter,
)


class _FakeConnectionLostCallback:
    """Stand-in whose repr matches asyncio's ``_call_connection_lost`` flood."""

    def __repr__(self) -> str:
        return "<Handle _ProactorBasePipeTransport._call_connection_lost(None)>"


def test_benign_teardown_matches_reset_in_connection_lost():
    ctx = {
        "exception": ConnectionResetError(10054, "forcibly closed"),
        "handle": _FakeConnectionLostCallback(),
    }
    assert _is_benign_teardown(ctx) is True


def test_benign_teardown_matches_aborted_and_broken_pipe():
    for exc in (
        ConnectionAbortedError(10053, "aborted"),
        BrokenPipeError("epipe"),
    ):
        ctx = {"exception": exc, "callback": _FakeConnectionLostCallback()}
        assert _is_benign_teardown(ctx) is True


def test_reset_outside_connection_lost_is_not_suppressed():
    # Same error type, but NOT from the connection-lost teardown path — must
    # fall through to the default handler.
    ctx = {
        "exception": ConnectionResetError("reset in a real handler"),
        "handle": "<Handle some_other_handler()>",
    }
    assert _is_benign_teardown(ctx) is False


def test_unrelated_exception_is_not_suppressed():
    ctx = {
        "exception": ValueError("boom"),
        "handle": _FakeConnectionLostCallback(),
    }
    assert _is_benign_teardown(ctx) is False


def test_no_exception_is_not_suppressed():
    assert _is_benign_teardown({"message": "loop warning, no exc"}) is False


def _shielded_ctx(exc: BaseException) -> dict:
    # Shape of the context Python 3.14's asyncio.shield() reports when the shielded
    # future fails after the outer await was cancelled (cpython gh-156321).
    return {"message": f"{type(exc).__name__} exception in shielded future", "exception": exc}


def test_closed_websocket_in_shielded_future_is_benign():
    from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
    from websockets.frames import Close, CloseCode

    timeout = ConnectionClosedError(None, Close(CloseCode.INTERNAL_ERROR, "keepalive ping timeout"), None)
    assert _is_benign_teardown(_shielded_ctx(timeout)) is True
    assert _is_benign_teardown(_shielded_ctx(ConnectionClosedOK(None, None, None))) is True


def test_other_errors_in_shielded_future_are_not_suppressed():
    assert _is_benign_teardown(_shielded_ctx(RuntimeError("real bug"))) is False
    assert _is_benign_teardown(_shielded_ctx(ConnectionResetError("reset"))) is False


def test_closed_websocket_outside_shield_is_not_suppressed():
    from websockets.exceptions import ConnectionClosedOK

    ctx = {"message": "Task exception was never retrieved", "exception": ConnectionClosedOK(None, None, None)}
    assert _is_benign_teardown(ctx) is False


def test_install_suppresses_flood_and_forwards_real_errors():
    loop = asyncio.new_event_loop()
    try:
        forwarded: list[dict] = []
        loop.set_exception_handler(lambda _loop, ctx: forwarded.append(ctx))

        install_loop_noise_filter(loop)

        # Benign teardown flood → swallowed, not forwarded.
        loop.call_exception_handler(
            {
                "exception": ConnectionResetError(10054, "forcibly closed"),
                "handle": _FakeConnectionLostCallback(),
            }
        )
        assert forwarded == []

        # Genuine loop error → forwarded to the previous handler unchanged.
        real_ctx = {"exception": RuntimeError("genuine loop bug")}
        loop.call_exception_handler(real_ctx)
        assert len(forwarded) == 1
        assert forwarded[0] is real_ctx
    finally:
        loop.close()






@pytest.mark.parametrize("kind,cancelled,expected_forwarded", [
    ("websocket", True, 0),
    ("application", True, 1),
    ("websocket", False, 0),
], ids=["cancelled-peer-hangup", "cancelled-real-error", "uncancelled-retrieval"])
def test_real_shield_report_reaches_installed_filter(
        caplog, record_property, kind, cancelled, expected_forwarded):
    """Use asyncio's own report, including its owned Future, rather than a context fixture."""
    import json
    import logging

    from websockets.exceptions import ConnectionClosedError
    from websockets.frames import Close, CloseCode

    def exercise(filtered):
        loop = asyncio.new_event_loop()
        reports = []
        loop.set_exception_handler(lambda _loop, context: reports.append(context))
        if filtered:
            install_loop_noise_filter(loop)
        error = (ConnectionClosedError(None, Close(CloseCode.INTERNAL_ERROR, "keepalive ping timeout"), None)
                 if kind == "websocket" else RuntimeError("real application failure"))

        async def finish():
            inner = loop.create_future()
            outer = asyncio.shield(inner)
            if cancelled:
                outer.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await outer
                await asyncio.sleep(0)  # Let shield install its actual cancellation callback.
            inner.set_exception(error)
            assert inner.exception() is error  # The owning code retrieves the failure.
            if not cancelled:
                with pytest.raises(type(error)):
                    await outer
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            return inner, outer

        try:
            inner, outer = loop.run_until_complete(finish())
            assert inner.done() and not inner.cancelled()
            assert outer.cancelled() is cancelled
            for report in reports:
                assert report["exception"] is error and report["future"] is inner
                assert report["message"] == f"{type(error).__name__} exception in shielded future"
            return {"forwarded": len(reports), "inner_cancelled": inner.cancelled(),
                    "outer_cancelled": outer.cancelled(), "owner_retrieved": True}
        finally:
            loop.close()

    unfiltered = exercise(False)
    if cancelled and not unfiltered["forwarded"]:
        pytest.skip("This interpreter does not emit the shielded-future cancellation report")
    assert unfiltered["forwarded"] == int(cancelled)
    caplog.set_level(logging.DEBUG, logger="tui_gateway.loop_noise")
    caplog.clear()
    filtered = exercise(True)
    debug = [r for r in caplog.records if r.name == "tui_gateway.loop_noise"
             and "ws peer hangup during teardown" in r.getMessage()]
    record_property("shield_consumer_observation", json.dumps(
        {"unfiltered": unfiltered, "filtered": filtered, "debug_count": len(debug)}, sort_keys=True))
    assert filtered["forwarded"] == expected_forwarded
    assert len(debug) == int(kind == "websocket" and cancelled)
