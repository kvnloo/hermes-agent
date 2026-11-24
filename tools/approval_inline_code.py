"""Screen the code an interpreter runs inline, so it gets the scan a shell command gets.

The gates see ``python3 -c ...``, a heredoc into an interpreter and an ``execute_code`` script as one
opaque "script execution" class. Once that class key is granted (session/always, or a
``command_allowlist`` entry), whatever the script does ran unasked: ``shutil.rmtree`` of the home
directory, ``os.system("rm -rf ~/x")``, ``exec(urlopen(url).read())``. This module reads the payload
and returns findings that each need their own grant:

* shell strings passed to process-spawn APIs, run through the shell detectors (*scan*);
* a short list of direct destructive or fetch-and-run APIs.

Python is read with :mod:`ast` (never executed). A miss
costs no more than the class key alone did; a payload that cannot be read (syntax error, too large)
adds nothing, so the gate behaves as before. Like the rest of the gate this is an accident check for
a cooperating agent, not a sandbox: an author who wants past it can build the call at run time.
"""

import ast
import re
import shlex

INLINE_DELETE_DESCRIPTION = "recursive delete via inline code"
INLINE_FETCH_EXEC_DESCRIPTION = "inline code runs downloaded content (fetch then exec/eval)"

_MAX_SOURCE_CHARS = 256_000
# Cheap pre-filter: a command naming no interpreter skips the word walk.
_INTERPRETER_WORD_RE = re.compile(r"(?i)py|node|perl|ruby|php|pwsh|powershell|bun|deno|osascript")

_PY_SPAWN = frozenset({
    "os.system", "os.popen", "subprocess.run", "subprocess.call", "subprocess.check_call",
    "subprocess.check_output", "subprocess.Popen", "subprocess.getoutput", "subprocess.getstatusoutput",
})
_PY_DELETE = frozenset({"shutil.rmtree", "os.remove", "os.unlink", "os.rmdir", "os.removedirs"})
_PY_FETCH = frozenset({
    "urllib.request.urlopen", "urllib.request.urlretrieve", "urllib2.urlopen", "requests.get", "requests.post",
    "requests.request", "httpx.get", "httpx.post",
})
_PY_EXEC = frozenset({"exec", "eval", "builtins.exec", "builtins.eval"})
# The path argument's source text: the home directory however it is spelled, or the filesystem root.
_HOME_OR_ROOT_RE = re.compile(
    r"expanduser|Path\.home\(|\bHOME\b|USERPROFILE|^['\"](?:~|/(?:Users|home|root)?(?:/|['\"]))")


def screen_inline_code(language: str, source: str, scan) -> list[str]:
    """Findings for *source* written in *language* (an interpreter family from
    ``approval_detection._INTERPRETER_NAME_RES``, or ``applescript``); ``scan(shell)`` yields the
    shell detectors' findings for one extracted command string. Never raises on bad input."""
    if not source or len(source) > _MAX_SOURCE_CHARS or language != "python":
        return []
    try:
        shells, findings = _screen_python(language, source)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return []
    for shell in shells:
        findings.extend(scan(shell))
    return list(dict.fromkeys(findings))


def screen_command_inline_code(command: str, scan) -> list[str]:
    """:func:`screen_inline_code` over every program *command* hands an interpreter inline: an
    execution flag's value (``python3 -c``, ``node -e``, ``deno eval``, ``pwsh -c``) and a heredoc
    body fed to one directly or through a pipe (``python3 <<'PY'``, ``cat <<'PY' | python3``)."""
    if not _INTERPRETER_WORD_RE.search(command):
        return []
    findings = []
    for language, source in _inline_programs(command):
        findings.extend(screen_inline_code(language, source, scan))
    return list(dict.fromkeys(findings))


def _inline_programs(command: str):
    from tools.approval_applescript import _heredoc_body, _heredoc_operator
    from tools.approval_detection import (
        _deobfuscate_shell_word_for_detection as deobfuscate, _interpreter_family, _iter_shell_command_word_spans,
        _shell_command_segment, _shell_segment_tokens,
    )
    body_span = (-1, -1)  # a heredoc body already read; command words inside it are program text
    for start, end, word in _iter_shell_command_word_spans(command):
        if body_span[0] <= start < body_span[1]:
            continue
        segment = _shell_command_segment(command, start)
        args = segment[end - start:]
        family = own = _interpreter_family(deobfuscate(word))
        heredoc = _heredoc_operator(args)
        if family is None and heredoc is not None:
            # `cat <<'PY' | python3`: the body is the program of the interpreter the line pipes into.
            line_end = command.find("\n", end)
            piped = re.search(r"\|\s*(\S+)", command[end:line_end if line_end >= 0 else len(command)])
            family = _interpreter_family(deobfuscate(piped.group(1))) if piped else None
        if family is None:
            continue
        if heredoc is not None:
            body, body_span = _heredoc_body(command, start + len(segment), heredoc[0], heredoc[2])
            yield family, body
        tokens = _shell_segment_tokens(args, 0) if own else None
        if tokens and (payload := _flag_payload(family, tokens)):
            yield family, payload


def _flag_payload(family: str, args: list[str]) -> str | None:
    """The program text an execution flag owns (``-c CODE``, ``--eval=CODE``, ``-le CODE``, ``eval CODE``)."""
    from tools.approval_detection import _interpreter_exec_flag, _powershell_command_payload
    if family == "powershell":
        return _powershell_command_payload(args)
    flag = _interpreter_exec_flag(family, args)
    if flag is None:
        return None
    for index, token in enumerate(args):
        option, equals, value = token.partition("=")
        if option == flag and equals:
            return value
        bundled = len(flag) == 2 and token[:1] == "-" and token[1:2] != "-" and token.endswith(flag[1])
        if option == flag or bundled:
            return next(iter(args[index + 1:]), None)
    return None


def _screen_python(_language: str, source: str) -> tuple[list[str], list[str]]:
    tree = ast.parse(source)
    aliases, assigned = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            assigned[node.targets[0].id] = node.value

    def qualname(func) -> str | None:
        parts = []
        while isinstance(func, ast.Attribute):
            parts.append(func.attr)
            func = func.value
        if not isinstance(func, ast.Name):
            return None
        return ".".join([aliases.get(func.id, func.id), *reversed(parts)])

    shells, findings, fetches, execs = [], [], False, False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = qualname(node.func)
        arg = node.args[0] if node.args else None
        if name in _PY_SPAWN and arg is not None and (text := _py_text(arg)) is not None:
            shells.append(text)
        elif name in _PY_DELETE and arg is not None:
            target = assigned.get(arg.id, arg) if isinstance(arg, ast.Name) else arg
            if _HOME_OR_ROOT_RE.search(ast.unparse(target)):
                findings.append(INLINE_DELETE_DESCRIPTION)
        fetches = fetches or name in _PY_FETCH
        execs = execs or name in _PY_EXEC
    if fetches and execs:
        findings.append(INLINE_FETCH_EXEC_DESCRIPTION)
    return shells, findings


def _py_text(node) -> str | None:
    """A spawn call's command text: a string, or an argv list joined as the shell would quote it.
    None for a bare variable (``subprocess.run(cmd)``)."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return shlex.join(map(_py_part, node.elts))
    return _py_part(node) if isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp)) else None


def _py_part(node) -> str:
    """Literal text of a string expression; a non-literal part reads ``x`` (``f"rm -rf {d}"`` is ``rm -rf x``)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(map(_py_part, node.values))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _py_part(node.left) + _py_part(node.right)
    return "x"
