"""Independent real-import rendering contracts for upstream PR 138412.

Evidence-only tests: authored fix and original regression tests remain credited
to rodricksz4h5. Values are resolved from temporary config and skill files.
"""

import contextlib
import re
from pathlib import Path

import pytest
import hermes_yaml as yaml


CASES = [
    pytest.param({"value": False}, {"default": True}, "False", id="configured-false"),
    pytest.param({"value": 0}, {"default": 3}, "0", id="configured-zero"),
    pytest.param({"value": 0.0}, {}, "0.0", id="configured-float-zero"),
    pytest.param({}, {}, "(not set)", id="missing"),
    pytest.param({"value": ""}, {}, "(not set)", id="empty-string"),
    pytest.param({"value": None}, {}, "(not set)", id="null-config"),
    pytest.param({}, {"default": None}, "(not set)", id="null-default"),
    pytest.param({"value": True}, {}, "True", id="configured-true"),
    pytest.param({"value": 3}, {}, "3", id="positive-number"),
    pytest.param({"value": "0"}, {}, "0", id="string-zero"),
    pytest.param({"value": []}, {}, "[]", id="empty-list"),
    pytest.param({"value": {}}, {}, "{}", id="empty-mapping"),
    pytest.param({}, {"default": False}, "False", id="false-default"),
    pytest.param({}, {"default": 0}, "0", id="zero-default"),
]


def _write_profile(home, configured, declaration):
    skill_dir = home / "skills" / "render-contract"
    skill_dir.mkdir(parents=True)
    frontmatter = {
        "name": "render-contract",
        "description": "Read a configured setting",
        "metadata": {"hermes": {"config": [
            {"key": "review.value", "description": "Review value", **declaration}
        ]}},
    }
    (skill_dir / "SKILL.md").write_text(
        "---\n" + yaml.safe_dump(frontmatter) + "---\nRead the setting.\n", encoding="utf-8"
    )
    (home / "config.yaml").write_text(
        yaml.safe_dump({"skills": {"config": {"review": configured}}}), encoding="utf-8"
    )


@contextlib.contextmanager
def _active_profile(home):
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override

    token = set_hermes_home_override(home)
    try:
        yield
    finally:
        reset_hermes_home_override(token)


def _render_value(surface, capsys):
    if surface == "invocation":
        from agent.skill_commands import build_skill_invocation_message

        message = build_skill_invocation_message("/render-contract", "Read the value")
        assert message is not None
        values = [line.removeprefix("  review.value = ") for line in message.splitlines()
                  if line.startswith("  review.value = ")]
    else:
        from hermes_cli.config import _show_skill_settings

        _show_skill_settings()
        output = re.sub(r"\x1b\[[0-9;]*m", "", capsys.readouterr().out)
        values = [line.split("review.value", 1)[1].rsplit("[render-contract]", 1)[0].strip()
                  for line in output.splitlines() if line.strip().startswith("review.value ")]
    assert len(values) == 1
    return values[0]


@pytest.fixture
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    return tmp_path / ".hermes"


@pytest.mark.parametrize("surface", ["invocation", "settings"])
@pytest.mark.parametrize("configured,declaration,expected", CASES)
def test_resolved_values_render_verbatim(isolated_root, capsys, surface, configured, declaration, expected):
    _write_profile(isolated_root, configured, declaration)
    with _active_profile(isolated_root):
        assert _render_value(surface, capsys) == expected


@pytest.mark.parametrize("surface", ["invocation", "settings"])
def test_profile_switch_keeps_each_config_value(isolated_root, capsys, surface):
    first = isolated_root / "profiles" / "first"
    second = isolated_root / "profiles" / "second"
    _write_profile(first, {"value": "first-profile"}, {})
    _write_profile(second, {"value": False}, {"default": True})
    for home, expected in [(first, "first-profile"), (second, "False"), (first, "first-profile")]:
        with _active_profile(home):
            assert _render_value(surface, capsys) == expected
