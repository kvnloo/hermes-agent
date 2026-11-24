"""Decimal repeat counts may have leading zeroes in Python patterns."""
import re

import pytest

import hermes_re


@pytest.mark.parametrize(("pattern", "subject"), [
    (r"a{01}", "a"),
    (r"a{1,02}", "aa"),
    (r"a{,02}", ""),
    (r"a{00,}", "aa"),
    (rb"a{01}", b"a"),
    (r"(?:a{01})$", "a"),
    (r"a\{01}", "a{01}"),
    (r"[a{01}]+", "a{01}"),
])
def test_repeat_spelling_matches_stdlib(pattern, subject):
    expected = re.fullmatch(pattern, subject)
    assert expected is not None
    actual = hermes_re.fullmatch(pattern, subject)
    assert actual is not None
    assert actual.span() == expected.span()


def test_padded_repeat_does_not_match_literal_braces():
    assert hermes_re.fullmatch(r"a{01}", "a{01}") is None
