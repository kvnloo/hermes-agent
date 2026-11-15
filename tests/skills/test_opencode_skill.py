"""Version-specific OpenCode CLI guidance (#156159)."""

from pathlib import Path


SKILL = (
    Path(__file__).resolve().parents[2]
    / "optional-skills/autonomous-ai-agents/opencode/SKILL.md"
)


def test_opencode_run_flags_are_version_scoped():
    """V2 instructions must never send readers to V1-only run flags."""
    body = SKILL.read_text(encoding="utf-8")
    common_section = body.split("## Common Flags", 1)[1].split("\n## Procedure", 1)[0]
    common_rows = [line for line in common_section.splitlines() if line.startswith("| `")]
    assert not any(
        row.startswith("| `--variant ") or row.startswith("| `--attach ")
        for row in common_rows
    )

    section = body.partition("### Version-specific `opencode run` flags")[2]
    assert section, "OpenCode V1/V2 run syntax is missing"
    rows = [line for line in section.splitlines() if line.startswith("| V")]
    assert len(rows) == 2
    v1, v2 = rows
    assert v1.startswith("| V1 (1.x) |")
    assert "--variant <level>" in v1 and "--attach <url>" in v1
    assert v2.startswith("| V2 (2.x) |")
    assert "opencode run --model 'provider/model#variant'" in v2
    assert "--server <url>" in v2
    assert "--variant" not in v2 and "--attach" not in v2
