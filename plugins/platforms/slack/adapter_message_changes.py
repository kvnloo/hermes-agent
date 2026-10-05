"""Normalize genuine Slack edits without replaying metadata-only updates."""

from collections.abc import Collection


def normalize_changed_message(event: dict, processed_message_ts: Collection[str]) -> dict | None:
    """Turn a ``message_changed`` envelope into a plain message event.
    None if malformed, a Slack-side metadata update, or the original was already routed to the
    agent. The edit's own ts rides along as ``_slack_changed_event_ts`` for dedup."""
    updated_message = event.get("message")
    if not isinstance(updated_message, dict):
        return None
    original_message_ts = str(updated_message.get("ts") or "")
    if original_message_ts and original_message_ts in processed_message_ts:
        return None
    edited = updated_message.get("edited")
    if not (isinstance(edited, dict) and edited.get("ts")):
        # Slack also fires ``message_changed`` without ``edited`` for its own metadata updates
        # (a thread root's reply_count/latest_reply, link unfurls): never the user speaking.
        # The in-memory ts map is empty after a gateway restart, so it cannot be the only
        # guard stopping a metadata update from re-routing the root as a new turn (#131688).
        return None
    edited_ts = str(edited.get("ts") or "")
    outer_event_ts = str(event.get("ts") or "")
    changed_event_ts = (
        str(event.get("event_ts") or edited_ts or "")
        or (outer_event_ts if outer_event_ts != original_message_ts else "")
        or (f"{original_message_ts}:changed" if original_message_ts else ""))
    normalized_event = dict(updated_message)
    for key in ("channel", "channel_type", "team", "team_id"):
        if not normalized_event.get(key) and event.get(key):
            normalized_event[key] = event.get(key)
    if changed_event_ts:
        normalized_event["_slack_changed_event_ts"] = changed_event_ts
    return normalized_event
