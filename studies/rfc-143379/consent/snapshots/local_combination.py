"""Hypothetical local composition of PR 116834's target gate and PR 116846's
self-report detector. This module is NOT a published upstream PR/branch.
"""
import json
from .pr_116834 import _background_op_needs_staging
from .pr_116846 import _consent_sensitive_add


def _background_delete_gate(store, action, operations, target='memory', content=None,old_text=None):
    from tools.skill_provenance import is_unattended_review
    if not is_unattended_review():
        return None
    payload = ({'action':'batch','target':target,'operations':operations} if operations is not None
               else {'action':action,'target':target,'content':content,'old_text':old_text})
    consent_hit = _consent_sensitive_add(action,content) or any(
        isinstance(op,dict) and _consent_sensitive_add(op.get('action'),op.get('content'))
        for op in (operations or []))
    if not (_background_op_needs_staging(payload) or consent_hit):
        return None
    detail = ('; '.join(_batch_op_line(op) for op in operations) if operations is not None
              else _batch_op_line({'action':action,'content':content,'old_text':old_text}))
    from tools import write_approval as wa
    record = wa.stage_write(
        wa.MEMORY,payload,
        summary=(f"background review consolidation ({'batch' if operations is not None else action} "
                 f"on {target}): {detail}")[:200],origin=wa.current_origin())
    return json.dumps({'success':True,'staged':True,'proposal_staged':True,'pending_id':record['id']})
