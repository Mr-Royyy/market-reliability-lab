"""Diagnose raw historical candle availability at a fixed checkpoint."""

import json

import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry

SERIES = "KXRAINMIAM"
EVENT = "KXRAINMIAM-26NOV"
CUTOFF = pd.Timestamp("2026-11-24T18:00:00Z")
LOOKBACK_HOURS = 24


def main() -> None:
    with create_kalshi_http_client() as client:
        response = get_with_retry(
            client,
            "/markets",
            params={
                "series_ticker": SERIES,
                "limit": 200,
                "mve_filter": "exclude",
            },
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("cursor"):
            raise RuntimeError("Market pagination required")

        markets = [
            market for market in payload.get("markets", []) if market.get("event_ticker") == EVENT
        ]

        for market in markets:
            opened = pd.to_datetime(market["open_time"], utc=True)
            closed = pd.to_datetime(market["close_time"], utc=True)

            if not (opened <= CUTOFF < closed):
                continue

            ticker = market["ticker"]
            start = max(
                opened,
                CUTOFF - pd.Timedelta(hours=LOOKBACK_HOURS),
            )

            candles = fetch_candlestick_history(
                client=client,
                series_ticker=SERIES,
                market_ticker=ticker,
                start=start,
                end=CUTOFF,
            )

            df = build_candle_dataframe(ticker, candles)

            print(f"\n{'=' * 65}")
            print(f"CONTRACT: {ticker}")
            print(f"Raw candles: {len(candles)}")
            print(f"Normalized rows: {len(df)}")

            if candles:
                print("\nFIRST RAW CANDLE")
                print(json.dumps(candles[0], indent=2, default=str))

                print("\nLAST RAW CANDLE")
                print(json.dumps(candles[-1], indent=2, default=str))

            if not df.empty:
                print("\nNORMALIZED QUOTE SUMMARY")
                print(f"Valid quote rows: {int(df['has_valid_quotes'].sum())}")
                print(f"Usable midpoint rows: {int(df['usable_midpoint'].sum())}")

                print("\nLAST FIVE NORMALIZED ROWS")
                print(df.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
