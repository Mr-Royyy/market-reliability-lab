"""Audit historical probability uncertainty across temperature contracts.

Fetches a small sample of resolved NYC temperature contracts and
examines their pre-close midpoint probabilities.

Side effects:
    Read-only Kalshi API requests.
"""

import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry
from market_reliability.data.market_metadata import normalize_market_metadata

SERIES = "KXTEMPNYCHS"
MAX_EVENTS = 3


def main() -> None:
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

        markets = response.json()["markets"]

        event_tickers = sorted(
            {market["event_ticker"] for market in markets if market.get("event_ticker")}
        )[:MAX_EVENTS]

        for event_ticker in event_tickers:
            event = get_with_retry(
                client,
                f"/events/{event_ticker}",
            ).json()["event"]

            event_markets = [
                market for market in markets if market.get("event_ticker") == event_ticker
            ]

            print(f"\nEVENT: {event_ticker}")

            for market in event_markets:
                metadata = normalize_market_metadata(market, event)

                candles = fetch_candlestick_history(
                    client=client,
                    series_ticker=SERIES,
                    market_ticker=metadata["market_ticker"],
                    start=metadata["open_time"],
                    end=metadata["close_time"],
                )

                df = build_candle_dataframe(
                    metadata["market_ticker"],
                    candles,
                )

                df = df.loc[df["usable_midpoint"]].copy()

                if df.empty:
                    continue

                close_time = pd.Timestamp(metadata["close_time"])

                df["minutes_before_close"] = (
                    close_time - df["timestamp_utc"]
                ).dt.total_seconds() / 60

                df = df.loc[df["minutes_before_close"] >= 0]

                uncertain = df["midpoint"].between(0.2, 0.8)

                print(
                    f"{metadata['market_ticker']}: "
                    f"usable={len(df)}, "
                    f"uncertain={uncertain.sum()}, "
                    f"uncertain_pct={uncertain.mean():.1%}, "
                    f"max_lead={df['minutes_before_close'].max():.1f}m, "
                    f"min_p={df['midpoint'].min():.3f}, "
                    f"max_p={df['midpoint'].max():.3f}"
                )


if __name__ == "__main__":
    main()
