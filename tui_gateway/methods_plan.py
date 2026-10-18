"""Revision-checked plan intents; transport ownership is checked on every call."""
from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method


def _plan_request(rid, params, model, operation):
    from pydantic import ValidationError
    from .plan_review import plan_state

    try:
        parsed = model.model_validate(params)
    except ValidationError as exc:
        return _err(rid, 4000, str(exc))
    sid = parsed.session_id
    _, session = _current_session_steer_authority(sid)
    if session is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    state = plan_state(session)
    with state["lock"]:
        if _current_session_steer_authority(sid)[1] is not session:
            return _err(rid, 4001, "session authority changed")
        return operation(parsed, session, state)


def _plan_target(rid, params, session, state):
    from .plan_review import plan_snapshot

    plan = plan_snapshot(session)["plan"]
    if (session.get("running") or state["generating"] or not state["enabled"] or not plan
            or plan["id"] != params.plan_id or plan["revision"] != params.revision
            or plan["decision"] != "pending"):
        return _err(rid, 4094, "Plan changed, is unavailable, or was already decided. Reopen plan review.")
    return None


@method("plan.status")
@_registry.profile_scoped
def _plan_status(rid, params):
    from .contracts.common import SessionParams
    from .plan_review import plan_snapshot
    return _plan_request(rid, params, SessionParams,
                         lambda p, session, state: _ok(rid, plan_snapshot(session)))


@method("plan.mode")
@_registry.profile_scoped
def _plan_mode(rid, params):
    from .contracts.plans import PlanModeParams
    from .plan_review import plan_snapshot

    def apply(p, session, state):
        if session.get("running"):
            return _err(rid, 4009, "Cannot change plan mode during a turn")
        # Isolated/provider-owned execution cannot enforce this local tool policy.
        agent = session.get("agent")
        if p.enabled and (_session_uses_compute_host(session) or str(getattr(agent, "base_url", "")).startswith("acp://")):
            return _err(rid, 4094, "Plan enforcement is unavailable for this execution transport")
        if state["enabled"] != p.enabled:
            state.update(enabled=p.enabled, plan=None, generating=False,
                         history_version=session.get("history_version", 0))
        if agent is not None:
            agent._plan_mode = p.enabled
        return _ok(rid, plan_snapshot(session))
    return _plan_request(rid, params, PlanModeParams, apply)


def _plan_mutate(rid, params, model, mutate):
    from .plan_review import plan_snapshot

    def apply(p, session, state):
        if error := _plan_target(rid, p, session, state):
            return error
        if error := mutate(p, state["plan"]):
            return error
        state["plan"]["revision"] += 1
        return _ok(rid, plan_snapshot(session))
    return _plan_request(rid, params, model, apply)


@method("plan.edit")
@_registry.profile_scoped
def _plan_edit(rid, params):
    from .contracts.plans import PlanEditParams

    def edit(p, plan):
        if not p.text.strip():
            return _err(rid, 4000, "Plan must not be blank")
        plan.update(text=p.text, annotations=[])
    return _plan_mutate(rid, params, PlanEditParams, edit)


@method("plan.annotate")
@_registry.profile_scoped
def _plan_annotate(rid, params):
    from .contracts.plans import PlanAnnotateParams
    from .plan_review import plan_section_count

    def annotate(p, plan):
        if p.section >= plan_section_count(plan["text"]):
            return _err(rid, 4000, "Unknown plan section")
        notes = [note for note in plan["annotations"] if note["section"] != p.section]
        if p.text.strip():
            notes.append({"section": p.section, "text": p.text.strip()})
        plan["annotations"] = notes
    return _plan_mutate(rid, params, PlanAnnotateParams, annotate)


@method("plan.decide")
@_registry.profile_scoped
def _plan_decide(rid, params):
    from .contracts.plans import PlanDecideParams
    from .plan_review import plan_snapshot

    def decide(p, session, state):
        if error := _plan_target(rid, p, session, state):
            return error
        plan = state["plan"]
        if p.intent == "approve":
            # Approval records exact reviewed bytes; it never fabricates a user prompt
            # or starts execution. The next explicit user turn may execute.
            plan["decision"] = "approved"
            state["enabled"] = False
            if session.get("agent") is not None:
                session["agent"]._plan_mode = False
        else:
            if not p.feedback.strip() and not plan["annotations"]:
                return _err(rid, 4000, "Refinement needs feedback or section annotations")
            notes = "\n".join(f"Section {n['section'] + 1}: {n['text']}" for n in plan["annotations"])
            text = (f"Refine plan {plan['id']} revision {plan['revision']}. Remain in plan mode; do not execute.\n\n"
                    f"{plan['text']}\n\nFeedback:\n{p.feedback.strip()}\n{notes}")
            plan["decision"] = "refined"
            result = _methods["prompt.submit"](rid, {"session_id": p.session_id, "text": text, "image_paths": []})
            if "error" in result:
                plan["decision"] = "pending"
                return result
        return _ok(rid, plan_snapshot(session))
    return _plan_request(rid, params, PlanDecideParams, decide)


def register(server):
    bind_module(globals(), server)
