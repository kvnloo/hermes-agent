"""``approvals.safe_delete_roots``: let the agent clean up after itself without a prompt.

A command whose ONLY findings are deletes (``rm -r``/``rm /abs``, ``git branch -D``) runs
without asking when every target it names is something the agent made and nothing is lost:

* every ``rm`` target resolves (``~`` and ``$VAR`` expanded, then ``realpath``) strictly inside a
  safe root, and is not the root itself; a target that is a git checkout must also be clean and pushed;
* every ``git worktree remove`` path in the same command is a worktree root inside a safe root
  with no uncommitted or untracked changes and no commit missing from a remote-tracking ref;
* every ``git branch -D`` branch exists and has no commit missing from a remote-tracking ref.

Anything the parser cannot read with certainty keeps today's behaviour (the normal prompt):
command substitution, subshells, braces, heredocs, redirections on a delete, assignments,
shell keywords, ``sudo``/``env``/``xargs`` in front of ``rm``, unknown ``rm``/``git`` options,
unset variables, ``~user``, relative targets without a ``cd /abs &&`` before them, globs outside
the last path component. The gate does not know the shell's working directory, so relative
targets resolve only against a ``cd`` in the same command joined by ``&&``.

Like the rest of the approval gate this is an accident-prevention heuristic (SECURITY.md §2.4),
not a boundary: ``$VAR`` values come from the agent process, not from the shell session.
"""

from __future__ import annotations

import glob
import os
import shlex
import subprocess
from pathlib import Path

# Detector descriptions this module may clear. Any other finding in the command keeps the prompt.
DELETE_FINDINGS = frozenset({
    "recursive delete",
    "recursive delete (long flag)",
    "recursive delete (flags after operands)",
    "delete in root path",
    "git branch force delete",
    "git branch force delete (long flags)",
    "git branch force delete (long flags, force-first)",
})

DEFAULT_SAFE_DELETE_ROOTS = ["<scratch>", "<kanban-workspaces>", "<build-outputs>"]
# ``<build-outputs>``: these names directly under a directory the command ``cd``-ed into.
BUILD_OUTPUT_NAMES = frozenset({
    "node_modules", "dist", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
})

_SEPARATORS = frozenset({";", "&&", "||", "|", "&"})
_REFUSED_TEXT = ("$(", "`", "<(", ">(", "<<", "\n", "\r", "#", "{", "}", "!", "\\")
_REFUSED_WORDS = frozenset({
    "if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done", "case", "esac",
    "select", "function", "export", "declare", "typeset", "local", "readonly", "read", "set",
    "unset", "source", ".", "eval", "exec", "alias", "shopt", "pushd", "popd", "builtin",
    "command", "trap", "[[", "time",
})
_RM_SHORT = frozenset("rRfvdiI")
_RM_LONG = frozenset({"--recursive", "--force", "--verbose", "--dir"})
_GLOB_CHARS = frozenset("*?[")
_GIT_TIMEOUT = 5.0


class _Unsafe(Exception):
    """The command cannot be shown to touch only safe targets."""


def _expand(word: str) -> str:
    """``~`` / ``~/x`` and ``$NAME`` / ``${NAME}`` from the agent environment; anything else refuses."""
    if word.startswith("~"):
        if word != "~" and not word.startswith("~/"):
            raise _Unsafe("~user")
        word = os.path.expanduser("~") + word[1:]
    out, i = [], 0
    while i < len(word):
        ch = word[i]
        if ch != "$":
            out.append(ch)
            i += 1
            continue
        braced = word.startswith("${", i)
        j = i + (2 if braced else 1)
        k = j
        while k < len(word) and (word[k] == "_" or word[k].isalnum()):
            k += 1
        name = word[j:k]
        if not name or name[0].isdigit() or (braced and not word.startswith("}", k)):
            raise _Unsafe("unsupported expansion")
        value = os.environ.get(name, "")
        # An unquoted value with blanks splits into several targets; with glob chars it expands.
        if not value or any(c.isspace() or c in _GLOB_CHARS for c in value):
            raise _Unsafe(f"${name} is unset or not a plain path")
        out.append(value)
        i = k + 1 if braced else k
    return "".join(out)


def _inside(path: str, root: str) -> bool:
    return path != root and path.startswith(root.rstrip(os.sep) + os.sep)


def _scratch_roots() -> list[str]:
    from hermes_constants import get_hermes_home
    home = get_hermes_home()
    roots = [home / "cache" / "scratch"]
    tmp = os.environ.get("TMPDIR", "")
    if tmp and _inside(os.path.realpath(tmp), os.path.realpath(home)):
        roots.append(Path(tmp))
    return [str(r) for r in roots]


def _kanban_roots() -> list[str]:
    roots = []
    override = os.environ.get("HERMES_KANBAN_WORKSPACES_ROOT", "").strip()
    if override:
        roots.append(os.path.expanduser(override))
    try:
        from hermes_cli.kanban_db import kanban_home
        base = Path(kanban_home()) / "kanban"
    except Exception:
        from hermes_constants import get_hermes_home
        base = get_hermes_home() / "kanban"
    roots.append(str(base / "workspaces"))
    roots.extend(glob.glob(str(base / "boards" / "*" / "workspaces")))
    return roots


def configured_roots(entries) -> tuple[list[str], bool]:
    """``(real root paths, build_outputs_enabled)`` for the ``approvals.safe_delete_roots`` value."""
    if entries is None:
        entries = DEFAULT_SAFE_DELETE_ROOTS
    if isinstance(entries, str) or not isinstance(entries, (list, tuple)):
        return [], False
    roots, build = [], False
    for entry in entries:
        entry = str(entry).strip()
        try:
            if entry == "<scratch>":
                paths = _scratch_roots()
            elif entry == "<kanban-workspaces>":
                paths = _kanban_roots()
            elif entry == "<build-outputs>":
                build = True
                continue
            else:
                paths = [_expand(entry)]
        except Exception:
            continue
        for path in paths:
            # A relative entry or one that names the filesystem root / home makes everything safe.
            real = os.path.realpath(path)
            if os.path.isabs(path) and real not in (os.sep, os.path.realpath(os.path.expanduser("~"))):
                roots.append(real)
    return roots, build


def _screen_syntax(command: str) -> None:
    """Refuse shell syntax this check does not read. Single-quoted text is literal, so an awk program
    (``awk '{print $4}'``) is fine; inside double quotes ``$(``, backticks and backslashes still refuse."""
    plain, quoted, quote = [], [], ""
    for ch in command:
        if quote:
            if ch == quote:
                quote = ""
            elif quote == '"':
                quoted.append(ch)
        elif ch in "'\"":
            quote = ch
            plain.append(" ")
        else:
            plain.append(ch)
    plain_text, quoted_text = "".join(plain), "".join(quoted)
    if any(t in plain_text for t in _REFUSED_TEXT) or any(t in quoted_text for t in ("$(", "`", "\\")):
        raise _Unsafe("shell syntax this check does not read")


def _segments(command: str) -> list[tuple[str, list[str]]]:
    """``[(separator before it, argv)]``; refuses anything beyond plain ``a && b; c | d`` lists."""
    _screen_syntax(command)
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError as exc:
        raise _Unsafe(str(exc)) from exc
    segments, argv, sep = [], [], ""
    for token in tokens:
        if token in _SEPARATORS:
            if not argv:
                raise _Unsafe("empty command")
            segments.append((sep, argv))
            argv, sep = [], token
        elif token and set(token) <= set(";&|()<>"):
            if "(" in token or ")" in token:
                raise _Unsafe("subshell")
            argv.append(token)  # a redirection; delete segments refuse it below
        else:
            argv.append(token)
    if argv:
        segments.append((sep, argv))
    elif segments:
        raise _Unsafe("trailing separator")
    for _, argv in segments:
        if "=" in argv[0] or argv[0] in _REFUSED_WORDS:
            raise _Unsafe("assignment or shell keyword")
    return segments


def _words(token: str) -> list[str]:
    return "".join(c if c.isalnum() or c in "._-/" else " " for c in token).split()


def _resolve(word: str, cwd: str | None) -> str:
    path = _expand(word)
    if not os.path.isabs(path):
        if cwd is None:
            raise _Unsafe(f"relative target {word!r} with no cd in this command")
        path = os.path.join(cwd, path)
    return path


def _rm_targets(argv: list[str], cwd: str | None) -> list[tuple[str, list[str]]]:
    targets, options_done = [], False
    for arg in argv[1:]:
        if not options_done and arg == "--":
            options_done = True
        elif not options_done and arg.startswith("--"):
            if arg not in _RM_LONG:
                raise _Unsafe(f"rm option {arg}")
        elif not options_done and arg.startswith("-") and arg != "-":
            if not set(arg[1:]) <= _RM_SHORT:
                raise _Unsafe(f"rm option {arg}")
        else:
            targets.append(arg)
    if not targets:
        raise _Unsafe("rm without a target")
    paths = []  # (path to check against the roots, existing paths it deletes)
    for word in targets:
        path = _resolve(word, cwd)
        parent, leaf = os.path.split(path.rstrip(os.sep))
        globbed = any(c in _GLOB_CHARS for c in leaf)
        # `.*` matches `..` in older shells; `x/..` and `x/.` name a parent / the dir itself.
        if leaf in ("", ".", "..") or (globbed and leaf.startswith(".")):
            raise _Unsafe(f"target {word!r}")
        if any(c in _GLOB_CHARS for c in parent):
            raise _Unsafe("glob outside the last path component")
        if globbed:
            # The glob only matches children of ``parent``; check ``parent`` as the deepest target.
            paths.append((os.path.join(parent, "_"), glob.glob(path)))
        else:
            paths.append((path, [path]))
    return paths


def _git(repo: str, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    proc = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", repo, *args],
        capture_output=True, text=True, timeout=_GIT_TIMEOUT, env=env, check=False,
    )
    if proc.returncode != 0:
        raise _Unsafe(f"git {args[0]} failed")
    return proc.stdout


def _unpushed(repo: str, rev: str) -> bool:
    if not _git(repo, "for-each-ref", "--count=1", "refs/remotes").strip():
        return True  # no remote-tracking refs: nothing can be shown to be pushed
    return _git(repo, "rev-list", "--count", rev, "--not", "--remotes").strip() != "0"


def _git_op(argv: list[str], cwd: str | None) -> tuple[str, str | None, list[str]]:
    """``(subcommand, repo dir, args)`` for ``git [-C dir] <sub> ...``; other global options refuse."""
    i, repo = 1, cwd
    while i < len(argv) and argv[i].startswith("-"):
        if argv[i] != "-C" or i + 1 >= len(argv):
            raise _Unsafe(f"git option {argv[i]}")
        repo = _resolve(argv[i + 1], cwd)
        i += 2
    if i >= len(argv):
        raise _Unsafe("bare git")
    return argv[i], repo, argv[i + 1:]


def _check_branch_delete(repo: str | None, args: list[str]) -> None:
    names = []
    for arg in args:
        if arg in ("-D", "-d", "--delete", "-f", "--force", "-q", "--quiet"):
            continue
        if arg.startswith("-"):
            raise _Unsafe(f"git branch option {arg}")
        names.append(arg)
    if repo is None or not names:
        raise _Unsafe("git branch -D needs a repository (cd or -C) and a branch")
    for name in names:
        ref = f"refs/heads/{name}"
        _git(repo, "rev-parse", "--verify", "--quiet", ref)
        if _unpushed(repo, ref):
            raise _Unsafe(f"branch {name} has commits on no remote")


def _check_worktree_remove(repo: str | None, args: list[str], roots: list[str]) -> None:
    paths = [a for a in args if a not in ("-f", "--force")]
    if len(paths) != 1 or paths[0].startswith("-"):
        raise _Unsafe("git worktree remove arguments")
    path = os.path.realpath(_resolve(paths[0], repo))
    if not any(_inside(path, root) for root in roots):
        raise _Unsafe("worktree outside the safe roots")
    if os.path.realpath(_git(path, "rev-parse", "--show-toplevel").strip()) != path:
        raise _Unsafe("not a worktree root")
    _check_checkout(path)


def _check_checkout(path: str) -> None:
    """A checkout about to be deleted holds no uncommitted or untracked change and no unpushed commit."""
    if _git(path, "status", "--porcelain", "--untracked-files=all").strip():
        raise _Unsafe("checkout has uncommitted changes")
    if _unpushed(path, "HEAD"):
        raise _Unsafe("checkout has commits on no remote")


def _check(command: str, roots: list[str], build_outputs: bool) -> None:
    deletes = 0
    cwd: str | None = None
    for sep, argv in _segments(command):
        if sep != "&&":
            cwd = None  # after `;`, `||` or `|` a failed cd would leave the old directory
        name = os.path.basename(argv[0])
        redirected = any(set(a) <= set("&|<>") for a in argv)
        if name == "cd":
            if len(argv) != 2 or redirected:
                raise _Unsafe("cd form")
            target = _expand(argv[1])
            if os.path.isabs(target):
                cwd = os.path.realpath(target)
            elif cwd is not None:
                cwd = os.path.realpath(os.path.join(cwd, target))
            continue
        if name in ("rm", "rm.exe"):
            if redirected:
                raise _Unsafe("redirection on a delete")
            for path, existing in _rm_targets(argv, cwd):
                real = os.path.realpath(path)
                build = (build_outputs and cwd is not None and os.path.basename(real) in BUILD_OUTPUT_NAMES
                         and os.path.dirname(real) == cwd
                         and cwd not in (os.sep, os.path.realpath(os.path.expanduser("~"))))
                if not build and not any(_inside(real, root) for root in roots):
                    raise _Unsafe(f"{path} is outside the safe roots")
                # A git checkout named as a target (not one nested deeper) must hold nothing unpushed.
                for item in existing:
                    if not os.path.islink(item) and os.path.lexists(os.path.join(item, ".git")):
                        _check_checkout(item)
            deletes += 1
            continue
        if name == "git":
            if redirected:
                raise _Unsafe("redirection on git")
            sub, repo, args = _git_op(argv, cwd)
            force_delete = "-D" in args or (
                any(a in ("-d", "--delete") for a in args) and any(a in ("-f", "--force") for a in args))
            if sub == "branch" and force_delete:
                _check_branch_delete(repo, args)
                deletes += 1
            elif sub == "worktree" and args[:1] == ["remove"]:
                _check_worktree_remove(repo, args[1:], roots)
                deletes += 1
            continue
        # Any other command: an `rm` or `git` it would run (sudo rm, ssh host 'rm -rf x', xargs rm)
        # is a delete this check has not read.
        if any(os.path.basename(w) in ("rm", "rm.exe", "git") for a in argv[1:] for w in _words(a)):
            raise _Unsafe("rm or git run by another command")
    if not deletes:
        raise _Unsafe("no delete found")


def safe_delete_clears(command: str, findings: list[tuple[str, str]], env_type: str) -> bool:
    """True when *findings* are all deletes and every target in *command* is a safe delete.

    Local backend only: on ssh/docker/other backends the paths name another filesystem."""
    if env_type != "local" or not findings or any(key not in DELETE_FINDINGS for key, _ in findings):
        return False
    try:
        from tools import approval_context
        roots, build_outputs = configured_roots(approval_context._get_approval_config().get("safe_delete_roots"))
        if not roots and not build_outputs:
            return False
        _check(command, roots, build_outputs)
    except _Unsafe:
        return False
    except Exception:  # never let a parse/git surprise approve, or break the gate
        return False
    return True
