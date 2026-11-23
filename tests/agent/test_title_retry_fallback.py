import json
from types import SimpleNamespace

import pytest

from agent import title_generator


@pytest.mark.parametrize(
    ("replies", "expected"),
    [
        pytest.param(
            ["Unicode grapheme cluster debugging", "Code changes"],
            "Unicode grapheme cluster debugging",
            id="shorter-canned-echo",
        ),
        pytest.param(
            ["Unicode grapheme cluster debugging", "這不是標題這只是我在回答你的問題因為我不懂"],
            "Unicode grapheme cluster debugging",
            id="shorter-answer-shaped",
        ),
        pytest.param(["🐈 Café\nparser"], "🐈 Café parser", id="short-emoji-newline"),
    ],
)
def test_title_retry_keeps_usable_first_title(monkeypatch, replies, expected):
    reply_iter = iter(replies)
    calls = []

    def model(**kwargs):
        calls.append(kwargs)
        content = json.dumps({"title": next(reply_iter)})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    monkeypatch.setattr(title_generator, "call_llm", model)
    assert title_generator.generate_title("Debug how the Unicode parser groups graphemes") == expected
    assert len(calls) == len(replies)
