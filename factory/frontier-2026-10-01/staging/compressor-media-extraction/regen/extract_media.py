#!/usr/bin/env python3
"""Regenerate the compressor image/media extraction on any hermes-agent checkout.

Moves the image/media cluster of ``agent/context_compressor.py`` into
``agent/context_compressor_media.py`` as a byte-verbatim move:

* every moved top-level statement keeps its exact source text (leading comment block and,
  for constants, a trailing comment block that ends in a blank line);
* the facade imports from the sibling only the moved names it still reads itself (no
  re-export shim) and drops imports that only the moved code used;
* every ``from agent.context_compressor import ...`` statement anywhere in the tree that
  names a moved symbol is split so the moved names come from the sibling (module level
  and function-local imports alike);
* dotted text references ``[agent.]context_compressor.<moved>`` in tracked text files are
  repointed to ``context_compressor_media``.

It refuses (exit 2) instead of guessing when the tree no longer matches the recipe: a
moved name is missing or defined twice, the moved code reads a free name the header does
not provide, an affected import carries a comment, or the facade binds a moved name some
other way. Stdlib only; run it from anywhere:

    python3 extract_media.py /path/to/hermes-agent-checkout

Then run ``verify_media.py <base> <head>`` for the parity/no-shim gates.

Recipe provenance: the topic cut and module name follow NousResearch/hermes-agent#80636
(andrexibiza, "extract content/media strip helpers (LB4)"), rebuilt for current main
without that PR's re-export seam (AGENTS.md: no re-export shims for internal moves).
"""

from __future__ import annotations

import ast
import builtins
import re
import subprocess
import sys
from pathlib import Path

FACADE = "agent/context_compressor.py"
SIBLING = "agent/context_compressor_media.py"
FACADE_MOD = "agent.context_compressor"
SIBLING_MOD = "agent.context_compressor_media"

# Moved names. Source order in the facade is preserved in the sibling regardless of the
# order here. Content-text helpers (_part_text, _content_text_for_contains,
# _append_text_to_content, ...) deliberately stay: they are text utilities, not media.
MOVED = (
    "_MAX_KEEP_TOOL_IMAGES",
    "_replace_image_parts",
    "_tool_result_parts",
    "_tool_content_has_images",
    "_strip_images_from_tool_msg",
    "_rewritten",
    "_retire_stale_tool_result_images",
    "_image_payload",
    "evict_stale_outbound_tool_images",
    "_IMAGE_PART_TYPES",
    "_is_image_part",
    "_content_has_images",
    "_strip_images_from_content",
    "_strip_historical_media",
    "_summary_part_text",
    "_image_part_label",
)

# Imports the sibling header provides. Every free name of the moved code must resolve to
# one of these, another moved name, or a builtin; anything else aborts the run.
SIBLING_HEADER_IMPORTS = {
    "typing": ("Any", "Dict", "List", "Optional", "Tuple"),
    "agent.image_eviction_policy": ("outbound_image_retire_count",),
    "agent.turn_context": ("drop_stale_api_content",),
}

SIBLING_DOCSTRING = '''"""Image and media handling for context compression.

Compaction-time retirement of historical image payloads, the send-path eviction of stale
tool-result images, and the summarizer-facing labels for non-text content parts.
``agent.context_compressor`` imports this module at load time, so it must never import the
facade back.
"""'''

TEXT_SUFFIXES = (".py", ".md", ".mdx", ".rst", ".txt")
LINE_LIMIT = 100


class RecipeMismatch(SystemExit):
    def __init__(self, msg: str) -> None:
        print(f"RECIPE MISMATCH: {msg}", file=sys.stderr)
        super().__init__(2)


def _bound_name(node: ast.stmt) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def _segment(lines: list[str], node: ast.stmt) -> tuple[int, int]:
    """0-based inclusive [start, end] of a node plus its attached comments."""
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]) - 1
    end = node.end_lineno - 1
    while start > 0 and _is_comment(lines[start - 1]) and not lines[start - 1].startswith((" ", "\t")):
        start -= 1
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        probe = end + 1
        while probe < len(lines) and _is_comment(lines[probe]) and not lines[probe].startswith((" ", "\t")):
            probe += 1
        # A trailing comment block belongs to the constant only when a blank line closes it;
        # otherwise it is the leading comment of the next statement.
        if probe > end + 1 and (probe >= len(lines) or not lines[probe].strip()):
            end = probe - 1
    return start, end


def _free_names(nodes: list[ast.stmt]) -> set[str]:
    """Names read (Load) by the moved code that it does not bind itself."""
    loads: set[str] = set()
    bound: set[str] = set()
    for top in nodes:
        for n in ast.walk(top):
            if isinstance(n, ast.Name):
                (loads if isinstance(n.ctx, ast.Load) else bound).add(n.id)
            elif isinstance(n, ast.arg):
                bound.add(n.arg)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(n.name)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                bound.update((a.asname or a.name).split(".")[0] for a in n.names)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                bound.add(n.name)
    return loads - bound


def _names_read(tree: ast.Module) -> set[str]:
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def _render_import(module: str, aliases: list[ast.alias], indent: str, multiline: bool) -> str:
    names = [a.name if not a.asname else f"{a.name} as {a.asname}" for a in aliases]
    single = f"{indent}from {module} import {', '.join(names)}"
    if not multiline and len(single) <= LINE_LIMIT:
        return single
    body = "".join(f"{indent}    {n},\n" for n in names)
    return f"{indent}from {module} import (\n{body}{indent})"


def _join_segments(chunks: list[str]) -> str:
    return "\n\n\n".join(c.rstrip("\n") for c in chunks) + "\n"


def build_sibling_and_facade(root: Path) -> tuple[list[str], str]:
    facade_path = root / FACADE
    if (root / SIBLING).exists():
        raise RecipeMismatch(f"{SIBLING} already exists")
    src = facade_path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)

    by_name: dict[str, list[ast.stmt]] = {}
    for node in tree.body:
        name = _bound_name(node)
        if name:
            by_name.setdefault(name, []).append(node)
    missing = [n for n in MOVED if n not in by_name]
    dupes = [n for n in MOVED if len(by_name.get(n, [])) > 1]
    if missing or dupes:
        raise RecipeMismatch(f"missing={missing} defined-twice={dupes}")
    # A moved name must be bound exactly once at top level and nowhere else in the facade.
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            clash = {(a.asname or a.name) for a in node.names} & set(MOVED)
            if clash:
                raise RecipeMismatch(f"facade imports moved name(s) {sorted(clash)} at line {node.lineno}")

    moved_nodes = sorted((by_name[n][0] for n in MOVED), key=lambda n: n.lineno)
    segments = [_segment(lines, n) for n in moved_nodes]
    for (s1, e1), (s2, _e2) in zip(segments, segments[1:]):
        if s2 <= e1:
            raise RecipeMismatch("overlapping segments")

    free = _free_names(moved_nodes) - set(MOVED) - set(dir(builtins))
    provided = {name for names in SIBLING_HEADER_IMPORTS.values() for name in names}
    unresolved = free - provided
    if unresolved:
        raise RecipeMismatch(f"moved code reads names the sibling header lacks: {sorted(unresolved)}")

    # ── sibling ────────────────────────────────────────────────────────────────
    header = [SIBLING_DOCSTRING, ""]
    stdlib = [(m, n) for m, n in SIBLING_HEADER_IMPORTS.items() if not m.startswith("agent.")]
    local = [(m, n) for m, n in SIBLING_HEADER_IMPORTS.items() if m.startswith("agent.")]
    for group in (stdlib, local):
        used_group = [(m, [x for x in names if x in free]) for m, names in group]
        used_group = [(m, names) for m, names in used_group if names]
        for m, names in used_group:
            header.append(f"from {m} import {', '.join(names)}")
        if used_group:
            header.append("")
    seg_text = ["".join(lines[s : e + 1]) for s, e in segments]
    sibling_src = "\n".join(header) + "\n\n" + _join_segments(seg_text)
    (root / SIBLING).write_text(sibling_src, encoding="utf-8")

    # ── facade: cut segments, closing each gap to the larger of its two blank runs (max 2) ──
    delete = set()
    for s, e in segments:
        delete.update(range(s, e + 1))
    # Blank lines whose nearest non-blank neighbours are both deleted go too.
    i = 0
    while i < len(lines):
        if lines[i].strip() == "" and i not in delete:
            j = i
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            prev_del = i > 0 and (i - 1) in delete
            next_del = j < len(lines) and j in delete
            if prev_del and next_del:
                delete.update(range(i, j))
            i = j
        else:
            i += 1
    out: list[str] = []
    i = 0
    while i < len(lines):
        if i not in delete:
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < len(lines) and j in delete:
            j += 1
        # blank run already emitted before the gap
        before = 0
        while before < len(out) and out[len(out) - 1 - before].strip() == "":
            before += 1
        after = 0
        while j + after < len(lines) and lines[j + after].strip() == "" and (j + after) not in delete:
            after += 1
        want = min(max(before, after), 2)
        # trim the blank run on both sides to `want` in total
        while before > 0:
            out.pop()
            before -= 1
        out.extend(["\n"] * want)
        i = j + after
    new_facade = "".join(out)

    # Imports only the moved code used, then the sibling import of names the facade still reads.
    ftree = ast.parse(new_facade)
    reads = _names_read(ftree)
    attr_reads = {n.value.id for n in ast.walk(ftree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    needed_from_sibling = sorted(n for n in MOVED if n in reads)
    orig_reads = _names_read(tree)
    flines = new_facade.splitlines(keepends=True)
    edits: list[tuple[int, int, str]] = []
    anchor_line = None
    for node in ftree.body:
        if not isinstance(node, ast.ImportFrom) or node.level:
            continue
        if node.module == "agent.context_compressor_summary":
            anchor_line = node.end_lineno
        dead = [
            a for a in node.names
            if (a.asname or a.name) not in reads | attr_reads and (a.asname or a.name) in orig_reads
            and (a.asname or a.name) in free
        ]
        if not dead:
            continue
        keep = [a for a in node.names if a not in dead]
        seg = "".join(flines[node.lineno - 1 : node.end_lineno])
        if "#" in seg:
            raise RecipeMismatch(f"facade import at line {node.lineno} carries a comment")
        repl = "" if not keep else _render_import(node.module, keep, "", node.end_lineno > node.lineno) + "\n"
        edits.append((node.lineno - 1, node.end_lineno, repl))
    if anchor_line is None:
        raise RecipeMismatch("facade no longer imports agent.context_compressor_summary (anchor)")
    sibling_import = _render_import(
        SIBLING_MOD, [ast.alias(name=n) for n in needed_from_sibling], "", True
    ) + "\n"
    edits.append((anchor_line, anchor_line, sibling_import))
    for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
        flines[start:end] = [repl] if repl else []
    (root / FACADE).write_text("".join(flines), encoding="utf-8")
    return needed_from_sibling, sibling_src


def rewrite_callers(root: Path) -> list[str]:
    files = subprocess.run(
        ["git", "-C", str(root), "ls-files", "*.py"], check=True, capture_output=True, text=True
    ).stdout.split()
    touched: list[str] = []
    moved = set(MOVED)
    for rel in files:
        if rel in (FACADE, SIBLING):
            continue
        path = root / rel
        if not path.is_file():
            continue
        src = path.read_text(encoding="utf-8")
        if FACADE_MOD not in src and "context_compressor" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines(keepends=True)
        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == FACADE_MOD:
                if any(a.name == "*" for a in node.names):
                    raise RecipeMismatch(f"{rel}:{node.lineno} star import from the facade")
                hit = [a for a in node.names if a.name in moved]
                if not hit:
                    continue
                keep = [a for a in node.names if a.name not in moved]
                seg = "".join(lines[node.lineno - 1 : node.end_lineno])
                if "#" in seg:
                    raise RecipeMismatch(f"{rel}:{node.lineno} affected import carries a comment")
                first = lines[node.lineno - 1]
                indent = first[: len(first) - len(first.lstrip())]
                last = lines[node.end_lineno - 1].rstrip("\r\n")
                if node.col_offset != len(indent) or node.end_col_offset != len(last):
                    raise RecipeMismatch(f"{rel}:{node.lineno} affected import shares its line with other code")
                was_multi = node.end_lineno > node.lineno
                parts = []
                if keep:
                    parts.append(_render_import(FACADE_MOD, keep, indent, was_multi and len(keep) >= 2))
                parts.append(_render_import(SIBLING_MOD, hit, indent, len(hit) >= 2))
                edits.append((node.lineno - 1, node.end_lineno, "\n".join(parts) + "\n"))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == FACADE_MOD:
                        # `import agent.context_compressor as x` + x.<moved> must be repointed by hand.
                        alias = a.asname or a.name
                        pat = re.compile(rf"\b{re.escape(alias)}\.({'|'.join(MOVED)})\b")
                        if pat.search(src):
                            raise RecipeMismatch(f"{rel}: module-alias access to a moved name via {alias}")
        if not edits:
            continue
        for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
            lines[start:end] = [repl]
        path.write_text("".join(lines), encoding="utf-8")
        touched.append(rel)
    return touched


def rewrite_text_refs(root: Path) -> list[str]:
    files = subprocess.run(
        ["git", "-C", str(root), "ls-files"], check=True, capture_output=True, text=True
    ).stdout.split()
    pat = re.compile(rf"\b((?:agent\.)?)context_compressor\.({'|'.join(MOVED)})\b")
    touched = []
    for rel in files:
        if rel in (FACADE, SIBLING) or not rel.endswith(TEXT_SUFFIXES):
            continue
        path = root / rel
        if not path.is_file():
            continue
        try:
            src = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in src.splitlines():
            if pat.search(line) and re.search(r"\b(patch|setattr|getattr|delattr)\b", line):
                # A patch target must name where production reads (AGENTS.md); never repoint blindly.
                raise RecipeMismatch(f"{rel}: dotted reference to a moved name inside a patch/attr call: {line.strip()}")
        new = pat.sub(r"\1context_compressor_media.\2", src)
        if new != src:
            path.write_text(new, encoding="utf-8")
            touched.append(rel)
    return touched


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    root = Path(argv[1]).resolve()
    imported, _ = build_sibling_and_facade(root)
    callers = rewrite_callers(root)
    texts = rewrite_text_refs(root)
    print(f"facade imports from sibling: {', '.join(imported)}")
    print(f"import statements rewritten in: {', '.join(callers) or '-'}")
    print(f"text references repointed in: {', '.join(texts) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
