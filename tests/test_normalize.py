"""Tests for Kalshi candlestick normalization."""

from copy import deepcopy

import pytest

from market_reliability.data.normalize import normalize_candle


@pytest.fixture
def example_candle():
    """Return a representative candle with quotes but no trade."""
    return {
        "end_period_ts": 1794770520,
        "price": {},
        "volume_fp": "0.00",
        "yes_bid": {"close_dollars": "0.2300"},
        "yes_ask": {"close_dollars": "0.2600"},
    }


def test_normalizes_quote_only_candle(example_candle):
    result = normalize_candle("EXAMPLE", example_candle)

    assert result["market_ticker"] == "EXAMPLE"
    assert result["trade_close"] is None
    assert result["volume"] == 0.0
    assert result["spread"] == pytest.approx(0.03)
    assert result["midpoint"] == pytest.approx(0.245)


def test_preserves_original_candle(example_candle):
    original = deepcopy(example_candle)

    normalize_candle("EXAMPLE", example_candle)

    assert example_candle == original


def test_normalizes_trade_price(example_candle):
    example_candle["price"] = {"close_dollars": "0.7500"}
    example_candle["volume_fp"] = "25.50"

    result = normalize_candle("EXAMPLE", example_candle)

    assert result["trade_close"] == pytest.approx(0.75)
    assert result["volume"] == pytest.approx(25.5)


def test_rejects_crossed_quotes(example_candle):
    example_candle["yes_bid"]["close_dollars"] = "0.80"

    with pytest.raises(ValueError):
        normalize_candle("EXAMPLE", example_candle)


@pytest.mark.parametrize(
    "invalid_price",
    ["-0.10", "1.10", "nan", "inf"],
)
def test_rejects_invalid_prices(example_candle, invalid_price):
    example_candle["price"] = {"close_dollars": invalid_price}

    with pytest.raises(ValueError):
        normalize_candle("EXAMPLE", example_candle)


def test_rejects_negative_volume(example_candle):
    example_candle["volume_fp"] = "-1.0"

    with pytest.raises(ValueError):
        normalize_candle("EXAMPLE", example_candle)


def test_rejects_invalid_timestamp(example_candle):
    example_candle["end_period_ts"] = -1

    with pytest.raises(ValueError):
        normalize_candle("EXAMPLE", example_candle)
