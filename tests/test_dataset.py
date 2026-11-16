"""Tests for the candlestick DataFrame builder."""

import pytest

from market_reliability.data.dataset import build_candle_dataframe


def make_candle(
    timestamp: int,
    bid: str,
    ask: str,
    trade: str | None = None,
    volume: str = "0.00",
) -> dict:
    """Construct a small representative Kalshi candlestick."""
    return {
        "end_period_ts": timestamp,
        "price": {"close_dollars": trade} if trade is not None else {},
        "yes_bid": {"close_dollars": bid},
        "yes_ask": {"close_dollars": ask},
        "volume_fp": volume,
    }


def test_dataframe_sorts_timestamps():
    candles = [
        make_candle(1794770580, "0.20", "0.24"),
        make_candle(1794770520, "0.22", "0.26"),
    ]

    df = build_candle_dataframe("EXAMPLE", candles)

    assert df["end_period_ts"].tolist() == [
        1794770520,
        1794770580,
    ]


def test_flags_valid_midpoint():
    candle = make_candle(
        1794770520,
        "0.23",
        "0.26",
        trade="0.25",
        volume="10.00",
    )

    df = build_candle_dataframe("EXAMPLE", [candle])

    assert bool(df.loc[0, "has_trade"])
    assert bool(df.loc[0, "has_valid_quotes"])
    assert bool(df.loc[0, "usable_midpoint"])


def test_flags_wide_spread():
    candle = make_candle(
        1794770520,
        "0.00",
        "1.00",
        trade="0.01",
        volume="93.52",
    )

    df = build_candle_dataframe("EXAMPLE", [candle])

    assert not bool(df.loc[0, "usable_midpoint"])
    assert df.loc[0, "midpoint"] == pytest.approx(0.50)
    assert bool(df.loc[0, "has_trade"])


def test_rejects_duplicate_timestamps():
    candle = make_candle(1794770520, "0.20", "0.25")

    with pytest.raises(ValueError):
        build_candle_dataframe("EXAMPLE", [candle, candle])


def test_empty_input():
    df = build_candle_dataframe("EXAMPLE", [])

    assert df.empty
    assert "usable_midpoint" in df.columns


def test_rejects_invalid_spread_threshold():
    with pytest.raises(ValueError):
        build_candle_dataframe("EXAMPLE", [], max_spread=1.5)
