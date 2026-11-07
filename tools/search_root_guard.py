"""Refuse search_files roots whose recursive walk would read a whole disk.

A root is refused when it IS, or CONTAINS, a broad root: the filesystem root,
the user's home, or an operator-listed root (``HERMES_SEARCH_BROAD_ROOTS``,
``os.pathsep``-separated, plus ``file_search.broad_roots`` in config.yaml).
Pure path arithmetic: the check itself never touches the disk.
"""

import os
from typing import Optional

ENV_VAR = "HERMES_SEARCH_BROAD_ROOTS"


def _config_roots() -> list[str]:
    try:
        from hermes_cli.config import load_config_readonly
        roots = (load_config_readonly().get("file_search") or {}).get("broad_roots") or []
    except Exception:
        return []
    return [str(r) for r in roots] if isinstance(roots, list) else []


def _broad_roots() -> list[str]:
    listed = [r for r in os.environ.get(ENV_VAR, "").split(os.pathsep) if r.strip()]
    roots = ["/", os.path.expanduser("~"), *listed, *_config_roots()]
    return [os.path.normpath(os.path.expanduser(r.strip())) for r in roots]


def broad_root_error(path: str) -> Optional[str]:
    """Refusal message when ``path`` (absolute) is or contains a broad root."""
    if not path or not os.path.isabs(path):
        return None
    target = os.path.normpath(path)
    for root in _broad_roots():
        if os.path.commonpath([target, root]) == target:
            what = "it is a broad root" if target == root else f"it contains the broad root {root}"
            return (f"Refusing to search {target}: {what}, and a recursive walk there reads "
                    "GiBs and starves every other process on the disk. Narrow `path` to the "
                    "task or project directory, or use "
                    "z0_file_search (indexed, per-repository) for repository-wide lookups.")
    return None


_WRAPPERS = {"rtk", "sudo", "nice", "ionice", "timeout", "env", "command", "exec", "time", "nohup"}
_MAX_SHALLOW_DEPTH = 3  # find -maxdepth / rg --max-depth at or under this only lists directories


def _depth(tokens: list[str], flags: tuple[str, ...]) -> Optional[int]:
    for i, tok in enumerate(tokens):
        name, _, val = tok.partition("=")
        if name in flags:
            val = val or (tokens[i + 1] if i + 1 < len(tokens) else "")
            return int(val) if val.isdigit() else None
    return None


def _walk_paths(tokens: list[str]) -> list[str]:
    """Absolute path args of a whole-tree walk (find/du/grep -r/rg), [] when bounded."""
    while tokens and (tokens[0] in _WRAPPERS or "=" in tokens[0] or tokens[0].startswith("-")
                      or tokens[0].isdigit() or tokens[0][:-1].isdigit()):
        tokens = tokens[1:]
    if not tokens:
        return []
    prog, args = os.path.basename(tokens[0]), tokens[1:]
    if prog == "find":
        depth = _depth(args, ("-maxdepth",))
    elif prog == "rg":
        depth = _depth(args, ("--max-depth", "-d", "--maxdepth"))
    elif prog in ("grep", "egrep", "fgrep"):
        recursive = any(a in ("--recursive", "--dereference-recursive") or
                        (a.startswith("-") and not a.startswith("--") and ("r" in a or "R" in a))
                        for a in args)
        depth = None if recursive else 0
    elif prog == "du":
        depth = None
    else:
        return []
    if depth is not None and depth <= _MAX_SHALLOW_DEPTH:
        return []
    paths = (os.path.expanduser(os.path.expandvars(a)) for a in args)
    return [p for p in paths if os.path.isabs(p)]


def broad_walk_error(command: str) -> Optional[str]:
    """Refusal message when a shell command walks a whole tree that is or contains a broad root.

    Agents' ``find``/``du``/``grep -r``/``rg`` over ``~`` or a data-disk root read GiBs per
    call, and the reaped child's reads land on the gateway's read_bytes. Shallow listings
    (find -maxdepth <= 3, rg --max-depth <= 3) stay allowed. Unparseable input is not blocked.
    """
    import shlex
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None
    simple: list[str] = []
    for tok in [*tokens, ";"]:
        if tok and set(tok) <= set(";&|()"):
            for path in _walk_paths(simple):
                err = broad_root_error(path)
                if err:
                    return err.replace("Narrow `path`", "Narrow the walk (or use find -maxdepth "
                                       f"{_MAX_SHALLOW_DEPTH} to list)")
            simple = []
        else:
            simple.append(tok)
    return None
