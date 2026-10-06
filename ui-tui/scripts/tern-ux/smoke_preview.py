"""Real Node process in a PTY, with a fake Tern protocol peer; not a GUI test."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import termios
import time

TUI = Path(__file__).resolve().parents[2]
KINDS = ['agent', 'card', 'code', 'col', 'diff', 'editor', 'md', 'overlay', 'row', 'text']
SURFACE = 'hermes:ux:preview'


def smoke(columns: int, rows: int, supported: bool = True) -> dict:
    master, slave = os.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, columns, 0, 0))
    original = termios.tcgetattr(slave)
    env = {k: v for k, v in os.environ.items() if k not in ('TMUX', 'STY', 'ZELLIJ')}
    env['TERM'] = 'xterm-256color'
    child = subprocess.Popen(
        ['node', '--import', 'tsx', 'scripts/tern-ux/preview.ts'], cwd=TUI, env=env,
        stdin=slave, stdout=slave, stderr=slave, close_fds=True,
    )
    buffer = b''
    opened = closed = frames = barriers = 0

    def reply(verb: str, payload: dict) -> None:
        os.write(master, b'\x1b_tsp;' + verb.encode() + b';' + json.dumps(payload).encode() + b'\x1b\\')

    def message(payload: bytes) -> None:
        nonlocal opened, closed, frames
        assert payload.startswith(b'tsp;'), payload[:100]
        verb, body = payload[4:].split(b';', 1)
        value = json.loads(body)
        if verb == b'q':
            assert value['app'] == 'hermes-ux-fixture' and value['features'] == []
            if supported:
                reply('r', {'r': 'hello', 'v': 1, 'term': 'tern', 'kinds': KINDS,
                            'features': ['dock'], 'credits': 1, 'apc': 65536, 'cols': columns})
        elif verb == b'o':
            opened += 1
            assert value['id'] == SURFACE and value['mode'] == 'inline'
        elif verb == b'f':
            frames += 1
            assert value['sf'] == SURFACE and value['s'] == frames
            assert not closed
            reply('e', {'ev': 'ack', 'sf': SURFACE, 's': frames})
            os.write(master, b'n' if frames < 14 else b'q')
        elif verb == b'x':
            closed += 1
            assert value == {'id': SURFACE, 'keep': False}

    try:
        deadline = time.monotonic() + 30
        while child.poll() is None and time.monotonic() < deadline:
            if not select.select([master], [], [], 0.1)[0]:
                continue
            buffer += os.read(master, 65536)
            while buffer:
                if buffer.startswith(b'\x1b_'):
                    end = buffer.find(b'\x1b\\', 2)
                    if end < 0:
                        break
                    message(buffer[2:end])
                    buffer = buffer[end + 2:]
                elif buffer.startswith(b'\x1b[c'):
                    barriers += 1
                    if closed:
                        # Delayed terminal events after x must be consumed before cooked input returns.
                        reply('e', {'ev': 'ack', 'sf': SURFACE, 's': frames})
                    os.write(master, b'\x1b[?1;2c')
                    buffer = buffer[3:]
                elif buffer.startswith(b'\x1b') and len(buffer) < 3:
                    break
                else:
                    buffer = buffer[1:]
        assert child.wait(timeout=2) == (0 if supported else 1), 'unexpected preview exit'
        assert (opened, closed, frames) == ((1, 1, 14) if supported else (0, 0, 0))
        assert barriers == 2, 'probe and post-close barriers must both complete'
        restored = termios.tcgetattr(slave)
        for flag in (termios.ECHO, termios.ICANON):
            assert restored[3] & flag == original[3] & flag, 'TTY mode was not restored'
        return {'columns': columns, 'rows': rows, 'supported': supported,
                'opens': opened, 'closes': closed, 'frames': frames, 'tty_restored': True}
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        os.close(master)
        os.close(slave)


if __name__ == '__main__':
    results = [smoke(c, r) for c, r in [(80, 28), (120, 36), (180, 44)]]
    results.append(smoke(80, 28, supported=False))
    print(json.dumps({'test': 'fake-Tern PTY, not native visual verification', 'results': results}, indent=2))
