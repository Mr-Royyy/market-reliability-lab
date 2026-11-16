"""Inspect resolved contracts from two long-lived election series.

Inputs:
    Public Kalshi metadata for CONTROLH and CONTROLS.

Outputs:
    Contract metadata, duration, and volume.

Side effects:
    Read-only API requests. No files written.
"""

from datetime import datetime

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

SERIES = ["CONTROLH", "CONTROLS"]


def main() -> None:
    """Print metadata for resolved contracts in selected series."""
    with create_kalshi_http_client() as client:
        for series_ticker in SERIES:
            response = get_with_retry(
                client,
                "/markets",
                params={
                    "series_ticker": series_ticker,
                    "status": "settled",
                    "limit": 100,
                    "mve_filter": "exclude",
                },
            )

            markets = response.json()["markets"]

            print(f"\nSERIES: {series_ticker}")
            print(f"Settled markets returned: {len(markets)}")

            for market in markets:
                opened = datetime.fromisoformat(market["open_time"])
                closed = datetime.fromisoformat(market["close_time"])

                duration_days = (closed - opened).total_seconds() / 86400

                print("\nMARKET")
                print(f"Ticker: {market.get('ticker')}")
                print(f"Title: {market.get('title')}")
                print(f"Result: {market.get('result')}")
                print(f"Status: {market.get('status')}")
                print(f"Opened: {opened}")
                print(f"Closed: {closed}")
                print(f"Duration (days): {duration_days:.1f}")
                print(f"Volume: {market.get('volume_fp')}")
                print(f"Open interest: {market.get('open_interest_fp')}")
                print(f"Event ticker: {market.get('event_ticker')}")
                print(f"Expiration: {market.get('expiration_time')}")
                print(f"Settlement: {market.get('settlement_ts')}")


if __name__ == "__main__":
    main()
