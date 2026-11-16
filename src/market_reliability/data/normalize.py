"""Convert Kalshi candlesticks into consistent research records."""

import math
from typing import Any


def read_close(candle: dict[str, Any], field: str) -> float | None:
    """Read a nested closing price, preserving missing values."""
    price_data = candle.get(field)

    if price_data is None:
        return None

    if not isinstance(price_data, dict):
        raise TypeError(f"{field} must be a dictionary.")

    value = price_data.get("close_dollars")

    if value is None:
        return None

    price = float(value)

    if not math.isfinite(price) or not 0 <= price <= 1:
        raise ValueError(f"Invalid {field} closing price.")

    return price


def normalize_candle(
    market_ticker: str,
    candle: dict[str, Any],
) -> dict[str, Any]:
    """Normalize one candlestick without modifying the source data."""
    if not market_ticker:
        raise ValueError("Market ticker cannot be empty.")

    timestamp = candle["end_period_ts"]

    if type(timestamp) is not int or timestamp <= 0:
        raise ValueError("Invalid candlestick timestamp.")

    trade = read_close(candle, "price")
    bid = read_close(candle, "yes_bid")
    ask = read_close(candle, "yes_ask")

    volume = float(candle["volume_fp"])

    if not math.isfinite(volume) or volume < 0:
        raise ValueError("Invalid volume.")

    spread = None
    midpoint = None

    if bid is not None and ask is not None:
        if bid > ask:
            raise ValueError("Bid cannot exceed ask.")

        spread = ask - bid
        midpoint = (bid + ask) / 2

    return {
        "market_ticker": market_ticker,
        "end_period_ts": timestamp,
        "trade_close": trade,
        "yes_bid_close": bid,
        "yes_ask_close": ask,
        "volume": volume,
        "spread": spread,
        "midpoint": midpoint,
    }
