"""Observe intake user turns without changing or waiting on the LLM call."""
from __future__ import annotations

import contextvars
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time

from .matcher import update_ledger

DEFAULT_LEDGER = '/mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-ledger.json'


def message_text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return '\n'.join(part['text'] for part in value
                         if isinstance(part, dict) and part.get('type') in {'text', 'input_text'}
                         and isinstance(part.get('text'), str)).strip()
    return ''


class Observer:
    def __init__(self, ledger: Path, log: Path, owner_id: str):
        self.ledger = ledger
        self.log = log
        self.owner_id = owner_id
        self.workers: set[threading.Thread] = set()
        self.guard = threading.Lock()

    def record(self, event: str, **fields) -> None:
        try:
            self.log.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps({'time': datetime.now(timezone.utc).isoformat(), 'event': event, **fields})
            with self.log.open('a', encoding='utf-8') as out:
                out.write(line + '\n')
        except Exception:
            # Logging failures must never escape into the agent or its shutdown path.
            return

    def process(self, message_id: str, text: str) -> None:
        try:
            self.record('pre_llm_call', message_id=message_id)
            result = update_ledger(self.ledger, message_id, text)
            self.record('ledger_updated', **result)
        except Exception as exc:
            self.record('error', message_id=message_id, error_type=type(exc).__name__)
        finally:
            with self.guard:
                self.workers.discard(threading.current_thread())

    def pre_llm_call(self, user_message='', session_id='', turn_id='', message_id='',
                     source_msg_id='', parent_session_id='', sender_id='', platform='',
                     role='user', **kwargs) -> None:
        try:
            if role != 'user' or parent_session_id:
                return None
            if platform not in {'', 'cli', 'tui', 'acp'} and str(sender_id) != self.owner_id:
                return None
            text = message_text(user_message)
            if not text:
                return None
            native_id = source_msg_id or message_id
            stable_id = str(native_id or turn_id)
            # Missing identity is rejected by the worker, with no disk I/O on this path.
            # Preserve supplied IDs verbatim. Today's core supplies only a unique turn_id.
            worker = threading.Thread(target=contextvars.copy_context().run,
                                      args=(self.process, stable_id, text),
                                      name='intake-ledger-match', daemon=True)
            with self.guard:
                self.workers.add(worker)
            try:
                worker.start()
            except Exception:
                with self.guard:
                    self.workers.discard(worker)
                raise
        except Exception as exc:
            self.record('error', error_type=type(exc).__name__)
        return None

    def drain(self, **kwargs) -> None:
        """Only at session end, never on the LLM path; cap shutdown waiting."""
        deadline = time.monotonic() + 6.0
        with self.guard:
            workers = list(self.workers)
        for worker in workers:
            worker.join(max(0, deadline - time.monotonic()))


def register(ctx) -> None:
    from hermes_constants import get_hermes_home

    home = get_hermes_home()
    observer = Observer(Path(ctx.get_config('ledger_path', DEFAULT_LEDGER)),
                        home / 'logs' / 'ledger-match.log',
                        str(ctx.get_config('owner_id', '1083429746')))
    ctx.register_hook('pre_llm_call', observer.pre_llm_call)
    ctx.register_hook('on_session_end', observer.drain)
    ctx.on_unload(observer.drain)
    observer.record('loaded', plugin='intake_ledger_match', ledger=str(observer.ledger))
