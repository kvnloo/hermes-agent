"""Overlay panel fragments and current terminal width for the interactive CLI."""

import logging
import shutil

logger = logging.getLogger(__name__)


def terminal_columns() -> int:
    """Live terminal width: prompt_toolkit's size follows resizes; shutil covers
    callers outside a running app (tests, early startup)."""
    try:
        from prompt_toolkit.application import get_app
        from prompt_toolkit.application.dummy import DummyApplication

        app = get_app()
        if not isinstance(app, DummyApplication):  # DummyOutput always reports 80x24
            return app.output.get_size().columns
    except Exception:
        logger.exception("Unable to read the active terminal width; using shell dimensions")
    return shutil.get_terminal_size((100, 24)).columns


class Panel:
    """Fragment accumulator for one bordered overlay panel (``(style, text)`` tuples)."""

    def __init__(self, border: str, box_width: int, title: str = "", title_style: str = ""):
        from cli import _append_blank_panel_line, _append_panel_line
        self.lines, self.border, self.width = [], border, box_width
        self._row, self._blank = _append_panel_line, _append_blank_panel_line
        if title:
            # Title inlined into the top rule: ``╭─ Title ───╮``.
            self.lines.append((border, "╭─ "))
            self.lines.append((title_style, title))
            self.lines.append((border, " " + ("─" * max(0, box_width - len(title) - 3)) + "╮\n"))
        else:
            self.lines.append((border, "╭" + ("─" * box_width) + "╮\n"))

    def row(self, style: str, text: str) -> None:
        self._row(self.lines, self.border, style, text, self.width)

    def blank(self) -> None:
        self._blank(self.lines, self.border, self.width)

    def close(self) -> list:
        self.lines.append((self.border, "╰" + ("─" * self.width) + "╯\n"))
        return self.lines
