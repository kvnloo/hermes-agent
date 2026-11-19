"""Refuse ``search_files`` roots whose recursive walk would read a whole disk.

A root is refused when it IS, or CONTAINS, a broad root: the filesystem root,
the user's home, or an entry of ``search_files_broad_roots`` in config.yaml
(for example a large data mount). Anything below a broad root (a project or
task directory) still searches normally. ``search_files_refuse_broad_roots:
false`` turns the check off.

Pure path arithmetic: the check never touches the disk, so a refused call
costs nothing and never spawns rg/find.
"""

import os
from typing import Optional


def _config() -> dict:
    try:
        from hermes_cli.config import load_config_readonly
        return load_config_readonly() or {}
    except Exception:
        return {}


def _home() -> str:
    from tools import file_operations as _fo  # lazy: tests monkeypatch _HOME there
    return _fo._HOME or os.path.expanduser("~")


def _broad_roots(cfg: dict) -> list[str]:
    extra = cfg.get("search_files_broad_roots") or []
    if isinstance(extra, str):
        extra = [extra]
    if not isinstance(extra, list):
        extra = []
    roots = [os.path.abspath(os.sep), _home(), *(str(r) for r in extra if str(r).strip())]
    return [os.path.normcase(os.path.normpath(os.path.expanduser(r.strip()))) for r in roots]


def broad_root_error(path: str) -> Optional[str]:
    """Refusal message when absolute ``path`` is or contains a broad root, else None."""
    if not path or not os.path.isabs(path):
        return None
    cfg = _config()
    if cfg.get("search_files_refuse_broad_roots") is False:
        return None
    target = os.path.normcase(os.path.normpath(path))
    for root in _broad_roots(cfg):
        try:
            if os.path.commonpath([target, root]) != target:
                continue
        except ValueError:  # different drives on Windows
            continue
        what = "it is a broad root" if target == root else f"it contains the broad root {root}"
        return (f"Refusing to search {target}: {what}, and a recursive walk there reads the whole "
                "disk and slows every other process using it. Narrow `path` to the project or "
                "task directory you actually need.")
    return None
