"""Audit historical quote feasibility for longer-lived Kalshi markets.

Makes read-only API requests. Does not save files.
"""

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry

SERIES = [
    "KXRAINMIAM",
    "KXRAINAUSM",
    "KXLOWTLAX",
    "KXUSHOMEINVENT",
    "KXINXU",
]

MAX_EVENTS = 3


def main() -> None:
    results = []

    with create_kalshi_http_client() as client:
        for series in SERIES:
            response = get_with_retry(
                client,
                "/markets",
                params={
                    "series_ticker": series,
                    "status": "settled",
                    "limit": 200,
                    "mve_filter": "exclude",
                },
            )

            markets = response.json().get("markets", [])
            by_event = {}

            for market in markets:
                event = market.get("event_ticker")
                if event:
                    by_event.setdefault(event, []).append(market)

            selected_events = sorted(by_event)[:MAX_EVENTS]

            print(f"\nSERIES: {series}")

            for event in selected_events:
                # Deterministic selection, not based on outcome.
                market = min(
                    by_event[event],
                    key=lambda item: item["ticker"],
                )

                ticker = market["ticker"]
                opened = pd.Timestamp(market["open_time"])
                closed = pd.Timestamp(market["close_time"])

                lifetime = closed - opened

                if lifetime < pd.Timedelta(hours=24):
                    continue

                targets = {
                    "24h_before_close": closed - pd.Timedelta(hours=24),
                    "mid_lifetime": opened + lifetime / 2,
                }

                for window_name, target in targets.items():
                    start = max(
                        opened,
                        target - pd.Timedelta(minutes=60),
                    )
                    end = min(
                        closed,
                        target + pd.Timedelta(minutes=60),
                    )

                    if start >= end:
                        continue

                    try:
                        candles = fetch_candlestick_history(
                            client=client,
                            series_ticker=series,
                            market_ticker=ticker,
                            start=start,
                            end=end,
                        )

                        df = build_candle_dataframe(
                            ticker,
                            candles,
                        )

                        # Do not include post-close candle timestamps.
                        df = df.loc[
                            (df["timestamp_utc"] >= start)
                            & (df["timestamp_utc"] <= end)
                            & (df["timestamp_utc"] <= closed)
                        ]

                        usable = df.loc[df["usable_midpoint"]]

                        uncertain = usable["midpoint"].between(0.2, 0.8)

                        results.append(
                            {
                                "series": series,
                                "event": event,
                                "window": window_name,
                                "candles": len(df),
                                "usable": len(usable),
                                "uncertain": int(uncertain.sum()),
                                "median_spread": usable["spread"].median(),
                            }
                        )

                    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                        print(f"Failed {ticker}, {window_name}: {exc}")

            print(f"Finished {series}")

    if not results:
        print("No eligible historical windows found.")
        return

    df = pd.DataFrame(results)

    print("\nHISTORICAL QUOTE FEASIBILITY")
    print(df.to_string(index=False))

    print("\nSERIES SUMMARY")
    print(
        df.groupby("series")
        .agg(
            windows=("window", "count"),
            usable_candles=("usable", "sum"),
            uncertain_candles=("uncertain", "sum"),
        )
        .to_string()
    )


if __name__ == "__main__":
    main()
