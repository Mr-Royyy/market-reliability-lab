"""Audit point-in-time snapshot coverage across forecast horizons.

Inputs:
    Historical candles for one NYC hourly temperature event.

Outputs:
    Snapshot availability, quote age, spread, and midpoint.

Side effects:
    Read-only API requests. No files written.
"""

from datetime import datetime, timedelta

import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry
from market_reliability.data.snapshots import select_quote_snapshot

SERIES = "KXTEMPNYCHS"
EVENTS_TO_AUDIT = 5

HORIZONS = [45, 30, 15]
MAX_QUOTE_AGE_MINUTES = 5


def main() -> None:
    """Compare quote coverage at three forecast horizons."""
    rows = []

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

        all_markets = response.json()["markets"]

        event_tickers = sorted(
            {market["event_ticker"] for market in all_markets if market.get("event_ticker")}
        )

        selected_events = event_tickers[:EVENTS_TO_AUDIT]

        markets = [
            market for market in all_markets if market.get("event_ticker") in selected_events
        ]

        print(f"Selected events: {selected_events}")

        print(f"Events selected: {len(selected_events)}")
        print(f"Contracts found: {len(markets)}")

        for market in markets:
            ticker = market["ticker"]
            opened = datetime.fromisoformat(market["open_time"])
            closed = datetime.fromisoformat(market["close_time"])

            candles = fetch_candlestick_history(
                client=client,
                series_ticker=SERIES,
                market_ticker=ticker,
                start=opened,
                end=closed,
                max_minutes=1440,
            )

            df = build_candle_dataframe(ticker, candles)

            for horizon in HORIZONS:
                cutoff = pd.Timestamp(closed - timedelta(minutes=horizon))

                snapshot = select_quote_snapshot(
                    df,
                    cutoff,
                    max_age_minutes=MAX_QUOTE_AGE_MINUTES,
                )

                rows.append(
                    {
                        "ticker": ticker,
                        "outcome": market.get("result"),
                        "horizon_minutes": horizon,
                        "has_snapshot": snapshot is not None,
                        "quote_age_minutes": (
                            snapshot["quote_age_minutes"] if snapshot is not None else None
                        ),
                        "midpoint": (snapshot["midpoint"] if snapshot is not None else None),
                        "spread": (snapshot["spread"] if snapshot is not None else None),
                        "event_ticker": market["event_ticker"],
                    }
                )

    report = pd.DataFrame(rows)

    print("\nSNAPSHOT AVAILABILITY BY HORIZON")

    summary = report.groupby("horizon_minutes").agg(
        contracts=("ticker", "count"),
        usable_snapshots=("has_snapshot", "sum"),
        median_quote_age=("quote_age_minutes", "median"),
        median_spread=("spread", "median"),
    )

    summary["coverage_pct"] = 100 * summary["usable_snapshots"] / summary["contracts"]

    print(summary.to_string())

    print("\nCONTRACT-LEVEL RESULTS")
    print(
        report.sort_values(
            ["horizon_minutes", "ticker"],
            ascending=[False, True],
        ).to_string(index=False)
    )

    print("\nCOVERAGE BY EVENT AND HORIZON")
    event_summary = report.groupby(["event_ticker", "horizon_minutes"]).agg(
        contracts=("ticker", "count"),
        usable=("has_snapshot", "sum"),
    )

    event_summary["coverage_pct"] = 100 * event_summary["usable"] / event_summary["contracts"]

    print(event_summary.to_string())


if __name__ == "__main__":
    main()
