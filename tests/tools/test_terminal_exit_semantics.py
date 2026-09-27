"""Tests for terminal command exit code semantic interpretation."""

import pytest

from tools.terminal_tool_result import _interpret_exit_code


class TestInterpretExitCode:
    """Test _interpret_exit_code returns correct notes for known command semantics."""

    # ---- exit code 0 always returns None ----

    def test_success_returns_none(self):
        assert _interpret_exit_code("grep foo bar", 0) is None
        assert _interpret_exit_code("diff a b", 0) is None
        assert _interpret_exit_code("test -f /etc/passwd", 0) is None

    # ---- grep / rg family: exit 1 = no matches ----

    @pytest.mark.parametrize("cmd", [
        "grep 'pattern' file.txt",
        "egrep 'pattern' file.txt",
        "fgrep 'pattern' file.txt",
        "rg 'foo' .",
        "ag 'foo' .",
        "ack 'foo' .",
    ])
    def test_grep_family_no_matches(self, cmd):
        result = _interpret_exit_code(cmd, 1)
        assert result is not None
        assert "no matches" in result.lower()


    # ---- diff: exit 1 = files differ ----

    def test_diff_files_differ(self):
        result = _interpret_exit_code("diff file1 file2", 1)
        assert result is not None
        assert "differ" in result.lower()



    # ---- test / [: exit 1 = condition false ----

    def test_test_condition_false(self):
        result = _interpret_exit_code("test -f /nonexistent", 1)
        assert result is not None
        assert "false" in result.lower()


    # ---- find: exit 1 = partial success ----


    # ---- curl: various informational codes ----


    # ---- git: exit 1 is context-dependent ----


    # ---- pipeline / chain handling ----


    # ---- full paths ----


    # ---- env var prefix ----


    # ---- unknown commands return None ----


    # ---- edge cases ----


    # ---- wrapper prefixes: the real command's semantics still apply ----

    @pytest.mark.parametrize("cmd,needle", [
        ("sudo grep 'pattern' /etc/shadow", "no matches"),
        ("sudo /usr/bin/rg 'foo' /var/log", "no matches"),
        ("doas diff file1 file2", "differ"),
        ("env FOO=bar rg 'foo' .", "no matches"),
        ("command test -f /nonexistent", "false"),
        ("sudo sudo grep 'pattern' f", "no matches"),
    ])
    def test_wrapper_prefix_keeps_base_command_semantics(self, cmd, needle):
        result = _interpret_exit_code(cmd, 1)
        assert result is not None, f"{cmd!r} lost its exit-code note through a wrapper prefix"
        assert needle in result.lower()

    def test_wrapper_prefix_unknown_base_still_none(self):
        assert _interpret_exit_code("sudo someunknowncmd --flag", 1) is None
        assert _interpret_exit_code("sudo", 1) is None

    def test_only_env_vars(self):
        """Command with only env var assignments, no actual command."""
        assert _interpret_exit_code("FOO=bar", 1) is None
