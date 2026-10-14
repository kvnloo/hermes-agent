"""Evidence-run guard: DNS and socket connections are never part of this probe."""

import sys

_attempts = []


def _audit(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}:
        _attempts.append(event)
        raise RuntimeError("Offline evidence guard blocked network activity")


sys.addaudithook(_audit)


def pytest_sessionfinish(session, exitstatus):
    if _attempts:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_line(f"Offline evidence guard: {len(_attempts)} network attempts")
