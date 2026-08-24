"""Direct-argv, bounded privileged process execution."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from typing import Optional


class Executor:
    """Execute a catalog-resolved plan without a shell or caller state."""

    def __init__(self, timeout: int = 30, max_output: int = 64 * 1024):
        self._timeout = timeout
        self._max_output = max_output

    def execute_plan(self, plan: dict, timeout: Optional[int] = None) -> dict:
        argv = plan["argv"]
        if not isinstance(argv, list) or not argv or not all(isinstance(value, str) for value in argv):
            raise ValueError("plan argv must be a non-empty string list")
        if not os.path.isabs(argv[0]):
            raise ValueError("plan executable must be absolute")
        actual_timeout = min(timeout or int(plan.get("timeout_seconds", self._timeout)), self._timeout)
        started_wall = time.time()
        started = time.monotonic()
        proc = subprocess.Popen(
            argv,
            cwd=plan.get("cwd", "/"),
            env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": ""},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
        selector = selectors.DefaultSelector()
        assert proc.stdout is not None and proc.stderr is not None
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        output = {"stdout": bytearray(), "stderr": bytearray()}
        total = 0
        truncated = False
        timed_out = False
        try:
            while selector.get_map():
                remaining = actual_timeout - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    self._kill_group(proc)
                    break
                events = selector.select(min(remaining, 0.1))
                if not events and proc.poll() is not None:
                    events = [(key, None) for key in list(selector.get_map().values())]
                for key, _ in events:
                    chunk = os.read(key.fd, min(4096, self._max_output - total + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    room = self._max_output - total
                    output[key.data].extend(chunk[:room])
                    total += min(len(chunk), room)
                    if len(chunk) > room or total >= self._max_output:
                        truncated = True
                        self._kill_group(proc)
                        selector.close()
                        break
            proc.wait(timeout=2)
        finally:
            selector.close()
            if proc.poll() is None:
                self._kill_group(proc)
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "stdout": output["stdout"].decode("utf-8", errors="replace"),
            "stderr": output["stderr"].decode("utf-8", errors="replace"),
            "exit_code": proc.returncode if proc.returncode is not None else -1,
            "executed_at": started_wall,
            "duration_ms": duration_ms,
            "truncated": truncated,
            "timed_out": timed_out,
        }

    @staticmethod
    def _kill_group(proc: subprocess.Popen) -> None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass

    def execute(self, *args, **kwargs):
        raise TypeError("arbitrary command execution was removed; use execute_plan")
