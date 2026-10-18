"""Foreground call output belongs to a live session/turn/call generation, not a jobs sheet."""
import uuid

from tools.environments.base_output import _BoundedOutputCollector
from tools.tool_output_limits import get_max_bytes


def start(session: dict, payload: dict) -> None:
    if payload["name"] not in {"terminal", "bash", "shell"} or not session.get("inflight_turn"):
        return
    with session["history_lock"]:
        turn = session.get("inflight_turn")
        if not isinstance(turn, dict) or not turn.get("streaming"):
            return
        payload["turn_id"] = turn.setdefault("tool_turn_id", uuid.uuid4().hex)
        turn.setdefault("tool_outputs", {})[payload["tool_id"]] = {"start": dict(payload)}


def complete(session: dict, call_id: str) -> None:
    if not session.get("inflight_turn"):
        return
    with session["history_lock"]:
        turn = session.get("inflight_turn") or {}
        turn.get("tool_outputs", {}).pop(call_id, None)


def progress(session: dict, event: str, name: str, text: str | None, kw: dict) -> dict | None:
    with session["history_lock"]:
        turn = session.get("inflight_turn") or {}
        if not turn.get("streaming") or session.get("_finalized"):
            return None
        state = turn.get("tool_outputs", {}).get(kw.get("tool_call_id"))
        if state is None or state["start"]["name"] != name:
            return None
        if event == "tool.output.open":
            if "stream_id" not in state:
                state.update(stream_id=kw["stream_id"], seq=0, collector=_BoundedOutputCollector(get_max_bytes()))
            return None
        if not text or state.get("stream_id") != kw.get("stream_id"):
            return None
        collector = state["collector"]
        collector.append(text)
        state["seq"] += 1
        truncated = collector.total_chars > collector.max_chars
        payload = {
            "tool_id": kw["tool_call_id"], "turn_id": turn["tool_turn_id"],
            "stream_id": state["stream_id"], "seq": state["seq"], "output_kind": "terminal",
            "text": collector.render() if truncated else text,
            "operation": "replace" if truncated else "append", "capture_truncated": truncated,
        }
        state["output"] = {**payload, "text": collector.render(), "operation": "replace"}
        return payload


def snapshot(turn: dict) -> list[dict]:
    return [{"start": dict(state["start"]), **({"output": dict(state["output"])} if "output" in state else {})}
            for state in turn.get("tool_outputs", {}).values()]
