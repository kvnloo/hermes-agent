"""Frozen async legacy plugin used by the behavior compatibility suite.

Keep ``_on_session_start`` in its old, narrow ``async def`` form: it predates additive
hook payload fields and does not accept ``**kwargs``. ``_observe`` is the control.
"""

received_sessions = []


async def _on_session_start(*, session_id):
    received_sessions.append(session_id)
    return {"async_legacy_session_id": session_id}


def _observe(**kwargs):
    return {"observed_fields": sorted(kwargs)}


def register(ctx):
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_start", _observe)
