"""Regression for #156660: mise exec -- ruby renders as Ruby."""

from agent.display import get_cute_tool_message


def test_ruby_terminal_icon():
    # One messaging-surface invariant: mise's separator still launches Ruby.
    for command in ("mise exec -- ruby -v", "echo setup && mise exec -- ruby -v"):
        message = get_cute_tool_message("terminal", {"command": command}, 0.1)
        assert "💎 " in message
        assert "💻" not in message

    ordinary = get_cute_tool_message("terminal", {"command": "echo ruby"}, 0.1)
    assert "💻 " in ordinary
    assert "💎" not in ordinary
