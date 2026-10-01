"""W1 salvage regression test: literal underscores in identifiers survive Slack Block Kit rendering.

Body path (rich_text lists / quotes / table cells): tests from kvnloo fork #23 (TestEmphasis).
Header path (plain_text header): tests from NousResearch/hermes-agent#96941 (NaMinhyeok).
Contract: an intra-word ``_`` / ``__`` is literal text, never an emphasis delimiter; real
word-boundary ``*x*`` / ``_x_`` / ``__x__`` emphasis still renders.
"""

from plugins.platforms.slack.block_kit import render_blocks


def _iter_text_elements(blocks):
    def _walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                yield node
            for v in node.values():
                yield from _walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from _walk(v)
    yield from _walk(blocks)


def _all_text(blocks) -> str:
    return "".join(el.get("text", "") for el in _iter_text_elements(blocks))


def _italic_texts(blocks) -> list:
    return [
        el["text"]
        for el in _iter_text_elements(blocks)
        if isinstance(el.get("style"), dict) and el["style"].get("italic")
    ]


# ---- body path (fork #23) -------------------------------------------------

class TestBodyEmphasis:
    def test_multiple_snake_case_identifiers_in_bullets_preserve_underscores(self):
        md = (
            "- Set MY_API_KEY in the config\n"
            "- Call fetch_user_data() helper\n"
            "- Inspect build_status_report logs"
        )
        blocks = render_blocks(md)
        text = _all_text(blocks)
        assert "MY_API_KEY" in text
        assert "fetch_user_data()" in text
        assert "build_status_report" in text
        assert _italic_texts(blocks) == []

    def test_snake_case_in_blockquote_preserves_underscores(self):
        blocks = render_blocks("> see foo_bar_baz here")
        assert "foo_bar_baz" in _all_text(blocks)
        assert _italic_texts(blocks) == []

    def test_snake_case_in_table_cell_preserves_underscores(self):
        md = (
            "| Field | Value |\n"
            "|-------|-------|\n"
            "| key | MY_API_KEY |"
        )
        blocks = render_blocks(md)
        assert blocks[0]["type"] == "table"
        assert "MY_API_KEY" in _all_text(blocks)
        assert _italic_texts(blocks) == []

    def test_star_emphasis_in_bullet_italicizes(self):
        blocks = render_blocks("- a *real* bug")
        assert _italic_texts(blocks) == ["real"]
        assert _all_text(blocks) == "a real bug"

    def test_underscore_emphasis_at_word_boundary_italicizes(self):
        blocks = render_blocks("- a _real_ word")
        assert _italic_texts(blocks) == ["real"]
        assert _all_text(blocks) == "a real word"

    def test_underscore_emphasis_multiword_phrase_italicizes(self):
        blocks = render_blocks("- the _quick brown fox_ jumps")
        assert _italic_texts(blocks) == ["quick brown fox"]
        assert _all_text(blocks) == "the quick brown fox jumps"

    def test_backticked_snake_case_preserved_as_code(self):
        blocks = render_blocks("- Call `fetch_user_data()` helper")
        code = [
            el["text"]
            for el in _iter_text_elements(blocks)
            if isinstance(el.get("style"), dict) and el["style"].get("code")
        ]
        assert code == ["fetch_user_data()"]
        assert _italic_texts(blocks) == []

    def test_cross_pair_star_underscore_is_not_emphasis(self):
        blocks = render_blocks("- 2*3=6 and my_var_b")
        assert "2*3=6 and my_var_b" in _all_text(blocks)
        assert _italic_texts(blocks) == []


# ---- body path, double underscore (same defect via _BOLD_RE; W1 addition) --

class TestBodyDoubleUnderscore:
    def test_double_underscore_identifier_in_bullet_preserved(self):
        blocks = render_blocks("- region SERVICE__US__EAST is up")
        assert "SERVICE__US__EAST" in _all_text(blocks)


# ---- header path (#96941) -------------------------------------------------

class TestHeader:
    def test_header_preserves_literal_markup_characters(self):
        blocks = render_blocks("# **SERVICE_US** `SA-03` _current status_")
        assert blocks is not None
        assert blocks[0]["text"]["text"] == "SERVICE_US SA-03 current status"

    def test_header_does_not_treat_identifier_underscores_as_emphasis(self):
        blocks = render_blocks("# SERVICE_US_EAST")
        assert blocks is not None
        assert blocks[0]["text"]["text"] == "SERVICE_US_EAST"

    def test_header_does_not_treat_double_identifier_underscores_as_strong(self):
        blocks = render_blocks("# SERVICE__US__EAST")
        assert blocks is not None
        assert blocks[0]["text"]["text"] == "SERVICE__US__EAST"

    def test_header_requires_matching_strong_delimiters(self):
        blocks = render_blocks("# **SERVICE_US__")
        assert blocks is not None
        assert blocks[0]["text"]["text"] == "**SERVICE_US__"

    def test_header_strips_valid_underscore_strong_markup(self):
        blocks = render_blocks("# __current status__")
        assert blocks is not None
        assert blocks[0]["text"]["text"] == "current status"
