"""BTW intents: durable gateway-owned threads, never main conversation messages."""
from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method


def _btw_prefix(owner):
    # JSON framing avoids prefix collisions between arbitrary imported session ids.
    return "btw:" + json.dumps(owner["session_key"]) + ":"


def _btw_read(conn, key):
    from tui_gateway.contracts.btw import BtwThread
    row = conn.execute("SELECT value FROM state_meta WHERE key = ?", (key,)).fetchone()
    return BtwThread.model_validate_json(row[0]).model_dump(mode="json") if row else None


def _btw_write(conn, key, thread):
    conn.execute("INSERT INTO state_meta (key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, json.dumps(thread)))


def _btw_change(owner, key, change):
    with _session_db(owner) as db:
        def update(conn):
            thread = _btw_read(conn, key)
            change(thread)
            thread["revision"] += 1
            _btw_write(conn, key, thread)
            return thread
        return db._execute_write(update)


def _btw_authority(rid, params):
    sid = params["session_id"]
    _, owner = _current_session_steer_authority(sid)
    if owner is None or not owner.get("session_key"):
        return None, _err(rid, 4001, "session not found or not owned by this transport")
    return owner, None


@method("btw.list")
@_registry.profile_scoped
def _btw_list(rid, params):
    owner, err = _btw_authority(rid, params)
    if err:
        return err
    from tui_gateway.contracts.btw import BtwThread
    from tui_gateway.btw_workers import worker_alive, worker_lock
    with worker_lock, _session_db(owner) as db:
        threads = []
        for key, raw in db.list_meta_prefix(_btw_prefix(owner)):
            thread = BtwThread.model_validate_json(raw).model_dump(mode="json")
            for turn in thread["turns"]:
                identity = json.loads(db.get_meta("btw-runtime:" + turn["id"]) or "{}")
                if turn["state"] == "running" and not worker_alive(identity, turn["id"]):
                    thread = _btw_finish(owner, params["session_id"], key, turn["id"], "cancelled", "",
                                         "Side worker stopped before completing; you can ask a follow-up.")
            threads.append(thread)
    return _ok(rid, {"threads": threads})


@method("btw.submit")
@_registry.profile_scoped
def _btw_submit(rid, params):
    from agent.interrupt_scope import InterruptScope
    from tui_gateway.btw_workers import workers, worker_lock, worker_identity

    owner, err = _btw_authority(rid, params)
    if err:
        return err
    text = params["text"].strip()
    if not text:
        return _err(rid, 4012, "text required")
    thread_id = params.get("thread_id") or "btw_" + uuid.uuid4().hex
    turn_id = "turn_" + uuid.uuid4().hex
    key = _btw_prefix(owner) + thread_id
    scope = InterruptScope()
    try:
        with worker_lock:
            with _session_db(owner) as db:
                def admit(conn):
                    thread = _btw_read(conn, key)
                    if thread is None:
                        if params.get("thread_id"):
                            raise ValueError("side thread not found in this session")
                        thread = {"id": thread_id, "revision": 0, "turns": []}
                    if any(turn["state"] == "running" for turn in thread["turns"]):
                        raise ValueError("side thread already has a running turn")
                    thread["turns"].append({"id": turn_id, "question": text, "answer": "",
                                             "state": "running", "error": None})
                    thread["revision"] += 1
                    _btw_write(conn, key, thread)
                    db.set_meta("btw-runtime:" + turn_id, json.dumps(worker_identity()), cursor=conn)
                    return thread
                thread = db._execute_write(admit)
            workers[turn_id] = scope
    except ValueError as exc:
        return _err(rid, 4000, str(exc))
    sid = params["session_id"]
    agent = owner.get("agent")
    snapshot = list(getattr(agent, "_session_messages", None) or owner.get("history") or [])
    # The main cached prefix is unchanged. Side history is data in the NEW side question.
    previous = thread["turns"][:-1]
    question = ("Previous turns in this side thread:\n" + json.dumps(previous, ensure_ascii=False)
                + "\n\nFollow-up question: " + text) if previous else text

    def run():
        _btw_run(owner, sid, key, turn_id, question, snapshot, agent, scope)

    if _start_session_work(run, name=f"btw-{turn_id}") is None:
        _btw_finish(owner, sid, key, turn_id, "error", "", "Backend is retiring; reconnect to continue.")
        with worker_lock:
            workers.pop(turn_id, None)
    with _session_db(owner) as db:
        current = db.get_meta(key)
    return _ok(rid, {"thread": json.loads(current), "turn_id": turn_id})


def _btw_emit(owner, thread):
    # A resume remints the UI id. Deliver to the live conversation, not the stale
    # id captured when its worker started; profile identity fences equal ids.
    with _sessions_lock:
        targets = [sid for sid, live in _sessions.items()
                   if live.get("session_key") == owner.get("session_key")
                   and live.get("profile_home") == owner.get("profile_home")]
    for target in targets:
        _emit("btw.update", target, {"thread": thread})


def _btw_finish(owner, sid, key, turn_id, state, answer, error=None):
    def finish(thread):
        turn = next(t for t in thread["turns"] if t["id"] == turn_id)
        if turn["state"] == "running":
            turn.update(state=state, answer=answer or turn["answer"], error=error)
    thread = _btw_change(owner, key, finish)
    _btw_emit(owner, thread)
    return thread


def _btw_run(owner, sid, key, turn_id, question, snapshot, agent, scope):
    from agent.interrupt_scope import bind_interrupt_scope
    from agent.side_question import answer_side_question
    from tui_gateway.btw_workers import workers, worker_lock

    tokens = _set_session_context(turn_id, cwd=_session_cwd(owner), ui_session_id=sid)
    try:
        def delta(text):
            if not text or scope.reason:
                return
            def append(thread):
                turn = next(t for t in thread["turns"] if t["id"] == turn_id)
                if turn["state"] == "running":
                    turn["answer"] += text
            thread = _btw_change(owner, key, append)
            _btw_emit(owner, thread)
        with _session_profile_runtime_scope(owner), bind_interrupt_scope(scope):
            answer = answer_side_question(question, snapshot, parent_agent=agent,
                                          stream_callback=delta, cancelled=lambda: bool(scope.reason))
            _btw_finish(owner, sid, key, turn_id, "cancelled" if scope.reason else "answered", answer)
    except Exception as exc:
        _btw_finish(owner, sid, key, turn_id, "error", "", str(exc))
    finally:
        with worker_lock:
            workers.pop(turn_id, None)
        _clear_session_context(tokens)


@method("btw.cancel")
@_registry.profile_scoped
def _btw_cancel(rid, params):
    from tui_gateway.btw_workers import workers, worker_lock

    owner, err = _btw_authority(rid, params)
    if err:
        return err
    key = _btw_prefix(owner) + params["thread_id"]
    with _session_db(owner) as db:
        raw = db.get_meta(key)
    thread = json.loads(raw) if raw else None
    turn = next((t for t in thread["turns"] if t["id"] == params["turn_id"]), None) if thread else None
    if turn is None:
        return _err(rid, 4000, "side turn not found in this session")
    with worker_lock:
        scope = workers.get(turn["id"])
        if turn["state"] == "running":
            if scope is None:
                return _err(rid, 4000, "Side worker unavailable; cannot confirm cancellation.")
            scope.cancel("Side question cancelled by user", tool_reason=None)
            thread = _btw_finish(owner, params["session_id"], key, turn["id"], "cancelled", "")
    return _ok(rid, {"thread": thread, "turn_id": turn["id"]})


def register(server):
    bind_module(globals(), server)
    server._LONG_HANDLERS = server._LONG_HANDLERS | _registry.names()
