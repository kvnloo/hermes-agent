#!/usr/bin/env python3
"""Offline hook smoke, not a Hermes CLI or provider-turn substitute."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins'))
plugin = importlib.import_module('intake_ledger_match')

with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    ledger = home / 'ledger.json'
    ledger.write_text('[{"id":"A17b","ask":"Build intake ledger matching hook"}]')
    callbacks = {}
    class Context:
        def get_config(self, key, default=None):
            return str(ledger) if key == 'ledger_path' else default
        def register_hook(self, name, callback):
            callbacks[name] = callback
        def on_unload(self, callback):
            self.unload = callback
    # This is intentionally a host stand-in: no Hermes bootstrap, vault or provider is called.
    sys.modules['hermes_constants'] = SimpleNamespace(get_hermes_home=lambda: home)
    context = Context()
    plugin.register(context)
    assert callbacks['pre_llm_call'](user_message='A17b', turn_id='offline-smoke-turn') is None
    callbacks['on_session_end']()
    context.unload()
    assert json.loads(ledger.read_text())[0]['mentions'] == ['offline-smoke-turn']
    print('OFFLINE_ONLY=1 CLI_ONESHOT_RUN=0')
    print((home / 'logs' / 'ledger-match.log').read_text(), end='')
