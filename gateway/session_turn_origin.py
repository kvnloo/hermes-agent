"""Human-input classification from the executing admission, never the cached agent."""
from agent.turn_author import parse_turn_author
from gateway.session_operator import is_viewer_input


def human_authored_input(policy, row, source) -> bool:
    """Require an attended viewer submit or an ordinary non-bot native message.

    Attribution alone cannot grant owner pacing: synthetic events reuse human sources,
    and API author labels are client supplied.
    """
    from gateway.session_ingress import row_turn_author

    payload = row['payload']
    author = parse_turn_author(row_turn_author(policy, row))
    if (author and (author['is_bot'] or (author['id'] or '').startswith('bot:'))
            or payload.get('unattended') or payload.get('display_v1', {}).get('kind')):
        return False
    if policy is not None and (policy.source not in {'cli', 'tui', 'gui', 'acp'}
                               or policy.kanban_json is not None):
        return False
    native = payload.get('native_text_v1')
    if native is not None:
        sender = native.get('source') or {}
        return ('automation' not in native and not native['event'].get('inherit_channel_pin')
                and sender.get('is_bot') is False
                and sender.get('platform') not in {None, 'local', 'api_server', 'webhook', 'a2a'}
                and bool(sender.get('user_id') or sender.get('user_name')))
    return source is not None and source.is_bot is False and is_viewer_input(row)
