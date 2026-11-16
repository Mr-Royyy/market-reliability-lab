"""Audit historical quote uncertainty across rainfall contracts.

Inputs:
    Settled Kalshi contracts in Austin and Miami monthly rainfall series.

Outputs:
    Console summaries by contract, event, and series.

Side effects:
    Read-only API requests. No files written.
"""

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry

SERIES = ("KXRAINAUSM", "KXRAINMIAM")
MAX_EVENTS = 3
WINDOW_MINUTES = 60


def audit_window(
    client: httpx.Client,
    series: str,
    market: dict,
    window_name: str,
    target: pd.Timestamp,
) -> dict:
    """Audit a two-hour window centered on a target time."""
    ticker = market["ticker"]
    opened = pd.Timestamp(market["open_time"])
    closed = pd.Timestamp(market["close_time"])

    start = max(opened, target - pd.Timedelta(minutes=WINDOW_MINUTES))
    end = min(closed, target + pd.Timedelta(minutes=WINDOW_MINUTES))

    if start >= end:
        return {
            "series": series,
            "event": market["event_ticker"],
            "market": ticker,
            "window": window_name,
            "candles": 0,
            "usable": 0,
            "uncertain": 0,
        }

    candles = fetch_candlestick_history(
        client=client,
        series_ticker=series,
        market_ticker=ticker,
        start=start,
        end=end,
    )

    df = build_candle_dataframe(ticker, candles)

    df = df.loc[
        (df["timestamp_utc"] >= start)
        & (df["timestamp_utc"] <= end)
        & (df["timestamp_utc"] <= closed)
    ]

    usable = df.loc[df["usable_midpoint"]]

    uncertain = usable["midpoint"].between(0.2, 0.8)

    return {
        "series": series,
        "event": market["event_ticker"],
        "market": ticker,
        "window": window_name,
        "candles": len(df),
        "usable": len(usable),
        "uncertain": int(uncertain.sum()),
    }


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

            payload = response.json()
            markets = payload.get("markets", [])

            by_event = {}

            for market in markets:
                event = market.get("event_ticker")

                if event:
                    by_event.setdefault(event, []).append(market)

            selected_events = sorted(by_event)[:MAX_EVENTS]

            print(f"\nSERIES: {series}")
            print(f"Selected events: {selected_events}")

            for event in selected_events:
                event_markets = sorted(
                    by_event[event],
                    key=lambda market: market["ticker"],
                )

                print(f"Processing {event}: {len(event_markets)} contracts")

                for market in event_markets:
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
                        try:
                            result = audit_window(
                                client,
                                series,
                                market,
                                window_name,
                                target,
                            )
                            results.append(result)

                        except (
                            httpx.HTTPError,
                            ValueError,
                            KeyError,
                            TypeError,
                        ) as exc:
                            print(f"Failed {market['ticker']} ({window_name}): {exc}")

    if not results:
        print("No eligible observations found.")
        return

    df = pd.DataFrame(results)

    print("\nSERIES SUMMARY")
    print(
        df.groupby("series")
        .agg(
            contracts=("market", "nunique"),
            events=("event", "nunique"),
            windows=("window", "count"),
            usable_candles=("usable", "sum"),
            uncertain_candles=("uncertain", "sum"),
        )
        .to_string()
    )

    print("\nEVENT SUMMARY")
    print(
        df.groupby(["series", "event"])
        .agg(
            contracts=("market", "nunique"),
            usable_candles=("usable", "sum"),
            uncertain_candles=("uncertain", "sum"),
        )
        .to_string()
    )

    print("\nCONTRACTS WITH UNCERTAIN QUOTES")
    uncertain_contracts = df.loc[df["uncertain"] > 0]

    if uncertain_contracts.empty:
        print("None found.")
    else:
        print(
            uncertain_contracts.sort_values(["series", "event", "market", "window"]).to_string(
                index=False
            )
        )

    print("\nCOVERAGE")
    print(
        df.groupby("series")
        .agg(
            windows_checked=("window", "count"),
            windows_with_quotes=("usable", lambda x: (x > 0).sum()),
            windows_with_uncertainty=(
                "uncertain",
                lambda x: (x > 0).sum(),
            ),
        )
        .to_string()
    )


if __name__ == "__main__":
    main()
