"""Tests for historical candlestick request windows."""

from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from market_reliability.data.time_windows import make_time_windows


def test_short_period_uses_one_window():
    start = datetime(2026, 11, 15, tzinfo=UTC)
    end = start + timedelta(hours=2)

    windows = make_time_windows(start, end)

    assert len(windows) == 1
    assert windows[0] == (
        int(start.timestamp()),
        int(end.timestamp()),
    )


def test_three_days_creates_three_windows():
    start = datetime(2026, 11, 15, tzinfo=UTC)
    end = start + timedelta(days=3)

    windows = make_time_windows(start, end)

    assert len(windows) == 3
    assert windows[0][0] == int(start.timestamp())
    assert windows[-1][1] == int(end.timestamp())


def test_windows_are_contiguous():
    start = datetime(2026, 11, 15, tzinfo=UTC)
    end = start + timedelta(hours=5)

    windows = make_time_windows(start, end, max_minutes=60)

    assert len(windows) == 5

    for previous, following in pairwise(windows):
        assert previous[1] == following[0]


def test_rejects_reversed_range():
    start = datetime(2026, 11, 15, tzinfo=UTC)

    with pytest.raises(ValueError):
        make_time_windows(start, start - timedelta(hours=1))


def test_rejects_naive_timestamps():
    start = datetime(2026, 11, 15)
    end = start + timedelta(hours=1)

    with pytest.raises(ValueError):
        make_time_windows(start, end)


def test_rejects_invalid_window_size():
    start = datetime(2026, 11, 15, tzinfo=UTC)
    end = start + timedelta(hours=1)

    with pytest.raises(ValueError):
        make_time_windows(start, end, max_minutes=0)
