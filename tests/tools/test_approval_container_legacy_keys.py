"""Regression for #130511: saved container approval keys survive a regex grammar update."""

import pytest

from tools import approval


# This is the legacy key fragment serialized by versions before #155408. Keep these
# historical bytes independent of the current detector's flag grammar.
_OLD_FLAGS = r'(?:-\S++(?:\s(?!-\S)\S++)?\s++)*'


@pytest.mark.parametrize(("command", "saved_key"), [
    ("docker -H ssh://host ps",
     r"docker\s+" + _OLD_FLAGS + r"(?:-h|--host)[=\s]+\S+"),
    ("docker --context staging ps",
     r"docker\s+" + _OLD_FLAGS + r"(?:-c|--context)[=\s]+\S+"),
    ("podman --url tcp://host ps",
     r"podman\s+" + _OLD_FLAGS + r"(?:--url|--connection|--identity)[=\s]+\S+"),
    ("podman --remote ps",
     r"podman\s+" + _OLD_FLAGS + r"(?:-r"),
    ("docker compose down",
     r"docker(?:-compose|\s+compose)\s+" + _OLD_FLAGS + r"(restart|stop|kill|down)"),
    ("docker stop web",
     r"docker\s+" + _OLD_FLAGS + r"(restart|stop|kill)"),
])
def test_saved_container_approval_keys_survive_flag_spacing_upgrade(command, saved_key):
    # The detector now uses canonical descriptions; historical config.yaml entries
    # with a pre-change regex key must still authorize the same command after update.
    dangerous, key, description = approval.detect_dangerous_command(command)
    assert dangerous and key == description, command
    previous = set(approval._permanent_set())
    try:
        approval.load_permanent({saved_key})
        assert approval.is_approved("legacy-container", key), command
    finally:
        approval.load_permanent(previous)
