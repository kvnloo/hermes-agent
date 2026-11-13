---
name: cross-profile-peek
description: Use when reading another bot's chat. Run hermes-peek.
---
# Cross-profile peek

Owner rule (2026-11-05): bots may read each other's conversations when needed. Check another profile before asking Kevin to repeat himself, and before assuming an ask was never made.

- `hermes-peek` lists profiles and their last activity.
- `hermes-peek <profile>` shows Kevin's last 20 messages there, with relays, handoffs and notifications filtered out.
- `hermes-peek <profile> --all -n 40` includes assistant replies.
- `hermes-peek <profile> -q <text>` runs a full-text search; `--since 3h` limits the time range.

Rules:
- Read-only (sqlite `mode=ro`). Never write to another profile's state.db.
- Long messages are truncated to `--width` (default 600). Raise it to read a full ask.
- An ask found in another profile goes into the ayo ledger (`intent-analyzer-20261104/render_ledger.py`) only if that profile isn't already handling it; check its later replies first.
- session_search / chat_history_lookup only cover your own profile. Use hermes-peek or `ctx` for everything else.
