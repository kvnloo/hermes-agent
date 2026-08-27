from hermes_cli.curses_ui import (
    _SearchState,
    _filter_indices,
    _handle_active_search_key,
    _move_filtered_cursor,
    _reconcile_cursor,
)


class _FakeCurses:
    KEY_BACKSPACE = 263
    KEY_DOWN = 258
    KEY_ENTER = 343


def test_provider_choice_enables_default_type_to_search(monkeypatch):
    from hermes_cli import main as main_mod

    captured = {}

    def fake_prompt(question, choices, default, **kwargs):
        captured.update(question=question, choices=choices, default=default, **kwargs)
        return 1

    monkeypatch.setattr("hermes_cli.setup._curses_prompt_choice", fake_prompt)

    assert main_mod._prompt_provider_choice(["Anthropic", "OpenAI"], default=1) == 1
    assert captured["searchable"] is True
    assert captured["search_on_type"] is True




def test_reconcile_cursor_moves_to_first_visible_match():
    assert _reconcile_cursor([2, 4], 0) == (2, 0)
    assert _reconcile_cursor([2, 4], 4) == (4, 1)




def test_active_search_consumes_query_editing_and_confirm_keys():
    search = _SearchState(active=True, query="op")

    assert _handle_active_search_key(_FakeCurses, ord("u"), search) == (True, False, True)
    assert search.query == "opu"

    assert _handle_active_search_key(_FakeCurses, _FakeCurses.KEY_ENTER, search) == (
        True,
        True,
        False,
    )
