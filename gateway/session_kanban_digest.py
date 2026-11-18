"""Trusted Kanban wake batching and execution-time, read-only card snapshots.

Never infer a board/task from rendered prose. Old admissions without structured
references retain their text; new notices are re-read only after route authorization.
"""
import json
import sqlite3
from pathlib import Path

from hermes_state_runtime import RuntimeStoreError


def descriptor(payload):
    return payload.get('local_automation_v1') or payload.get('native_text_v1', {}).get('automation') or {}


from hermes_state_runtime import is_kanban_input as is_kanban


def notice_metadata(metadata):
    if 'kanban_notices' not in metadata:
        return {}
    notices = metadata['kanban_notices']
    keys = {'db', 'board', 'task_id', 'platform', 'chat_id', 'thread_id'}
    allowed = keys | {'measured_at'}  # Old persisted notices have only the six original keys.
    if (not isinstance(notices, list) or not notices or any(
            not isinstance(n, dict) or not keys.issubset(n) or not set(n).issubset(allowed)
            or any(not isinstance(v, str) for v in n.values())
            or not Path(n['db']).is_absolute() for n in notices)):
        raise RuntimeStoreError('invalid_params')
    return {'kanban_notices': [dict(n) for n in notices]}


def fold_event(authority, sid, event, identity):
    from hermes_state_runtime import list_session_admissions
    category = event.metadata.get('notification_category', 'result')
    waiting = [r for r in list_session_admissions(authority.db, session_id=sid)
               if r['status'] == 'queued' and is_kanban(r)
               and r['principal_id'] == 'automation:' + event.metadata['gateway_session_key']
               and descriptor(r['payload']).get('notification_category', 'result') == category]
    if not waiting:
        return []
    identities = {identity}
    notices = list(event.metadata.get('kanban_notices', []))
    texts = []
    for row in waiting:
        old = descriptor(row['payload'])
        identities.update(old.get('identities') or [row['request_id']])
        notices.extend(old.get('kanban_notices', []))
        texts.append(row['payload']['text'])
    # Texts have no wrapping header: incremental folding remains linear.
    event.text = '\n\n'.join([*texts, event.text])
    event.metadata['automation_identities'] = sorted(identities)
    if notices:
        event.metadata['kanban_notices'] = list({(n['db'], n['task_id'], n['platform'], n['chat_id'], n['thread_id']): n
                                               for n in notices}.values())
    return [r['admission_id'] for r in waiting]


def retire_folded(ids, sid, retired):
    def guard(conn):
        for admission_id in ids:
            changed = conn.execute("UPDATE session_admissions SET status='terminal',outcome='cancelled' "
                                   "WHERE admission_id=? AND target_session_id=? AND status='queued'",
                                   (admission_id, sid)).rowcount
            if changed != 1:
                raise RuntimeStoreError('stale_generation')
        retired[:] = ids
    return guard


def refresh_text(desc, historical):
    notices = desc.get('kanban_notices')
    if not notices:
        return historical
    texts = []
    for n in notices:
        try:
            # Explicit URI mode=ro: missing DBs are NOT created; no migrations.
            with sqlite3.connect(Path(n['db']).as_uri() + '?mode=ro', uri=True, timeout=1) as conn:
                conn.row_factory = sqlite3.Row
                sub = conn.execute('SELECT 1 FROM kanban_notify_subs WHERE task_id=? AND platform=? '
                                   "AND chat_id=? AND COALESCE(thread_id,'')=?",
                                   (n['task_id'], n['platform'], n['chat_id'], n['thread_id'])).fetchone()
                if sub is None:
                    continue
                task = conn.execute('SELECT status,title,assignee FROM tasks WHERE id=?', (n['task_id'],)).fetchone()
                if task is None or task['status'] == 'archived':
                    continue
                measured = n.get('measured_at') or 'unknown (legacy wake)'
                texts.append(f"[kanban] {n['board']}/{n['task_id']} — Current status: {task['status']}\n"
                             f"Title: {task['title']}\nAssignee: {task['assignee'] or '(none)'}\n"
                             f"Event measured_at: {measured}\n"
                             'Historical events superseded by this execution-time snapshot.')
        except (OSError, sqlite3.Error, ValueError):
            texts.append('[kanban] Current state unavailable; historical notification withheld.')
    return '\n\n'.join(texts) or None
