"""Fallback paste collapse must not write undecodable terminal bytes as lone surrogates."""

from prompt_toolkit.buffer import Buffer

from hermes_cli.cli_tui_mixin import CLITuiMixin


def test_fallback_paste_with_surrogate_is_utf8_safe(tmp_path, monkeypatch):
    import cli

    monkeypatch.setattr(cli, "_hermes_home", tmp_path)
    shell = CLITuiMixin()
    shell.config = {}  # Real defaults: collapse at five newlines or 2000 characters.
    shell._tui_paste_counter = 0
    shell._tui_prev_text_len = 0
    shell._tui_prev_newline_count = 0
    shell._tui_paste_just_collapsed = False
    shell._skip_paste_collapse = False

    # A terminal without bracketed paste delivers this as a single buffer update.
    buf = Buffer()
    buf.on_text_changed += shell._tui_on_text_changed
    pasted = "one\udcff\ntwo\nthree\nfour\nfive\nsix"
    buf.insert_text(pasted)

    files = list((tmp_path / "pastes").glob("paste_1_*.txt"))
    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8") == pasted.replace("\udcff", "\ufffd")
    assert buf.text.startswith("[Pasted text #1: 6 lines")
