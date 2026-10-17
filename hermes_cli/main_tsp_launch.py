"""Opt-in native composer seam; the existing Ink client remains the runtime adapter."""

import subprocess

NO_TSP_EXIT = 75


def tern_activation_wanted(enabled: bool, env: dict) -> bool:
    """Detection is not consent. TERN_TSP is the SDK's existing per-launch override.

    Multiplexers always block APC probing, including a forced probe over SSH.
    """
    flag = (env.get("TERN_TSP") or "").strip().lower()
    if flag in {"0", "false", "no", "off"} or any(env.get(k) for k in ("TMUX", "STY", "ZELLIJ")):
        return False
    return flag in {"1", "true", "yes", "on"} or (enabled is True and env.get("TERM_PROGRAM") == "tern")


def tern_frontend_wanted(env: dict) -> bool:
    if tern_activation_wanted(False, env):
        return True
    try:
        from hermes_cli.config import load_config
        display = load_config().get("display", {})
        enabled = isinstance(display, dict) and display.get("tern") is True
    except Exception:
        enabled = False
    return tern_activation_wanted(enabled, env)


def run_tui_frontend(argv: list[str], cwd, env: dict, *, probe: bool) -> int:
    """Only a pre-runtime no-handshake exit retries Ink; errors are never masked."""
    if probe:
        code = subprocess.call([*argv, "--tern-composer"], cwd=str(cwd), env=env)
        if code != NO_TSP_EXIT:
            return code
    return subprocess.call(argv, cwd=str(cwd), env=env)
