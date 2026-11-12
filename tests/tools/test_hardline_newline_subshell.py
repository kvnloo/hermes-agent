"""A newline before `(` does not turn an earlier shutdown verb into a definition."""

import pytest

from tools.approval import detect_hardline_command


@pytest.mark.parametrize("verb", ["shutdown", "reboot", "halt", "poweroff"])
@pytest.mark.parametrize("separator", ["\n", " \n\t"])
def test_hardline_shutdown_before_newline_subshell(verb, separator):
    # The parenthesized command is on a later line: it is a subshell, not `verb ()`.
    command = f"{verb}{separator}( printf ok )"
    assert detect_hardline_command(command) == (True, "system shutdown/reboot")
