"""Jobs sheet: no second store, and no authority inferred from a public job id."""

from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method


def _jobs_processes(owner):
    from tools.process_registry import process_registry

    key = str(owner.get("session_key") or "")
    if not key:
        return []  # An unset key is never proof of ownership.
    owned = []
    for entry in process_registry.list_sessions(session_key=key):
        proc = process_registry.get(entry["session_id"])
        if proc is not None and proc.id == entry["session_id"] and proc.session_key == key:
            owned.append(proc)
    return owned


def _jobs_resolve(session_id, job_id, transport, owner):
    proc = next((p for p in _jobs_processes(owner) if p.id == job_id), None)
    child = next((r for r in _owned_subagent_records(session_id, transport, owner)
                  if r.get("subagent_id") == job_id), None)
    return proc, child


@method("jobs.list")
@_registry.profile_scoped
def _jobs_list(rid, params):
    sid = _str_param(params, "session_id")
    transport, owner = _current_session_steer_authority(sid)
    if owner is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    jobs = []
    for proc in _jobs_processes(owner):
        state = "running"
        if proc.exited:
            state = "cancelled" if proc.completion_reason == "killed" else "completed" if proc.exit_code == 0 else "failed"
        jobs.append({"id": proc.id, "kind": "process", "title": proc.command[:200],
                     "state": state, "started": proc.started_at, "owner_session_id": sid,
                     "parent_id": None})
    for record in _owned_subagent_records(sid, transport, owner):
        jobs.append({"id": record["subagent_id"], "kind": "subagent", "title": record.get("goal") or "Subagent",
                     "state": record.get("status") or "running", "started": record.get("started_at") or 0,
                     "owner_session_id": sid, "parent_id": record.get("parent_id")})
    return _ok(rid, {"jobs": jobs})


@method("jobs.tail")
@_registry.profile_scoped
def _jobs_tail(rid, params):
    sid = _str_param(params, "session_id")
    transport, owner = _current_session_steer_authority(sid)
    if owner is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    job_id = params["job_id"]
    proc, child = _jobs_resolve(sid, job_id, transport, owner)
    if proc is None and child is None:
        return _err(rid, 4044, "job not found or not owned by this session")
    available, truncated = True, False
    if proc is not None:
        with proc._lock:
            text = proc.output_buffer
    else:
        result = _methods["subagent.tail"](rid, {"session_id": sid, "subagent_id": job_id})
        if "error" in result:
            return result
        snapshot = result["result"]
        text, available, truncated = snapshot["text"], snapshot["available"], snapshot["truncated"]
    count = params.get("lines", 100)
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 500:
        return _err(rid, 4000, "lines must be an integer from 1 to 500")
    bounded = text.encode("utf-8")[-16384:].decode("utf-8", errors="ignore")
    lines = bounded.splitlines()
    return _ok(rid, {"job_id": job_id, "text": "\n".join(lines[-count:]), "available": available,
                     "truncated": truncated or len(text) > len(bounded) or len(lines) > count})


@method("jobs.cancel")
@_registry.profile_scoped
def _jobs_cancel(rid, params):
    from tools.process_registry import process_registry

    sid = _str_param(params, "session_id")
    transport, owner = _current_session_steer_authority(sid)
    if owner is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    job_id = params["job_id"]
    proc, child = _jobs_resolve(sid, job_id, transport, owner)
    if proc is None and child is None:
        return _err(rid, 4044, "job not found or not owned by this session")
    if _current_session_steer_authority(sid)[1] is not owner:
        return _err(rid, 4001, "session authority changed before cancellation")
    if proc is not None:
        if proc.exited:
            return _ok(rid, {"job_id": job_id, "accepted": False})
        result = process_registry.kill_process(proc.id, source="jobs.cancel", consume_output=False)
        if result.get("error") or result.get("scope_stop_failed"):
            return _err(rid, 5010, result.get("error") or "Job scope did not stop")
        accepted = result.get("status") in ("killed", "already_exited", "exited")
    else:
        result = _methods["subagent.interrupt"](rid, {"session_id": sid, "subagent_id": job_id})
        if "error" in result:
            return result
        accepted = result["result"]["found"]
    return _ok(rid, {"job_id": job_id, "accepted": accepted})


def register(server):
    bind_module(globals(), server)
    server._LONG_HANDLERS = server._LONG_HANDLERS | _registry.names()
