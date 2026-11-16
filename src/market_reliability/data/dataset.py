"""Build validated research tables from Kalshi candlesticks."""

from typing import Any

import pandas as pd

from market_reliability.data.normalize import normalize_candle

COLUMNS = [
    "market_ticker",
    "end_period_ts",
    "trade_close",
    "yes_bid_close",
    "yes_ask_close",
    "volume",
    "spread",
    "midpoint",
    "timestamp_utc",
    "has_trade",
    "has_valid_quotes",
    "usable_midpoint",
]


def build_candle_dataframe(
    market_ticker: str,
    candles: list[dict[str, Any]],
    max_spread: float = 0.10,
) -> pd.DataFrame:
    """Normalize candles and add exploratory data-quality indicators.

    Inputs:
        market_ticker: Identifier of the Kalshi market.
        candles: Raw API candlestick records.
        max_spread: Maximum allowed spread for the midpoint quality flag.

    Returns:
        A chronologically sorted DataFrame with quality indicators.

    Side effects:
        None. Does not modify inputs, contact the API, or save files.
    """
    if not 0 <= max_spread <= 1:
        raise ValueError("max_spread must be between 0 and 1.")

    records = [normalize_candle(market_ticker, candle) for candle in candles]

    if not records:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(records)

    df["timestamp_utc"] = pd.to_datetime(
        df["end_period_ts"],
        unit="s",
        utc=True,
    )

    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    if df["end_period_ts"].duplicated().any():
        raise ValueError("Duplicate timestamps detected.")

    df["has_trade"] = df["trade_close"].notna() & (df["volume"] > 0)

    df["has_valid_quotes"] = (
        df["yes_bid_close"].notna() & df["yes_ask_close"].notna() & df["spread"].notna()
    )

    df["usable_midpoint"] = df["has_valid_quotes"] & df["spread"].le(max_spread)

    return df[COLUMNS]
