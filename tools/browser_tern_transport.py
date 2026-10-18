"""Window-pinned CLI requests with demand-driven late-open reconciliation.

Keep an abandoned open's client alive long enough to receive its exact block id.
Never identify it by comparing discovery lists: another user can open a page too.
No worker threads, idle timers, or daemon/socket discovery are needed.
"""
from __future__ import annotations

import json
import subprocess


class TernBrowserCLI:
    def __init__(self, executable, env, window, timeout: float = 35):
        self.executable = executable
        self.env = env
        self.window = window
        self.timeout = timeout
        self.pending = None
        self.unknown = False

    def _answer(self, result, stdout, unwrap=True):
        from tools.browser_tern import TernBrowserError

        if result == 124:
            raise TernBrowserError("Tern request timed out without a definitive answer", "timeout")
        try:
            answer = json.loads(stdout)
        except (ValueError, TypeError) as error:
            raise TernBrowserError("Tern returned no valid JSON answer", "protocol") from error
        if not isinstance(answer, dict):
            raise TernBrowserError("Tern returned a non-object answer", "protocol")
        if result or "error" in answer:
            detail = answer.get("error")
            detail = detail if isinstance(detail, dict) else {}
            raise TernBrowserError(str(detail.get("message", "Tern browser failed")), detail.get("kind", "failed"))
        if not unwrap:
            return answer.get("ok", answer)
        if not isinstance(answer.get("ok"), dict):
            raise TernBrowserError("Tern answered without an object result", "protocol")
        return answer["ok"]

    def invoke(self, argv):
        result = subprocess.run([self.executable, *argv, "--window", self.window], env=self.env,
                                capture_output=True, text=True, timeout=self.timeout)
        return self._answer(result.returncode, result.stdout, unwrap=argv[0] == "browser")

    def __call__(self, op):
        from tools.browser_tern import TernBrowserError

        if op["op"] != "open":
            return self.invoke(["browser", json.dumps(op), "--timeout", "30"])
        if self.pending is not None or self.unknown:
            raise TernBrowserError("An earlier Tern open is still indeterminate", "open_pending")
        # The outer wait is shorter than the CLI wait. communicate(timeout=...) does
        # not kill Popen, so a later explicit command/cleanup can read the exact id.
        process = subprocess.Popen(
            [self.executable, "browser", json.dumps(op), "--timeout", "300", "--window", self.window],
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.pending = process
        try:
            stdout, _ = process.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired as error:
            raise TernBrowserError("Tern open timed out; its exact answer is pending reconciliation", "open_pending") from error
        return self._finish_open(stdout)

    def _finish_open(self, stdout):
        from tools.browser_tern import TernBrowserError

        process = self.pending
        assert process is not None
        self.pending = None
        try:
            return self._answer(process.returncode, stdout)
        except TernBrowserError as error:
            # A timeout, broken pipe or malformed reply cannot prove that no page
            # was created. Keep the quarantine even after the client has exited.
            self.unknown = error.kind not in {"unsupported", "invalid", "no_window"}
            raise

    def reconcile_open(self):
        from tools.browser_tern import TernBrowserError

        if self.unknown:
            raise TernBrowserError("Tern open has no definitive block id; inspect the isolated window before recovery", "open_unknown")
        if self.pending is None:
            raise TernBrowserError("Tern open has no exact answer available for reconciliation", "open_unknown")
        if self.pending.poll() is None:
            raise TernBrowserError("Tern open answer is still pending; retry reconciliation later", "open_pending")
        stdout, _ = self.pending.communicate(timeout=self.timeout)
        return self._finish_open(stdout)
