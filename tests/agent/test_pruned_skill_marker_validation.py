"""A reload marker for a skill that does not resolve must not survive compaction (#131487).

The summarizer is told to copy every ``[SKILL_PRUNED: ...]`` marker verbatim, and on re-compression its input
includes the previous summary, so a garbled or invented name would otherwise be carried forward forever.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agent import skill_utils
from tools import skills_tool
from agent.context_compressor import SUMMARY_PREFIX, ContextCompressor, _skill_pruned_marker
from agent.conversation_compression import _pruned_skill_reload_notice


@pytest.fixture
def skills_dir(tmp_path):
    root, external = tmp_path / "skills", tmp_path / "external"
    for base, rel in ((root, "pdf"), (root, "docs/axolotl"), (root, "off-skill"), (external, "ext-skill")):
        d = base / rel
        d.mkdir(parents=True)
        name = rel.rsplit("/", 1)[-1]
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {name} skill.\n---\n\n# {name}\n")
    with (
        patch.object(skills_tool, "SKILLS_DIR", root),
        patch.object(skill_utils, "get_external_skills_dirs", lambda: [external]),
        patch.object(skills_tool, "_is_skill_disabled", lambda *names, **_: "off-skill" in names),
    ):
        yield root


@pytest.mark.parametrize("name", ["pdf", "docs/axolotl", "axolotl", "ext-skill", "pdf-generator", "../outside"])
def test_skill_name_resolves_iff_skill_view_loads(skills_dir, name):
    assert skills_tool.skill_name_resolves(name) is json.loads(skills_tool.skill_view(name))["success"]


@pytest.mark.parametrize("name", ["off-skill", "my-plugin:helper"])
def test_disabled_and_plugin_names_are_kept(skills_dir, name):
    """skill_view refuses a disabled skill by name and serves ``ns:skill`` from the plugin registry, so a reload
    attempt either loads or tells the model why; neither is a stale name."""
    assert skills_tool.skill_name_resolves(name)


def test_reload_notice_keeps_every_loadable_skill(skills_dir):
    """Category paths and plugin skills are loadable, so validation must not cost them their reload."""
    names = ["pdf", "docs/axolotl", "my-plugin:helper"]
    notice = _pruned_skill_reload_notice([{"role": "user", "content": "\n".join(map(_skill_pruned_marker, names))}])
    assert all(f"skill_view(name='{name}')" in notice for name in names)


def _compress(prior_summary_markers, summarizer_text):
    with patch("agent.context_compressor.get_model_context_length", return_value=100000):
        c = ContextCompressor(model="test/model", quiet_mode=True, protect_first_n=1, protect_last_n=2)
    prior = SUMMARY_PREFIX + "\n\n## Goal\nOld work.\n\n## Pruned Skills\n" + "\n".join(prior_summary_markers)
    msgs = [{"role": "system", "content": "System prompt"}, {"role": "user", "content": prior}] + [
        {"role": "assistant" if i % 2 == 0 else "user", "content": f"turn {i} " + "q" * 300} for i in range(8)
    ]
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = summarizer_text
    with (
        patch.object(c, "_find_tail_cut_by_tokens", return_value=8),
        patch("agent.context_compressor.call_llm", return_value=response),
    ):
        result = c.compress(msgs, force=True)
    summary = next(m["content"] for m in result if ContextCompressor.classify_summary_content(m.get("content")))
    return c, result, summary


@pytest.mark.parametrize("summarizer_echoes", [True, False], ids=["summarizer-echoes", "summarizer-drops"])
def test_unresolvable_marker_does_not_cross_the_boundary(skills_dir, summarizer_echoes):
    markers = [_skill_pruned_marker("pdf"), _skill_pruned_marker("pdf-generator")]
    text = "## Goal\nNext task.\n\n## Pruned Skills\n" + ("\n".join(markers) if summarizer_echoes else "")
    c, result, summary = _compress(markers, text)

    assert _skill_pruned_marker("pdf") in summary
    assert "pdf-generator" not in summary
    assert "pdf-generator" not in c._previous_summary
    notice = _pruned_skill_reload_notice(result)
    assert "skill_view(name='pdf')" in notice and "pdf-generator" not in notice


def test_lookup_failure_keeps_every_marker(skills_dir):
    markers = [_skill_pruned_marker("pdf"), _skill_pruned_marker("pdf-generator")]
    with patch.object(skills_tool, "skill_name_resolves", side_effect=RuntimeError("catalog unavailable")):
        _c, _result, summary = _compress(markers, "## Goal\nNext task.\n\n## Pruned Skills\n" + "\n".join(markers))
    assert all(marker in summary for marker in markers)
