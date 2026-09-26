"""Security checks for user-configured MCP server entries.

Blocks three narrow shapes (see ``validate_mcp_server_entry``), including a hardcoded IOC blocklist
for the June 2026 hermes-0day campaign. Runs BOTH at save time (``_save_mcp_server`` — dashboard API +
CLI) and at spawn time (``tools.mcp_tool._filter_suspicious_mcp_servers``), so a hand-edited or
pre-planted ``config.yaml`` entry is caught before it can execute.
"""
from __future__ import annotations

import os
import re
import shlex
from typing import Any

_SHELL_INTERPRETERS = frozenset({
    "bash", "sh", "zsh", "dash", "fish", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe",
})

_EGRESS_PATTERN = re.compile(
    r"(?<![\w.-])(?:curl|wget|nc|ncat|socat)(?![\w.-])"
    r"|/dev/tcp/"
    r"|\bInvoke-WebRequest\b"
    r"|\bInvoke-RestMethod\b"
    r"|\bSystem\.Net\.WebClient\b",
    re.IGNORECASE,
)

_EXFIL_HINT_PATTERN = re.compile(
    r"\.env\b|--data-binary|--data-raw|\b-X\s+POST\b|\bPOST\b|<\s*[^\s]+",
    re.IGNORECASE,
)

# OS persistence surfaces an MCP server has no legitimate reason to write to (the hermes-0day
# SSH-key/PAM/sudoers/cron shape). Matched anywhere in the inline script.
_PERSISTENCE_PATTERN = re.compile(
    r"authorized_keys"               # SSH key persistence (the campaign's payload)
    r"|\.ssh/"                       # any write under ~/.ssh
    r"|/etc/ssh\b"                   # sshd_config / AuthorizedKeysCommand backdoor
    r"|/etc/pam\.d\b|pam_[\w-]+\.so" # PAM credential logger
    r"|/etc/sudoers"                 # sudoers escalation
    r"|/etc/cron|crontab\b"          # cron persistence
    r"|/etc/rc\.local|/etc/systemd"  # init / unit persistence
    r"|\.bashrc\b|\.bash_profile\b|\.profile\b|\.zshrc\b",  # shell rc backdoor
    re.IGNORECASE,
)

# Indicators of compromise, June 2026 hermes-0day campaign: exact attacker artifacts observed on
# multiple compromised public instances. Hardcoded so a pre-planted config.yaml is refused.
_IOC_SUBSTRINGS = (
    "AAAAC3NzaC1lZDI1NTE5AAAAICBoh1oDC4DnsO1m5mJ4yfEKrQebaFh",  # attacker SSH public key
    "hermes-0day",
    # Attacker source IPs seen authenticating with the key.
    "60.165.167.",
    "118.182.244.156",
    "61.178.123.196",
)


def _command_basename(command: Any) -> str:
    text = str(command or "").strip()
    if not text:
        return ""
    try:
        parts = shlex.split(text, posix=(os.name != "nt"))
    except ValueError:
        parts = text.split()
    first = parts[0] if parts else text
    return os.path.basename(first).lower()


# Exec-transparent wrappers: they exec(3) straight into the effective command, so keying the
# shell-interpreter check on the COMMAND basename lets `command: env, args: [bash, -c, …]` sail
# through. The validator judges the peeled effective command by the same rules.
_TRANSPARENT_WRAPPERS = frozenset({
    "env", "nice", "nohup", "setsid", "stdbuf", "flock", "timeout",
    "sudo", "su", "runuser", "chroot", "unshare",
})

# Short flags that consume the next token (or an attached value: -n5) per wrapper.
_VALUE_FLAG_CHARS = {
    "env": "u",          # -u VAR
    "nice": "n",         # -n 5 / -5
    "timeout": "sk",     # -s SIG / -k 30s
    "sudo": "ug",        # -u user / -g group
    "su": "c",           # -c script (runs via sh — handled specially)
    "runuser": "ug",
}

_LONG_VALUE_FLAGS = {
    "env": {"unset"},
    "nice": {"adjustment"},
    "timeout": {"signal", "kill-after"},
    "sudo": {"user", "group"},
    "su": {"command"},
    "runuser": {"user", "group"},
}

_DURATION_RE = re.compile(r"^\d+(\.\d+)?[smhdw]?$")


def _peel_one_wrapper(base: str, tokens: list[str]) -> list[str] | None:
    """Return the argv after one wrapper's own options, or None if it cannot be peeled."""
    i, n = 0, len(tokens)
    value_chars = _VALUE_FLAG_CHARS.get(base, "")
    while i < n:
        tok = tokens[i]
        if tok == "--":
            return tokens[i + 1:]
        if tok == "-":
            i += 1  # su login dash; never a real command
            continue
        if tok.startswith("--"):
            name = tok[2:]
            i += 1
            if "=" not in name and name in _LONG_VALUE_FLAGS.get(base, ()):
                i += 1
            if base == "su" and name.split("=")[0] == "command":
                script = name.split("=", 1)[1] if "=" in name else (tokens[i] if i < n else "")
                return ["sh", "-c", script]
            continue
        if tok.startswith("-") and len(tok) > 1:
            if base == "nice" and re.fullmatch(r"-\d+", tok):
                i += 1  # nice -5 == nice -n 5
                continue
            j, ate_value = 1, False
            while j < len(tok):
                if tok[j] in value_chars:
                    if base == "su":
                        # su -c 'script' runs the script via the shell.
                        script = tok[j + 1:] or (tokens[i + 1] if i + 1 < n else "")
                        return ["sh", "-c", script]
                    i += 1 if j + 1 < len(tok) else 2  # attached value vs next token
                    ate_value = True
                    break
                j += 1
            if not ate_value:
                i += 1
            continue
        if base in ("env", "sudo") and "=" in tok:
            i += 1  # VAR=value assignment
            continue
        break
    argv = tokens[i:]
    if base == "timeout" and argv and _DURATION_RE.match(argv[0]):
        argv = argv[1:]  # first positional is the duration, not the command
    if base == "chroot" and argv:
        argv = argv[1:]  # first positional is the new root dir
    return argv or None


def _peel_wrappers(command: Any, args: Any) -> tuple[Any, Any]:
    """Resolve exec-transparent wrappers to the effective (command, args) pair."""
    if isinstance(args, (list, tuple)):
        argv: list[Any] = [command] + [str(a) for a in args]
    else:
        try:
            argv = [command] + shlex.split(str(args or ""), posix=(os.name != "nt"))
        except ValueError:
            return command, args
    peels = 0
    while peels < 8 and _command_basename(argv[0]) in _TRANSPARENT_WRAPPERS:
        peels += 1
        peeled = _peel_one_wrapper(_command_basename(argv[0]), [str(t) for t in argv[1:]])
        if not peeled:
            break
        argv = peeled
    return argv[0], argv[1:]


def _inline_script(args: Any) -> str:
    if args is None:
        return ""
    if isinstance(args, (list, tuple)):
        return " ".join(str(item) for item in args)
    return str(args)


def _entry_text(entry: dict[str, Any]) -> str:
    """Flatten command + args + env values into one string for IOC scanning."""
    parts: list[str] = [str(entry.get("command") or "")]
    parts.append(_inline_script(entry.get("args")))
    env = entry.get("env")
    if isinstance(env, dict):
        parts.extend(str(v) for v in env.values())
    return " ".join(parts)


def validate_mcp_server_entry(name: str, entry: dict[str, Any]) -> list[str]:
    """Return security warnings for an MCP server entry (empty = not suspicious).

    Intentionally not a whitelist — custom commands, Python scripts, npx, uvx stay legal. Only three
    narrow shapes are blocked: (1) a known IOC anywhere in command/args/env, (2) a shell interpreter
    with network egress in its inline script, (3) a shell interpreter writing an OS persistence surface.

    * a shell interpreter whose inline script writes to an OS persistence surface (June 2026 hermes-0day
    SSH/PAM/sudoers/cron shape). See #45620.
    """
    if not isinstance(entry, dict):
        return []

    issues: list[str] = []
    flat = _entry_text(entry)
    for ioc in _IOC_SUBSTRINGS:
        if ioc in flat:
            # One IOC is enough to refuse; don't leak the full match list.
            issues.append(
                f"MCP server '{name}' contains a known hermes-0day "
                f"indicator-of-compromise ('{ioc}')"
            )
            return issues

    command = entry.get("command")
    eff_command, eff_args = _peel_wrappers(command, entry.get("args"))
    via = f" (via wrapper '{command}')" if str(eff_command) != str(command) else ""
    if _command_basename(eff_command) not in _SHELL_INTERPRETERS:
        return issues
    script = _inline_script(eff_args)
    if not script:
        return issues

    if _EGRESS_PATTERN.search(script):
        issue = (
            f"MCP server '{name}' uses shell interpreter '{eff_command}'{via} with "
            f"network egress in args"
        )
        if _EXFIL_HINT_PATTERN.search(script):
            issue += " and exfiltration-shaped arguments"
        issues.append(issue)
    if _PERSISTENCE_PATTERN.search(script):
        issues.append(
            f"MCP server '{name}' uses shell interpreter '{eff_command}'{via} to write "
            f"to an OS persistence surface (SSH keys / PAM / sudoers / cron / "
            f"shell rc) — this is the hermes-0day backdoor shape, not a real "
            f"MCP server"
        )
    return issues


# ---- BEGIN PLUGIN-COMPAT (revert-scheduled; see COMPAT_MANIFEST.md) ----
# Names external plugins imported from this module before the Sep 2026 decomposition.
# Internal code MUST NOT use these (scripts/check_compat_pointers.py fails CI if it does).
# The whole block is removed by reverting the commit that added it.

def is_mcp_server_entry_suspicious(name: str, entry: dict[str, Any]) -> bool:
    return bool(validate_mcp_server_entry(name, entry))
# ---- END PLUGIN-COMPAT ----
