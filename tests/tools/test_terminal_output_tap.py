"""The display tap cannot expose shell bookkeeping or damage the tool's capture."""
import pytest

from tools.terminal_output import TerminalOutputTap


@pytest.mark.parametrize("split", range(len("\n__HERMES_CWD_test__") + 1))
def test_cwd_trailer_prefix_can_cross_any_chunk_boundary(split):
    chunks = []
    marker = "__HERMES_CWD_test__"
    tap = TerminalOutputTap(chunks.append, marker)
    prefix = "\n" + marker
    tap.feed("\x1b[31m紅\x1b[0m\r100% ✓\n" + prefix[:split])
    tap.feed(prefix[split:] + "/private/path" + marker + "\n")
    tap.finish()
    assert "".join(chunks) == "\x1b[31m紅\x1b[0m\r100% ✓\n"


def test_incomplete_nonmarker_prefix_is_flushed_on_cancel():
    chunks = []
    tap = TerminalOutputTap(chunks.append, "__HERMES_CWD_test__")
    tap.feed("partial\n__H")
    tap.finish()
    assert "".join(chunks) == "partial\n__H"


def test_failing_ui_sink_cannot_fail_process_capture():
    def broken(_):
        raise BrokenPipeError("renderer disconnected")

    tap = TerminalOutputTap(broken, "__HERMES_CWD_test__")
    tap.feed("output\n")
    tap.finish()
