"""Gemma 4 reasoning-token streaming regressions for issue #43873.

A provider may split either native marker inside a stream delta.  Reasoning
must not become visible merely because the marker did not arrive whole.
"""

import pytest

from agent.think_scrubber import StreamingThinkScrubber


@pytest.mark.parametrize(
    ("opener", "closer"),
    [
        ("<|channel>thought", "<channel|>"),  # liuhao1024's reported form
        ("<|turn|>thinking", "<turn|>"),       # Gemma 4 variant
    ],
)
def test_native_reasoning_markers_split_inside_both_tokens(opener, closer):
    """Complete streamed reasoning remains hidden for partial open and close tags."""
    for open_cut in (1, len(opener) // 2, len(opener) - 1):
        for close_cut in (1, len(closer) // 2, len(closer) - 1):
            scrubber = StreamingThinkScrubber()
            deltas = [
                opener[:open_cut],
                opener[open_cut:] + "\nprivate chain of thought",
                closer[:close_cut],
                closer[close_cut:] + "Visible answer",
            ]
            output = "".join(scrubber.feed(delta) for delta in deltas)
            output += scrubber.flush()
            assert output == "Visible answer", (opener, open_cut, close_cut, output)
