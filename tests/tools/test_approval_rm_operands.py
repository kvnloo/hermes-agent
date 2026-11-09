"""Regression for relative-path rm approval bypass (NousResearch/hermes-agent#151542)."""

import pytest

from tools.approval_detection import _approval_key_aliases, detect_dangerous_command


@pytest.mark.parametrize("command", [
    "cd /srv/app/checkout-api && rm logs/archive/*.log.gz",
    "rm -f logs/archive/*",
    "rm ../../etc/passwd",
    "rm '../secret'",
    'rm "$DIR"/*.log',
    "rm logs/archive/file.log",
    "rm *.log.gz",
    "rm a.txt b.txt",
    'rm "a.txt" "b.txt"',
    'rm -- "a b.txt" "c.txt"',
    "F=1 rm *.log",
    "sudo -u root rm *.log",
    "nice -n 10 rm *.log",
    "builtin rm a b",
])
def test_rm_relative_path_or_glob_requires_approval(command):
    assert detect_dangerous_command(command)[0] is True, command


@pytest.mark.parametrize("command", [
    "rm readme.txt",
    "rm a.txt -f",
    "rm a.txt --verbose",
    "rm a.txt 2>/dev/null",
    "rm notes.txt # keep b.txt around",
    "rm -- -weird.txt",
    "rm '{lock}'",
    'rm "*.log"',
    'echo "rm a.txt b.txt"',
    "grep -r 'rm *.log' .",
    "rm a.txt && echo another file",
])
def test_rm_prose_flags_and_redirects_stay_quiet(command):
    assert detect_dangerous_command(command) == (False, None, None), command


def test_rm_existing_keys_are_unchanged():
    assert detect_dangerous_command("rm /srv/app/x/*.log.gz")[1] == "delete in root path"
    assert detect_dangerous_command("rm -r dir")[1] == "recursive delete"


def test_rm_new_keys_have_disjoint_approval_aliases():
    commands = ("rm '../secret'", "rm *.log", "rm a b", "rm logs/file.log")
    keys = [detect_dangerous_command(command)[1] for command in commands]
    assert len(set(keys)) == len(keys)
    for i, key in enumerate(keys):
        for other in keys[i + 1:]:
            assert _approval_key_aliases(key).isdisjoint(_approval_key_aliases(other))
