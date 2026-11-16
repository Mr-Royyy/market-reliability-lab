"""Inspect historical quote coverage at four points in a long-lived market.

Inputs:
    One Kalshi market ticker and four historical date windows.

Outputs:
    Per-window candle counts and quote-quality diagnostics.

Side effects:
    Makes read-only API requests. Does not write files.
"""

from datetime import UTC, datetime, timedelta

import httpx

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe

SERIES = "CONTROLH"
TICKER = "CONTROLH-2026-R"

CHECKPOINTS = [
    datetime(2024, 11, 15, tzinfo=UTC),
    datetime(2025, 6, 15, tzinfo=UTC),
    datetime(2026, 6, 15, tzinfo=UTC),
    datetime(2026, 10, 15, tzinfo=UTC),
]


def main() -> None:
    """Retrieve and summarize one day of candles per checkpoint."""
    with create_kalshi_http_client() as client:
        for start in CHECKPOINTS:
            end = start + timedelta(days=1)

            print(f"\nCHECKPOINT: {start.date()}")

            try:
                candles = fetch_candlestick_history(
                    client=client,
                    series_ticker=SERIES,
                    market_ticker=TICKER,
                    start=start,
                    end=end,
                    max_minutes=1440,
                )

                df = build_candle_dataframe(TICKER, candles)

                print(f"Candles returned: {len(df)}")

                if df.empty:
                    print("No historical candles available.")
                    continue

                print(f"Usable quotes: {int(df['usable_midpoint'].sum())}")
                print(f"Trade candles: {int(df['has_trade'].sum())}")
                print(f"Median spread: {df['spread'].median()}")
                print(f"Median midpoint: {df['midpoint'].median()}")
                print(f"Total observed volume: {df['volume'].sum()}")

                print(
                    "Timestamp range:",
                    df["timestamp_utc"].min(),
                    "to",
                    df["timestamp_utc"].max(),
                )

            except (
                httpx.HTTPError,
                ValueError,
                TypeError,
                KeyError,
            ) as error:
                print(f"ERROR: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
