"""Regression for #156346: the CLI banner points to the skill discovery command."""

from hermes_cli.banner import _banner_skill_lines


def test_empty_skills_hint_preserves_populated_and_disabled_states():
    def render(skills, *, enabled=True):
        return _banner_skill_lines(skills, enabled, dim="dim", text="text")

    empty = render({})
    assert len(empty) == 1
    assert "No skills installed yet" in empty[0]
    assert "hermes skills browse" in empty[0]

    populated = render({"general": ["note-taking"]})
    assert populated and all("hermes skills browse" not in line for line in populated)

    disabled = render({}, enabled=False)
    assert len(disabled) == 1
    assert "Skills toolset disabled" in disabled[0]
    assert "hermes skills browse" not in disabled[0]
