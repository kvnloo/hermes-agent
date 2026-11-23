"""Decision-window gate for proactive cron jobs (``cron.decision_window``).

A job may declare when it should speak (``window_class``) and how late is too late
(``stale_after_s``). ``gate`` answers fire / hold with a one-line reason; a pluggable
``WindowProvider`` reports the window open now. Jobs that declare neither field behave exactly
as before. Design: NousResearch/hermes-agent#158538.

Every fixture here is synthetic.
"""
from datetime import UTC, datetime, timedelta

import pytest

from cron.decision_window import (
    ALWAYS_ANYTIME, WindowClass, gate, is_stale, normalize_stale_after_s, normalize_window_class,
)

NOW = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)


def _job(**fields):
    due = (NOW - timedelta(seconds=30)).isoformat()
    return {"id": "j1", "name": "synthetic", "next_run_at": due, **fields}


class Fixed:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def current(self, now):
        self.calls.append(now)
        return self.value


def test_a_job_without_window_fields_fires_and_never_asks_the_provider():
    provider = Fixed(WindowClass.TROUGH)
    fire, reason = gate(_job(), NOW, provider)
    assert fire is True and reason
    assert provider.calls == []


def test_default_provider_reports_anytime_so_every_class_fires():
    assert ALWAYS_ANYTIME.current(NOW) is WindowClass.ANYTIME
    for cls in WindowClass:
        fire, _ = gate(_job(window_class=cls.value), NOW, ALWAYS_ANYTIME)
        assert fire is True, cls


def test_matching_window_fires_and_names_it():
    fire, reason = gate(_job(window_class="peak"), NOW, Fixed(WindowClass.PEAK))
    assert fire is True and "peak" in reason


def test_other_window_holds_with_a_reason_naming_both_classes():
    fire, reason = gate(_job(window_class="peak"), NOW, Fixed(WindowClass.TROUGH))
    assert fire is False
    assert "trough" in reason and "peak" in reason


@pytest.mark.parametrize("unknown", [None, "lunch", 3])
def test_unknown_window_holds(unknown):
    fire, reason = gate(_job(window_class="wind_down"), NOW, Fixed(unknown))
    assert fire is False and "unknown" in reason


def test_provider_may_answer_with_the_plain_string():
    fire, _ = gate(_job(window_class="wind_down"), NOW, Fixed("wind_down"))
    assert fire is True


def test_anytime_job_fires_even_when_the_provider_knows_nothing():
    provider = Fixed(None)
    fire, _ = gate(_job(window_class="anytime"), NOW, provider)
    assert fire is True


def test_provider_receives_the_tick_instant():
    provider = Fixed(WindowClass.PEAK)
    gate(_job(window_class="peak"), NOW, provider)
    assert provider.calls == [NOW]


def test_stale_occurrence_does_not_fire_even_in_its_window():
    job = _job(window_class="peak", stale_after_s=60, next_run_at=(NOW - timedelta(minutes=5)).isoformat())
    assert is_stale(job, NOW) is True
    fire, reason = gate(job, NOW, Fixed(WindowClass.PEAK))
    assert fire is False and "stale" in reason


def test_fresh_occurrence_is_not_stale():
    job = _job(stale_after_s=600)
    assert is_stale(job, NOW) is False
    assert gate(job, NOW, ALWAYS_ANYTIME)[0] is True


def test_stale_after_alone_drops_a_late_catch_up_run():
    job = _job(stale_after_s=60, next_run_at=(NOW - timedelta(hours=1)).isoformat())
    assert gate(job, NOW, ALWAYS_ANYTIME)[0] is False


def test_manual_run_is_never_gated():
    due = (NOW - timedelta(hours=2)).isoformat()
    job = _job(window_class="peak", stale_after_s=60, next_run_at=due, manual_run_at=due)
    provider = Fixed(WindowClass.TROUGH)
    assert gate(job, NOW, provider)[0] is True
    assert provider.calls == []


@pytest.mark.parametrize("raw,expected", [
    (None, None), ("", None), ("peak", "peak"), (" Wind_Down ", "wind_down"),
    (WindowClass.TROUGH, "trough"),
])
def test_normalize_window_class(raw, expected):
    assert normalize_window_class(raw) == expected


@pytest.mark.parametrize("raw", ["noon", 1, True])
def test_normalize_window_class_rejects_unknown_values(raw):
    with pytest.raises(ValueError, match="window_class"):
        normalize_window_class(raw)


@pytest.mark.parametrize("raw,expected", [(None, None), ("", None), (90, 90.0), ("3600", 3600.0), (1.5, 1.5)])
def test_normalize_stale_after_s(raw, expected):
    assert normalize_stale_after_s(raw) == expected


@pytest.mark.parametrize("raw", [0, -5, True, "soon", float("nan"), float("inf")])
def test_normalize_stale_after_s_rejects_non_positive_or_non_numbers(raw):
    with pytest.raises(ValueError, match="stale_after_s"):
        normalize_stale_after_s(raw)
