"""Screen the code an interpreter runs inline, so it gets the scan a shell command gets.

The gates see ``python3 -c ...``, a heredoc into an interpreter and an ``execute_code`` script as one
opaque "script execution" class. Once that class key is granted (session/always, or a
``command_allowlist`` entry), whatever the script does ran unasked: ``shutil.rmtree`` of the home
directory, ``os.system("rm -rf ~/x")``, ``exec(urlopen(url).read())``. This module reads the payload
and returns findings that each need their own grant:

* shell strings passed to process-spawn APIs, run through the shell detectors (*scan*);
* a short list of direct destructive or fetch-and-run APIs.

Python is read with :mod:`ast` (never executed); other languages with conservative regexes. A miss
costs no more than the class key alone did; a payload that cannot be read (syntax error, too large)
adds nothing, so the gate behaves as before. Like the rest of the gate this is an accident check for
a cooperating agent, not a sandbox: an author who wants past it can build the call at run time.
"""

import ast
import os
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
_LANGUAGE = {"node": "js", "bun": "js", "deno": "js"}
# Other languages, by regex: process-spawn calls whose string arguments are a shell command ...
_SPAWN_RES = {
    "js": re.compile(r"\b(?:execSync|exec|spawnSync|spawn|execFileSync|execFile|Deno\.Command|Deno\.run"
                     r"|Bun\.spawnSync|Bun\.spawn)\s*(?=\()"),
    "ruby": re.compile(r"\b(?:system|exec|spawn|IO\.popen|Open3\.\w+)\b[ \t]*(?=[(\s'\"])"),
    "perl": re.compile(r"\b(?:system|exec)\b[ \t]*(?=[(\s'\"])"),
    "php": re.compile(r"\b(?:shell_exec|system|exec|passthru|popen|proc_open)\s*(?=\()"),
}
# ... command-substitution literals (backticks, %x{}, qx{}, Bun's $`...`, AppleScript's do shell script) ...
_SUBST_RES = {
    "js": re.compile(r"\$`([^`]*)`"),
    "ruby": re.compile(r"`([^`]*)`|%x\{([^}]*)\}|%x\(([^)]*)\)"),
    "perl": re.compile(r"`([^`]*)`|\bqx\s*\{([^}]*)\}|\bqx\s*\(([^)]*)\)"),
    "php": re.compile(r"`([^`]*)`"),
    "applescript": re.compile(r'\bdo\s+shell\s+script\s+"((?:[^"\\]|\\.)*)"', re.IGNORECASE),
}
# ... recursive deletes, and eval of fetched content.
_DELETE_RES = {
    "js": re.compile(r"\b(?:rmSync|rm|rmdirSync|rmdir|Deno\.remove)\s*\([^;]{0,300}?\brecursive\s*:\s*true"),
    "ruby": re.compile(r"\bFileUtils\.(?:rm_rf|rm_r|remove_dir|remove_entry(?:_secure)?|rmtree)\b"),
    "perl": re.compile(r"\b(?:rmtree|remove_tree)\b"),
}
_EVAL_RE = re.compile(r"\b(?:eval|instance_eval|new\s+Function)\b")
_FETCH_RE = re.compile(
    r"\b(?:fetch|https?\.get|axios|URI\.open|open-uri|Net::HTTP|LWP|HTTP::Tiny|curl_exec)\b"
    r"|file_get_contents\s*\(\s*['\"]https?:")
_HOME_OR_ROOT_RE = re.compile(
    r"expanduser|Path\.home\(|\bHOME\b|USERPROFILE|^['\"](?:~|/(?:Users|home|root)?(?:/|['\"]))")


def screen_inline_code(language: str, source: str, scan) -> list[str]:
    """Findings for *source* written in *language* (an interpreter family from
    ``approval_detection._INTERPRETER_NAME_RES``, or ``applescript``); ``scan(shell)`` yields the
    shell detectors' findings for one extracted command string. Never raises on bad input."""
    if not source or len(source) > _MAX_SOURCE_CHARS:
        return []
    try:
        shells, findings = (_screen_python if language == "python" else _screen_regex)(language, source)
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
    from tools.approval_applescript import _PROGRAMS, _heredoc_body, _heredoc_operator, _osascript_program
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
        name = deobfuscate(word)
        family = own = "applescript" if os.path.basename(name).lower() == "osascript" else _interpreter_family(name)
        heredoc = _heredoc_operator(args)
        heredocs = _heredoc_operators(args) if heredoc is not None else []
        if family is None and heredoc is not None:
            # `cat <<'PY' | python3`: the body is the program of the interpreter the line pipes into.
            line_end = command.find("\n", end)
            piped = re.search(r"\|\s*(\S+)", command[end:line_end if line_end >= 0 else len(command)])
            family = _interpreter_family(deobfuscate(piped.group(1))) if piped else None
        if family is None:
            continue
        if heredoc is not None:
            # Bodies follow one another; the interpreter's stdin is the LAST redirection's body.
            body_start = start + len(segment)
            for delim, _quoted, strip_tabs in heredocs or [heredoc]:
                body, body_span = _heredoc_body(command, body_start, delim, strip_tabs)
                body_start = body_span[1]
            if strip_tabs:  # `<<-` strips leading tabs from every body line before the program sees it
                body = re.sub(r"(?m)^\t+", "", body)
            body_span = (start + len(segment), body_span[1])
            yield family, body
        if own == "applescript":
            yield family, _osascript_program(args, _PROGRAMS["osascript"])[0]
            continue
        tokens = _shell_segment_tokens(args, 0) if own else None
        if tokens and (payload := _flag_payload(family, tokens)):
            yield family, payload


def _heredoc_operators(args: str) -> list[tuple[str, bool, bool]]:
    """Every unquoted ``<<`` operator in *args*, in order (see ``_heredoc_operator``); empty when any
    delimiter is not a plain word."""
    from tools.approval_applescript import _HEREDOC_RE
    from tools.approval_detection import _scan_shell

    found = []
    for kind, i, _, quote in _scan_shell(args):
        if kind == "char" and quote is None and args.startswith("<<", i) and not args.startswith("<<<", i) \
                and (i == 0 or args[i - 1] != "<"):
            match = _HEREDOC_RE.match(args, i)
            if match is None:
                return []
            found.append((match.group("delim"), bool(match.group("q")), bool(match.group("dash"))))
    return found


def _flag_payload(family: str, args: list[str]) -> str | None:
    """The program text an execution flag owns (``-c CODE``, ``-cCODE``, ``--eval=CODE``, ``-le CODE``,
    ``eval CODE``). One walk with the same option-value ownership as ``_interpreter_exec_flag``, so a
    value such as ``-W -c`` is never taken for the flag."""
    from tools.approval_detection import _INTERPRETER_EXEC_FLAGS, _INTERPRETER_WITH_ARG, _powershell_command_payload
    if family == "powershell":
        return _powershell_command_payload(args)
    flags, with_arg = _INTERPRETER_EXEC_FLAGS[family], _INTERPRETER_WITH_ARG[family]
    skip_value = False
    for index, token in enumerate(args):
        if skip_value:
            skip_value = False
            continue
        rest = args[index + 1:]
        if token == "--" or not token.startswith("-"):
            if family == "deno" and token.lower() == "eval":
                # `deno eval --ext=ts CODE`: eval's own options come before the program.
                return next((arg for arg in rest if not arg.startswith("-")), None)
            return None
        option, equals, value = token.partition("=")
        if option in flags:
            return value if equals else next(iter(rest), None)
        if option.startswith("--"):
            skip_value = option in with_arg and not equals
            continue
        attached = next((short for short in with_arg if short.startswith("-") and not short.startswith("--")
                         and option.startswith(short) and len(option) > len(short)), None)
        if attached is None:
            # A short bundle: the first execution flag in it owns the rest of the token, else the next one.
            for position, char in enumerate(token[1:], 1):
                if f"-{char}" in flags:
                    return token[position + 1:] or next(iter(rest), None)
        skip_value = option in with_arg and not equals
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

    def qualname(func, depth: int = 0) -> str | None:
        parts = []
        while isinstance(func, ast.Attribute):
            parts.append(func.attr)
            func = func.value
        if isinstance(func, ast.Call) and depth < 3 and isinstance(func.func, ast.Name) \
                and func.func.id == "getattr" and len(func.args) >= 2 and isinstance(func.args[1], ast.Constant) \
                and isinstance(func.args[1].value, str):
            # getattr(subprocess, 'run')
            base = qualname(func.args[0], depth + 1)
            return ".".join([base, func.args[1].value, *reversed(parts)]) if base else None
        if not isinstance(func, ast.Name):
            return None
        bound = assigned.get(func.id)
        if depth < 3 and func.id not in aliases and isinstance(bound, (ast.Attribute, ast.Call)):
            # run = subprocess.run
            base = qualname(bound, depth + 1)
            return ".".join([base, *reversed(parts)]) if base else None
        return ".".join([aliases.get(func.id, func.id), *reversed(parts)])

    def first_arg(node):
        """The command argument: first positional, else ``args=``/``cmd=``/``command=``."""
        if node.args:
            return node.args[0]
        return next((kw.value for kw in node.keywords if kw.arg in ("args", "cmd", "command")), None)

    def resolved(arg):
        return assigned.get(arg.id, arg) if isinstance(arg, ast.Name) else arg

    def path_text(node, depth: int = 0) -> str:
        """Literal text of a path expression with local string variables substituted."""
        if isinstance(node, ast.Name) and node.id in assigned and depth < 3:
            return path_text(assigned[node.id], depth + 1)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return "".join(path_text(v.value if isinstance(v, ast.FormattedValue) else v, depth) for v in node.values)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return path_text(node.left, depth) + path_text(node.right, depth)
        if isinstance(node, ast.Call) and node.args and (qualname(node.func) or "").endswith(
                ("expanduser", "abspath", "realpath", "normpath")):
            return path_text(node.args[0], depth)
        if isinstance(node, ast.Call) and (qualname(node.func) or "").endswith("join") and node.args:
            return "/".join(path_text(a, depth) for a in node.args)
        return "x"

    # Local helpers that hand one of their parameters to a spawn API: def sh(c): subprocess.run(c, ...)
    helpers = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in fn.args.posonlyargs + fn.args.args]
            for inner in ast.walk(fn):
                if isinstance(inner, ast.Call) and qualname(inner.func) in _PY_SPAWN:
                    arg = first_arg(inner)
                    if isinstance(arg, ast.Name) and arg.id in params:
                        helpers[fn.name] = params.index(arg.id)

    shells, findings, fetches, execs = [], [], False, False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = qualname(node.func)
        arg = first_arg(node)
        if isinstance(node.func, ast.Name) and node.func.id in helpers and name not in _PY_SPAWN:
            index = helpers[node.func.id]
            arg = node.args[index] if index < len(node.args) else None
            name = "subprocess.run"
        if name in _PY_SPAWN and arg is not None and (text := _py_text(resolved(arg))) is not None:
            shells.append(text)
        elif name in _PY_DELETE and arg is not None:
            target = resolved(arg)
            if _HOME_OR_ROOT_RE.search(ast.unparse(target)) or _HOME_OR_ROOT_RE.search(repr(path_text(arg))) \
                    or any(isinstance(n, ast.Name) and n.id in assigned
                           and _HOME_OR_ROOT_RE.search(ast.unparse(assigned[n.id])) for n in ast.walk(arg)):
                findings.append(INLINE_DELETE_DESCRIPTION)
        fetches = fetches or name in _PY_FETCH
        execs = execs or name in _PY_EXEC
    if fetches and execs:
        findings.append(INLINE_FETCH_EXEC_DESCRIPTION)
    return shells, findings


def _screen_regex(language: str, source: str) -> tuple[list[str], list[str]]:
    lang = _LANGUAGE.get(language, language)
    if lang == "powershell":
        return [], []  # a `pwsh -c` payload already reaches the shell detectors (_powershell_command_payload)
    code = _code_mask(lang, source)

    def in_code(regex):
        """Matches that start in code, not inside a string literal or a comment (prose)."""
        return [m for m in regex.finditer(source) if code[m.start()]]

    shells = [_call_strings(source, m.end()) for m in in_code(_SPAWN_RES[lang])] if lang in _SPAWN_RES else []
    if lang in _SUBST_RES:
        shells += [next(filter(None, m.groups()), "").replace('\\"', '"') for m in _SUBST_RES[lang].finditer(source)]
    findings = [INLINE_DELETE_DESCRIPTION] if lang in _DELETE_RES and in_code(_DELETE_RES[lang]) else []
    if in_code(_EVAL_RE) and in_code(_FETCH_RE):
        findings.append(INLINE_FETCH_EXEC_DESCRIPTION)
    return [shell for shell in shells if shell.strip()], findings


def _code_mask(lang: str, source: str) -> list[bool]:
    """Per character: True where it is code, False inside a string literal's content or a comment.
    Quote characters themselves count as code, so a call whose argument is a string still matches
    at its name. Comments: ``//`` and ``/* */`` for JS and PHP, ``#`` for Ruby, Perl and PHP."""
    mask = [True] * len(source)
    line_comment = ("//",) if lang == "js" else ("//", "#") if lang == "php" else ("#",) if lang in ("ruby", "perl") else ()
    index, quote = 0, None
    while index < len(source):
        char = source[index]
        if quote:
            if char == "\\":
                mask[index:index + 2] = [False] * len(mask[index:index + 2])
                index += 2
                continue
            if char == quote:
                quote = None
            else:
                mask[index] = False
        elif char in "'\"" or (char == "`" and lang == "js"):
            quote = char
        elif lang in ("js", "php") and source.startswith("/*", index):
            end = source.find("*/", index + 2)
            end = len(source) if end < 0 else end + 2
            mask[index:end] = [False] * (end - index)
            index = end
            continue
        elif any(source.startswith(marker, index) for marker in line_comment) and (
                char != "#" or index == 0 or source[index - 1] in " \t\n;"):
            end = source.find("\n", index)
            end = len(source) if end < 0 else end
            mask[index:end] = [False] * (end - index)
            index = end
            continue
        index += 1
    return mask


def _call_strings(source: str, pos: int) -> str:
    """The string literals of the call at *pos*, up to its closing bracket (or the end of the statement
    for a paren-less Ruby/Perl call): one literal is the command, several an argv joined as the shell
    would quote it (``spawnSync('sh', ['-c', 'rm -rf x'])`` reads ``sh -c 'rm -rf x'``)."""
    strings, buf, quote, depth = [], [], None, 0
    stack: list[str] = []  # open brackets; a string inside an object literal / hash is an option value
    index, end = pos, min(len(source), pos + 4_000)
    while index < end:
        char = source[index]
        if quote:
            if char == "\\" and index + 1 < end:
                buf.append(source[index + 1])
                index += 1
            elif char == quote:
                if "{" not in stack:
                    strings.append("".join(buf))
                buf, quote = [], None
            else:
                buf.append(char)
        elif char in "'\"`":
            quote = char
        elif char in "([{":
            depth += 1
            stack.append(char)
        elif char in ")]}" or (depth == 0 and char in ";\n"):
            depth -= 1
            if stack:
                stack.pop()
            if depth <= 0:
                break
        index += 1
    return strings[0] if len(strings) == 1 else shlex.join(strings)


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
