"""R26: an unviewed completion in a bot's canonical Bot Chat runs as a turn; other unviewed local sessions keep the note.

Defaults to the repo module; R26_MODULE overrides it:
  R26_MODULE=<path to session_completion_notes.py> venv/bin/python -m pytest -q <this file>
With the original module this fails (RED); with the fix it passes (GREEN). The real gateway helpers are
monkeypatched only where they need a live authority (ledger write, reopen, physical target).
"""
import asyncio, importlib.util, json, os
from types import SimpleNamespace

import pytest

MOD = os.environ.get("R26_MODULE", os.path.join(os.path.dirname(__file__), "..", "..", "gateway", "session_completion_notes.py"))


def load():
    spec = importlib.util.spec_from_file_location("scn_under_test", MOD)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


class DB:
    def __init__(self, bot_root="bot-root", tip="bot-tip"):
        self.bot_root, self.tip, self.notes = bot_root, tip, []

    def get_session_by_title(self, title):
        return {"id": self.bot_root} if title == "Bot Chat" and self.bot_root else None

    def get_compression_tip(self, sid):
        return self.tip if sid == self.bot_root else sid

    def append_completion_note(self, *a):
        self.notes.append(a)


def row(producer="async_delegation"):
    ident = json.dumps([producer, "deleg_f087f663", ""])
    return {"admission_id": "adm1", "payload": {"text": "[ASYNC DELEGATION BATCH COMPLETE]",
            "local_automation_v1": {"identity": ident, "display_kind": "async_delegation_complete"}}}


@pytest.fixture
def env(monkeypatch):
    import gateway.session_runtime_workers as w, gateway.session_local_recovery as rec, gateway.session_viewer_close as vc
    calls = []

    async def tracked_write(authority, write, then=None, **_):
        calls.append(write); return write()
    monkeypatch.setattr(w, "tracked_write", tracked_write)
    monkeypatch.setattr(rec, "reopen_local_session", lambda a, r: calls.append("reopen"))
    monkeypatch.setattr(vc, "_physical_target", lambda a, sid: sid)
    return calls


def authority(sid, db, subscribers=()):
    live = SimpleNamespace(subscribers=set(subscribers), route="agent:intake:local:dm:" + sid)
    return SimpleNamespace(sessions={sid: live}, db=db, runner=SimpleNamespace(), pending_results={})


def run(m, a, sid, r):
    return asyncio.run(m.note_if_unviewed(a, SimpleNamespace(session_id=sid), r))


@pytest.mark.parametrize("producer", ["async_delegation", "completion"])
@pytest.mark.parametrize("sid", ["bot-root", "bot-tip"])
def test_idle_bot_chat_wakes_as_turn(env, producer, sid):
    # intake 11-05: deleg_f087f663 finished 04:21:51 and was noted; the session idled until 05:29
    db = DB(); m = load()
    assert run(m, authority(sid, db), sid, row(producer)) is None   # None = executor runs the turn
    assert db.notes == [] and "reopen" in env


def test_unviewed_plain_local_session_still_gets_note(env):
    db = DB(); m = load(); a = authority("cli-1", db)
    assert run(m, a, "cli-1", row()) == ""
    assert len(db.notes) == 1 and "adm1" in a.pending_results


def test_viewed_session_runs_turn_unchanged(env):
    db = DB(); m = load()
    assert run(m, authority("cli-2", db, subscribers={"viewer"}), "cli-2", row()) is None and db.notes == []


def test_lookup_failure_falls_back_to_note(env):
    db = DB(); db.get_session_by_title = lambda t: (_ for _ in ()).throw(RuntimeError("db"))
    m = load(); assert run(m, authority("bot-root", db), "bot-root", row()) == ""
