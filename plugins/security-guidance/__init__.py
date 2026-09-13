"""security-guidance plugin — fast pattern-matched security warnings on file writes.

Scans content written by ``write_file`` / ``patch`` / ``skill_manage`` for known dangerous patterns
and appends a ``⚠️ Security guidance`` block to the tool result; the file is still written and the
model self-corrects next turn. Warn (not block) by default because patterns have a real false-positive
rate (``eval(`` in a tokenizer, ECB in a test fixture); ``SECURITY_GUIDANCE_BLOCK=1`` refuses the write
instead, ``SECURITY_GUIDANCE_DISABLE=1`` is a kill switch. Pattern data: ``patterns.py`` (Apache-2.0 fork).
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from . import patterns as _patterns

logger = logging.getLogger(__name__)

# tool name -> (path_arg_name, content_arg_names). Every populated content field is scanned
# (patch's new_string vs raw patch text; skill_manage's file_path is the path inside the skill dir).
_TARGET_TOOLS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "write_file": ("path", ("content",)),
    "patch": ("path", ("new_string", "patch")),
    # skill_manage legacy flat single-op shape: the handler still accepts
    # top-level file_path/file_content/new_string for old transcripts and
    # staged-write replay (no longer advertised). The advertised operations[]
    # shape — where those keys live one level down inside each op — is handled
    # in _extract_path_and_content, since it doesn't fit the flat (path_key,
    # content_keys) tuple shape above.
    "skill_manage": ("file_path", ("file_content", "new_string")),
}

# Above this we skip: matching a multi-MB blob has poor signal and slows the agent loop.
_MAX_SCAN_BYTES = 256 * 1024

_TRUTHY = {"1", "true", "yes", "on"}


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in _TRUTHY


def _compile_rules() -> List[Dict[str, Any]]:
    """Pre-compile regexes once; substrings stay plain (``in`` beats a literal regex)."""
    compiled: List[Dict[str, Any]] = []
    for rule in _patterns.SECURITY_PATTERNS:
        try:
            regex = re.compile(rule["regex"]) if rule.get("regex") else None
        except re.error as err:
            logger.warning("security-guidance: skipping rule %s — invalid regex %r: %s", rule["ruleName"], rule["regex"], err)
            continue
        compiled.append({
            "ruleName": rule["ruleName"], "reminder": rule["reminder"], "path_filter": rule.get("path_filter"),
            "path_check": rule.get("path_check"), "substrings": tuple(rule.get("substrings", ())), "regex": regex,
        })
    return compiled


_COMPILED: List[Dict[str, Any]] = _compile_rules()


def _rule_matches(entry: Dict[str, Any], path: str, content: str) -> bool:
    """One rule against one write; a raising path predicate is a non-match. path_check rules fire on
    the path ALONE and never scan content; path_filter gates content rules to relevant file types."""
    try:
        if entry["path_check"] is not None:
            return bool(entry["path_check"](path))
        if entry["path_filter"] is not None and not entry["path_filter"](path):
            return False
    except Exception:
        return False
    return any(sub in content for sub in entry["substrings"]) or (entry["regex"] is not None and bool(entry["regex"].search(content)))


def _scan_content(path: str, content: str) -> List[Tuple[str, str]]:
    """Return [(ruleName, reminder), ...]; each rule fires at most once per call."""
    if not content or len(content.encode("utf-8", errors="ignore")) > _MAX_SCAN_BYTES:
        return []
    path = path or ""
    return [(e["ruleName"], e["reminder"]) for e in _COMPILED if _rule_matches(e, path, content)]


def _scan_args(tool_name: str, args: Any) -> List[Tuple[str, str]]:
    """Shared scan for both hooks (block mode via pre_tool_call, warn mode via transform)."""
    spec = _TARGET_TOOLS.get(tool_name)
    if _env_flag("SECURITY_GUIDANCE_DISABLE") or spec is None or not isinstance(args, dict):
        return []
    out: List[Tuple[str, str]] = []
    # skill_manage's advertised (schema-pinned) call shape is an operations[]
    # array: each op nests its own file_path / file_content / new_string /
    # content one level down. Scan every op against its own path so warn/block
    # behavior matches an equivalent write_file / patch call. The legacy flat
    # single-op shape (top-level file_path/file_content/new_string) is still
    # accepted by the handler for old transcripts / staged-write replay — it
    # falls through to the generic path-key lookup below.
    if tool_name == "skill_manage" and isinstance(args.get("operations"), list):
        for op in args["operations"]:
            if not isinstance(op, dict):
                continue
            path = op.get("file_path") or ""
            if not isinstance(path, str):
                path = ""
            # content is the create / full-rewrite body and can also carry
            # code (e.g. a patch of scripts/run.py); scan it too. old_string is
            # the text being removed — scanning it would warn about content
            # being deleted, so it is intentionally excluded.
            for ck in ("file_content", "new_string", "content"):
                val = op.get(ck)
                if isinstance(val, str) and val:
                    out.append((path, val))
        return out
    path_key, content_keys = spec
    path = args.get(path_key) or ""
    if not isinstance(path, str):
        path = ""
    for ck in content_keys:
        val = args.get(ck)
        if isinstance(val, str) and val:
            out.append((path, val))
    return out


def _format_warning_block(findings: List[Tuple[str, str]]) -> str:
    """Render findings into the Markdown block appended to the tool result."""
    names = ", ".join(name for name, _ in findings)
    lines = ["", "---", f"⚠️ Security guidance — {len(findings)} pattern{'s' if len(findings) != 1 else ''} matched ({names})", ""]
    for _, reminder in findings:
        lines += [reminder, ""]
    lines.append(
        "Pattern matches can be false positives. If the construct is safe in this "
        "context, briefly document why in a code comment and continue. Otherwise, "
        "fix the code before moving on."
    )
    return "\n".join(lines)


def _on_pre_tool_call(tool_name: str = "", args: Any = None, **_: Any) -> Optional[Dict[str, str]]:
    """Block mode only: refuse the write if any pattern matches (None = let it through)."""
    findings = _scan_args(tool_name, args) if _env_flag("SECURITY_GUIDANCE_BLOCK") else []
    if not findings:
        return None
    return {
        "action": "block",
        "message": "security-guidance refused this write: " + _format_warning_block(findings) + "\n\nTo override, unset SECURITY_GUIDANCE_BLOCK and retry.",
    }


def _on_transform_tool_result(tool_name: str = "", args: Any = None, result: Any = None, **_: Any) -> Optional[str]:
    """Warn mode: append the warning block to the result string (None = unchanged)."""
    # In block mode pre_tool_call already handled it — the tool didn't run, no result to wrap.
    findings = [] if _env_flag("SECURITY_GUIDANCE_BLOCK") or not isinstance(result, str) else _scan_args(tool_name, args)
    if not findings:
        return None
    # Don't decorate error results — the model already has bigger problems.
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "error" in parsed and len(parsed) <= 2:
            return None
    except (ValueError, TypeError):
        pass
    return result + "\n\n" + _format_warning_block(findings)


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("transform_tool_result", _on_transform_tool_result)
