"""A secret-named value in the profile's environment is masked by exact value on model egress.

Regression (P0): a skill's ``required_environment_variables`` prompt saved a sudo password to the
profile ``.env``, which also published it to ``os.environ``. A ``swift build`` error then printed the
child environment as ``'NAME=value'`` pairs. ``redact_terminal_output`` skips the ``KEY=value``
pass for a non-env-dump command, and the exact-value scrub only knew external secret-source values,
so the password reached the provider and ``state.db`` verbatim.
"""

from __future__ import annotations

import pytest

from agent import redact_secret_sources
from agent.redact import redact_terminal_output
from agent.tool_dispatch_helpers import make_tool_result_message
from hermes_cli.config import remove_env_value, save_env_value

FAKE_PASSWORD = "Qv7-not-real-9x"  # fake: no vendor prefix, so no shape pass knows it
PLAIN_PATH = "/srv/app/workspace"


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(redact_secret_sources, "_VALUES_BY_HOME", {})
    for name in ("GROOT_SUDO_PASSWORD", "PROJECT_DIR"):
        monkeypatch.delenv(name, raising=False)
    yield
    for name in ("GROOT_SUDO_PASSWORD", "PROJECT_DIR"):
        remove_env_value(name)


def _swift_build_error(value: str) -> str:
    return (
        "error: failed to run swift-frontend: env -i 'AI_AGENT=hermes-agent' 'CPATH=/usr/local/include' "
        f"'GROOT_SUDO_PASSWORD={value}' 'PROJECT_DIR={PLAIN_PATH}' swift-frontend -frontend -c\n"
        f"note: retry with {value}\n"
    )


def _wire_text(output: str) -> str:
    redacted = redact_terminal_output(output, command="swift build 2>&1 | grep -m3 -i error")
    msg = make_tool_result_message("terminal", redacted, "call_1")
    return msg["content"]


def test_skill_intake_secret_is_masked_in_a_terminal_result_whatever_the_format():
    save_env_value("GROOT_SUDO_PASSWORD", FAKE_PASSWORD)
    save_env_value("PROJECT_DIR", PLAIN_PATH)

    wire = _wire_text(_swift_build_error(FAKE_PASSWORD))

    assert FAKE_PASSWORD not in wire
    assert "GROOT_SUDO_PASSWORD=" in wire  # the name stays, so the reader knows what was there
    assert PLAIN_PATH in wire  # a non-secret variable's value is left alone


def test_a_removed_secret_is_no_longer_masked():
    save_env_value("GROOT_SUDO_PASSWORD", FAKE_PASSWORD)
    assert FAKE_PASSWORD not in _wire_text(f"value: {FAKE_PASSWORD}")

    remove_env_value("GROOT_SUDO_PASSWORD")
    assert FAKE_PASSWORD in _wire_text(f"value: {FAKE_PASSWORD}")
