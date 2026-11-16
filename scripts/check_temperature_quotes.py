"""Inspect historical quote coverage across one temperature event.

Inputs:
    Settled contracts from one NYC hourly temperature event.

Outputs:
    Per-contract quote coverage and timestamp diagnostics.

Side effects:
    Read-only API requests. No files written.
"""

from datetime import datetime

import httpx

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry

SERIES = "KXTEMPNYCHS"
EVENT = "KXTEMPNYCHS-26NOV1509"


def main() -> None:
    """Inspect the first five contracts belonging to one event."""
    with create_kalshi_http_client() as client:
        response = get_with_retry(
            client,
            "/markets",
            params={
                "series_ticker": SERIES,
                "status": "settled",
                "limit": 200,
                "mve_filter": "exclude",
            },
        )

        markets = [
            market for market in response.json()["markets"] if market.get("event_ticker") == EVENT
        ]

        print(f"Event: {EVENT}")
        print(f"Contracts found in sampled page: {len(markets)}")

        for market in markets[:5]:
            ticker = market["ticker"]
            opened = datetime.fromisoformat(market["open_time"])
            closed = datetime.fromisoformat(market["close_time"])

            print(f"\nContract: {ticker}")
            print(f"Outcome: {market.get('result')}")
            print(f"Open: {opened}")
            print(f"Close: {closed}")

            try:
                candles = fetch_candlestick_history(
                    client=client,
                    series_ticker=SERIES,
                    market_ticker=ticker,
                    start=opened,
                    end=closed,
                    max_minutes=1440,
                )

                df = build_candle_dataframe(ticker, candles)

                print(f"Candles: {len(df)}")

                if df.empty:
                    continue

                df = df[(df["timestamp_utc"] >= opened) & (df["timestamp_utc"] < closed)]

                print(f"Pre-close candles: {len(df)}")
                print(f"Usable midpoint candles: {int(df['usable_midpoint'].sum())}")
                print(f"Trade candles: {int(df['has_trade'].sum())}")
                print(f"Median spread: {df['spread'].median()}")

                if not df.empty:
                    print(
                        "First candle:",
                        df["timestamp_utc"].min(),
                    )
                    print(
                        "Last candle:",
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
