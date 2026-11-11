"""The terminal tool refuses whole-tree walks (find/du/grep -r/rg) over a broad root.

Agent shell commands like ``find /home/kvn /workspace /mnt/zer0models -name '*.toml'``
read GiBs per call; their child read_bytes roll into the gateway when it reaps them,
which is how the gateway showed up as a 5.7 GiB/min reader on the data disk.
"""

import pytest

from tools.search_root_guard import broad_walk_error


@pytest.fixture(autouse=True)
def _roots(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", "/home/u")
    monkeypatch.setenv("HERMES_SEARCH_BROAD_ROOTS", "/mnt/big/ws:/workspace/hh")
    monkeypatch.setattr("tools.search_root_guard._config_roots", list)


@pytest.mark.parametrize("command", [
    "find /home/u /workspace /mnt/big -name \"*.toml\" -path \"*memory*\" 2>/dev/null | head -20",
    "cd /tmp && find /mnt/big -maxdepth 6 -name x",
    "timeout 60 find ~ -name '*.py'",
    "rtk find / -name foo",
    "du -sh /workspace/hh",
    "grep -n -H -rn -e 'retained by owner' -- /home/u/.x /workspace/hh",
    "rg -l needle /mnt/big",
    "sudo du -sx /",
    "ls; find $HOME -type f",
])
def test_refuses_broad_walks(command):
    err = broad_walk_error(command)
    assert err and "Refusing" in err


@pytest.mark.parametrize("command", [
    "find /mnt/big/ws/products/app -name '*.toml'",
    "find /mnt/big -maxdepth 2 -type d",
    "rg -l needle /mnt/big/ws/oss/repo",
    "rg --max-depth 2 -l needle /home/u",
    "du -sh /mnt/big/ws/data/x",
    "grep -n foo /home/u/file.txt",
    "ls -la /mnt/big /home/u",
    "find . -name '*.py'",
    "echo 'find / -name x'",
    "git grep -r foo",
    "cat 'unbalanced",
])
def test_allows_bounded_commands(command):
    assert broad_walk_error(command) is None
