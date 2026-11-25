from agent.context_compressor_lean import (
    _LEAN_ANCHOR_HEADING,
    _parse_anchor_index,
    rebuild_lean_sections,
    strip_lean_sections,
)


def test_literal_count_suffix_survives_three_compactions():
    """An error's literal (xN) suffix is not an occurrence count."""
    summary = "## Progress\nCompacted output."
    error = "ValueError: unsupported shape (x2)"
    previous = ""
    for i in range(3):
        region = [{"role": "assistant", "content": error}] if i != 1 else [
            {"role": "user", "content": "Continue the investigation."}
        ]
        previous = rebuild_lean_sections(previous or summary, region, previous_summary=previous, session_id="s")

    _, sections = strip_lean_sections(previous, (_LEAN_ANCHOR_HEADING,))
    errors = _parse_anchor_index(sections[_LEAN_ANCHOR_HEADING])["errors"]
    assert errors == {error: 2}
