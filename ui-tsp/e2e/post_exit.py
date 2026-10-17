#!/usr/bin/env python3
"""Audit late terminal replies after the frontend has closed its surface."""
import json
import os
from pathlib import Path
import select
import sys
import termios
import time
import tty

old = termios.tcgetattr(0)
received = bytearray()
try:
    tty.setraw(0)
    end = time.monotonic()+0.5
    while time.monotonic() < end:
        ready, _, _ = select.select([0], [], [], max(0, end-time.monotonic()))
        if ready:
            data = os.read(0, 65536)
            if not data:
                break
            received.extend(data)
finally:
    termios.tcsetattr(0, termios.TCSANOW, old)
Path(sys.argv[1]).write_text(json.dumps(dict(hex=received.hex(), duration_ms=500)))
raise SystemExit(bool(received))
