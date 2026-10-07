#!/bin/sh
# The project the demo takes work in: a tiny router with one failing test.
#
#   project.sh [DIR]     (re)create it at DIR (default /tmp/courier); DIR is replaced
set -eu
dir=${1:-/tmp/courier}
rm -rf "$dir"
mkdir -p "$dir/courier" "$dir/tests"
cd "$dir"

cat > README.md << 'EOF'
# courier

A tiny message router. It reads messages from an inbox, picks a channel for
each one, and counts what went where.

    python -m courier inbox.json

Run the tests with `pytest`.
EOF
cat > pyproject.toml << 'EOF'
[project]
name = "courier"
version = "0.3.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
EOF
echo '"""courier: route messages to channels."""' > courier/__init__.py
cat > courier/router.py << 'EOF'
"""Pick a channel for each message and count what was delivered."""

ROUTES = {"alert": "pager", "report": "email", "chat": "telegram"}


def route(message: dict) -> str:
    """The channel a message goes to."""
    return ROUTES[message["kind"]]


def deliver(messages: list[dict]) -> dict[str, int]:
    """Count how many messages went to each channel."""
    counts: dict[str, int] = {}
    for message in messages:
        channel = route(message)
        counts[channel] = counts.get(channel, 0) + 1
    return counts
EOF
cat > courier/__main__.py << 'EOF'
import json
import sys

from courier.router import deliver

if __name__ == "__main__":
    with open(sys.argv[1]) as inbox:
        for channel, count in sorted(deliver(json.load(inbox)).items()):
            print(f"{channel:10} {count}")
EOF
cat > inbox.json << 'EOF'
[
  {"kind": "alert", "text": "disk at 91%"},
  {"kind": "report", "text": "weekly numbers"},
  {"kind": "chat", "text": "lunch?"},
  {"kind": "alert", "text": "build failed"}
]
EOF
cat > tests/test_router.py << 'EOF'
from courier.router import deliver, route


def test_known_kinds():
    assert route({"kind": "alert"}) == "pager"
    assert route({"kind": "report"}) == "email"


def test_counts_per_channel():
    inbox = [{"kind": "alert"}, {"kind": "alert"}, {"kind": "chat"}]
    assert deliver(inbox) == {"pager": 2, "telegram": 1}


def test_unknown_kind_falls_back_to_email():
    assert route({"kind": "invoice"}) == "email"
EOF
printf '__pycache__/\n.pytest_cache/\n' > .gitignore

git="git -c user.name=courier -c user.email=courier@example.invalid -c commit.gpgsign=false"
$git init -q -b main .
$git add README.md pyproject.toml courier inbox.json .gitignore
$git commit -q -m "Route messages to channels"
$git add tests
$git commit -q -m "Test the router, with a fallback for unknown kinds"
echo "project: $dir (one failing test)"
