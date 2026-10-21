"""Classic /queue management over the gateway's actual accepted-prompt envelopes."""
from __future__ import annotations

from hermes_cli.cli_loops_mixin import _QUEUE_VERBS, _parse_queue_index


def _retire_row(server, session, envelope):
    staged = envelope.get('_submit_user_row')
    if not isinstance(staged, dict) or not isinstance(staged.get('_row_id'), int):
        return
    with server._session_db(session) as db:
        if db is None:
            raise RuntimeError('Queue history store unavailable; queue unchanged.')
        key = server._submit_row_owner_key(staged, session)
        row = db.resolve_active_row_id(key, staged['_row_id'])
        if row is not None:
            db.deactivate_message(key, row)


def execute_queue(rid, session, arg):
    from . import server

    if session is None:
        return server._err(rid, 4001, 'no active session')
    payload = (arg or '').strip()
    verb, _, rest = payload.partition(' ')
    verb, rest = verb.lower(), rest.strip()
    if verb == 'add':
        return (server._ok(rid, {'type': 'send', 'message': rest}) if rest
                else server._ok(rid, {'type': 'exec', 'output': 'Usage: /queue add <prompt>'}))
    handler, takes_index = _QUEUE_VERBS.get(verb, (None, False))
    management = not payload or handler is not None and (
        rest.split(None, 1)[0].isdigit() if takes_index and rest else not rest)
    if not management:
        return server._ok(rid, {'type': 'send', 'message': payload})
    with session['history_lock']:
        head = session.get('queued_prompt')
        entries = ([head] if head else []) + list(session.get('queued_prompts') or [])
        if not payload or handler == '_queue_list':
            output = ('Queued prompts:\n' + '\n'.join(f"  {i}. {item.get('text', '')}" for i, item in enumerate(entries, 1))
                      if entries else 'No queued prompts.')
        elif handler == '_queue_clear':
            for item in entries:
                _retire_row(server, session, item)
            server._ac_set_queue(session, [])
            output = f'Cleared {len(entries)} queued prompts.'
        else:
            output = _mutate_queue(server, session, entries, handler, rest)
    return server._ok(rid, {'type': 'exec', 'output': output})


def _mutate_queue(server, session, entries, handler, rest):
    bits = rest.split(None, 1)
    index = _parse_queue_index(bits[0]) if bits else None
    if index is None or not 1 <= index <= len(entries):
        return 'Queue item not found. Use /queue list, edit N <prompt>, rm N, move A B, or clear.'
    if handler == '_queue_remove':
        if len(bits) != 1:
            return 'Usage: /queue rm N'
        _retire_row(server, session, entries[index - 1])
        entries.pop(index - 1)
    elif handler == '_queue_edit':
        if len(bits) != 2 or not bits[1].strip():
            return 'Usage: /queue edit N <prompt>'
        envelope = entries[index - 1]
        previous = envelope['text']
        envelope['text'] = bits[1].strip()
        try:
            server._persist_queued_user_row(session, envelope, envelope.get('_queued_display_kind'))
        except Exception:
            envelope['text'] = previous
            raise
    elif handler == '_queue_move':
        destination = _parse_queue_index(bits[1]) if len(bits) == 2 else None
        if destination is None or not 1 <= destination <= len(entries):
            return 'Usage: /queue move A B (both indices must exist)'
        entries.insert(destination - 1, entries.pop(index - 1))
    server._ac_set_queue(session, entries)
    return 'Queue updated. Use /queue list to inspect it.'
