"""Clarify fragment sizing consumes the active app's resize dimensions (#126970)."""

import os
import shutil

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.data_structures import Size
from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput

from hermes_cli.cli_tui_mixin import CLITuiMixin


class ResizingOutput(DummyOutput):
    columns = 120

    def get_size(self):
        return Size(rows=50, columns=self.columns)


def test_clarify_reflows_with_active_output_even_when_shell_size_is_stale(monkeypatch):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback=(80, 24): os.terminal_size((100, 50)))
    host = CLITuiMixin()
    host._clarify_freetext = False
    host._clarify_state = {
        "questions": [{"qid": "first", "question": " ".join(["deployment"] * 60)}],
        "answers": {}, "answer_meta": {}, "active": 0,
        "choices": ["red", "blue"], "selected": 0, "multi_select": False,
    }
    output = ResizingOutput()
    app = Application(input=DummyInput(), output=output)
    widths = []
    with set_app(app):
        for columns in (60, 120, 200):
            output.columns = columns
            fragments = host._get_clarify_display_fragments()
            lines = "".join(text for _, text in fragments).splitlines()
            width = max(len(line) for line in lines if line.startswith("│"))
            assert width <= columns
            widths.append(width)
    assert widths[0] < widths[1] < widths[2]
