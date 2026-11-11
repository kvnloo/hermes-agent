"""Off-turn approvals use the captured chat, never a completed native stream."""
from concurrent.futures import Future
from types import SimpleNamespace

import pytest

import gateway.run  # load bootstrap before the per-test home I/O guard
from gateway.config import Platform
from gateway.session import SessionSource
from gateway.turn_context import TurnContext

_CHAT = SessionSource(platform=Platform.TELEGRAM, chat_id="a", chat_type="dm", user_id="u")
from gateway.run_turn_runner import TurnRunner
from gateway.run_turn_runner_approval_transport import approval_transport


def test_background_prompt_ignores_completed_stream(monkeypatch):
    sent = []

    class Adapter:
        async def send(self, chat_id, text, metadata=None):
            sent.append((chat_id, metadata))
            return SimpleNamespace(success=True)

        def pause_typing_for_chat(self, chat_id):
            raise AssertionError("completed turn typing state was reused")

    ctx = TurnContext(session_key="chat-a", source=_CHAT, _status_adapter_pinned=Adapter(),
                      _status_chat_id="a", _status_thread_metadata={"thread_id": "t"},
                      _run_still_current=lambda: False)
    turn = TurnRunner(None, ctx)

    def schedule(self, coro, *args):
        import asyncio
        fut = Future()
        fut.set_result(asyncio.run(coro))
        return fut

    monkeypatch.setattr(TurnRunner, "_schedule", schedule)
    transport = approval_transport(turn)
    ctx._status_chat_id = "new-chat"
    transport.background_notify({"command": "print(1)", "description": "test"})
    assert sent[0][0] == "a"
    assert sent[0][1]["thread_id"] == "t"
    assert sent[0][1]["is_approval_prompt"] is True


@pytest.mark.parametrize("buttons", [False, True])
def test_background_transport_refusal_fails_closed(monkeypatch, buttons):
    import asyncio

    sent = []

    class Adapter:
        async def send(self, *args, **kwargs):
            sent.append("text")
            return SimpleNamespace(success=False)

    class ButtonAdapter(Adapter):
        async def send_exec_approval(self, **kwargs):
            sent.append((kwargs["chat_id"], kwargs["session_key"]))
            return SimpleNamespace(success=False)

    ctx = TurnContext(session_key="origin-session", _status_chat_id="origin-chat", source=_CHAT,
                      _status_adapter_pinned=ButtonAdapter() if buttons else Adapter())
    transport = approval_transport(TurnRunner(None, ctx))

    def schedule(self, coro, *args):
        fut = Future()
        fut.set_result(asyncio.run(coro))
        return fut

    monkeypatch.setattr(TurnRunner, "_schedule", schedule)
    monkeypatch.setattr(gateway.run, "_approval_send_outcome", lambda *args, **kw: "declined")
    with pytest.raises(RuntimeError):
        transport.background_notify({"command": "print(1)"})
    assert sent == [("origin-chat", "origin-session")] if buttons else sent == ["text"]


def test_background_text_send_timeout_keeps_delivered_prompt_answerable(monkeypatch):
    """A delayed send receipt must not orphan a text prompt already visible in chat."""
    import asyncio
    import threading
    from concurrent.futures import TimeoutError as FutureTimeoutError

    from tools import approval
    from tools.approval_context import reset_current_session_key, set_current_session_key
    from tools.approval_notify_lease import acquire, run

    key = "background-text-ambiguous-receipt"
    sent = []
    scheduled, finished = threading.Event(), threading.Event()
    decisions = []

    class TextOnlyAdapter:
        typed_command_prefix = "/"

        async def send(self, chat_id, message, metadata=None):
            sent.append((chat_id, message))
            return SimpleNamespace(success=True, message_id="visible-prompt")

    class LateReceipt:
        def result(self, timeout=None):
            assert timeout == 15  # production receipt wait; never shorten it in this test
            scheduled.set()
            raise FutureTimeoutError()

    def schedule(self, coro, *args):
        asyncio.run(coro)  # the chat has already received the message; only its receipt stalls
        return LateReceipt()

    monkeypatch.setattr(TurnRunner, "_schedule", schedule)
    monkeypatch.setattr(approval.approval_context, "_get_approval_mode", lambda: "manual")
    monkeypatch.setattr(approval, "_presence", lambda cb=None: (None, False, True, False))

    ctx = TurnContext(session_key=key, source=_CHAT, _status_adapter_pinned=TextOnlyAdapter(),
                      _status_chat_id="a", _status_thread_metadata={},
                      _run_still_current=lambda: False)
    transport = approval_transport(TurnRunner(None, ctx))
    approval.register_gateway_notify(key, transport)
    lease = acquire(key)
    approval.unregister_gateway_notify(key)  # the parent has replied

    def child():
        token = set_current_session_key(key)
        try:
            decisions.append(run(lease, lambda: approval.check_execute_code_guard("print('safe')", "local")))
        finally:
            reset_current_session_key(token)
            finished.set()

    thread = threading.Thread(target=child)
    thread.start()
    try:
        assert scheduled.wait(5), "the background text prompt must be attempted"
        assert len(sent) == 1 and sent[0][0] == "a"
        assert not finished.wait(2), "a late text receipt is not proof of failed delivery"
        assert approval.has_blocking_approval(key), "/approve must find the delivered text request"
        assert approval.resolve_gateway_approval(key, "once") == 1
        assert finished.wait(5)
        assert decisions[0]["approved"] is True
    finally:
        lease.release()
        thread.join(5)
        approval.unregister_gateway_notify(key)
        with approval._lock:
            approval._gateway_queues.pop(key, None)
