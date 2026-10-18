"""Session-owned side-question history, separate from the main transcript."""
from .base import Payload, Result, WireEnum
from .common import SessionParams
from .registry import event, method


class BtwState(WireEnum):
    running = "running"
    answered = "answered"
    error = "error"
    cancelled = "cancelled"


class BtwTurn(Result):
    id: str
    question: str
    answer: str
    state: BtwState
    error: str | None = None


class BtwThread(Result):
    id: str
    revision: int
    turns: list[BtwTurn]


class BtwListResult(Result):
    threads: list[BtwThread]


class BtwSubmitParams(SessionParams):
    text: str
    thread_id: str | None = None


class BtwSubmitResult(Result):
    thread: BtwThread
    turn_id: str


class BtwCancelParams(SessionParams):
    thread_id: str
    turn_id: str


class BtwUpdatePayload(Payload):
    thread: BtwThread


method("btw.list", params=SessionParams, result=BtwListResult,
       doc="Read all side threads owned by this conversation, without main transcript entries.")
method("btw.submit", params=BtwSubmitParams, result=BtwSubmitResult,
       doc="Start a side question or continue an exact owned thread; streams btw.update snapshots.")
method("btw.cancel", params=BtwCancelParams, result=BtwSubmitResult,
       doc="Cancel only the exact running side turn, returning canonical readback.")
event("btw.update", BtwUpdatePayload, doc="Canonical side-thread snapshot after a streamed delta or state change.")
