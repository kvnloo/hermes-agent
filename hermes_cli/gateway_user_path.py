"""Read the systemd user manager's PATH when generating a gateway user unit."""

import shlex
import subprocess
import sys


def manager_path() -> str:
    """Return inherited user-service PATH; omit it when the manager is unreachable."""
    if sys.platform != "linux":
        return ""
    # Late binding matches gateway's facade seams and its systemctl user-bus handling.
    from hermes_cli import gateway as gw

    if not gw._user_systemd_socket_ready():
        return ""
    try:
        result = gw._run_systemctl(
            ["show-environment"], capture_output=True, text=True, timeout=2,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    for line in result.stdout.splitlines():
        if not line.startswith("PATH="):
            continue
        # systemctl uses ANSI-C $'...' quoting for control bytes; never misparse it.
        if line.startswith("PATH=$'"):
            return ""
        try:
            assignment = shlex.split(line)
        except ValueError:
            return ""
        if len(assignment) == 1 and assignment[0].startswith("PATH="):
            return assignment[0][5:]
        return ""
    return ""
