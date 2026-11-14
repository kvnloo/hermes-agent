"""Regression for #58642 / #155258: quoted protected roots may traverse back to root.

The shell expands /etc/../* into root-level children. Hardline classification must
not become an approvable warning when the quoted prefix is dequoted.
"""

import pytest

from tools.approval_detection import detect_hardline_command


@pytest.mark.parametrize("command", [
    'rm -rf "/etc"/../*',
    "nice rm -rf '/usr'/../*",
    'rm -rf "/etc"/../../*',
])
def test_protected_system_directory_parent_glob_is_hardline(command):
    assert detect_hardline_command(command) == (
        True, "recursive delete of system directory",
    ), command


@pytest.mark.parametrize("command", [
    'rm -rf "/etc"/nginx/old',
    "rm -rf /etcetera/",
])
def test_sibling_subtrees_are_not_hardline(command):
    assert detect_hardline_command(command) == (False, None), command
