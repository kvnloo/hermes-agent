"""Contract for discovery and content of the optional OpenUI board skill."""

import re
from pathlib import Path

from tools.skills_hub_official import OptionalSkillSource


REPO = Path(__file__).resolve().parents[2]
IDENTIFIER = "official/productivity/openui-boards"
FENCE_RE = re.compile(r"^```openui-v2\n([\s\S]*?)\n```$", re.MULTILINE)


def _source():
    source = OptionalSkillSource()
    source._optional_dir = REPO / "optional-skills"
    return source


def test_openui_boards_can_be_discovered_and_fetched_as_official_optional_skill():
    source = _source()
    matches = [m for m in source.list_local() if m.identifier == IDENTIFIER]
    assert len(matches) == 1
    meta = matches[0]
    assert meta.source == "official"
    assert meta.path == "optional-skills/productivity/openui-boards"
    assert "openui" in meta.tags

    bundle = source.fetch(IDENTIFIER)
    assert bundle is not None
    assert bundle.identifier == IDENTIFIER
    assert bundle.name == "openui-boards"
    assert bundle.trust_level == "builtin"
    assert bundle.files["SKILL.md"].decode("utf-8").startswith("---\nname: openui-boards\n")


def test_source_demo_fences_are_complete_read_only_and_have_markdown_fallbacks():
    bundle = _source().fetch(IDENTIFIER)
    assert bundle is not None
    content = bundle.files["SKILL.md"].decode("utf-8")
    programs = FENCE_RE.findall(content)
    assert len(programs) == 2
    for program in programs:
        lines = program.splitlines()
        assert lines[0].startswith("root = Board(")
        assert len(lines) >= 2
        assert not any(token in program for token in ("Query(", "Mutation(", "State(", "<script"))
    assert content.count("Markdown fallback:") == len(programs)
