"""Discover longer-lived settled Kalshi series across categories.

Uses a reproducible random sample from the public series catalog.

Side effects:
    Read-only Kalshi API requests.
"""

import random

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

CATEGORIES = [
    "Economics",
    "Financials",
    "Elections",
    "Climate and Weather",
    "Science and Technology",
]

SAMPLE_PER_CATEGORY = 12
RANDOM_SEED = 42


def main() -> None:
    rng = random.Random(RANDOM_SEED)

    with create_kalshi_http_client() as client:
        response = get_with_retry(
            client,
            "/series",
            params={"limit": 200},
        )

        series_catalog = response.json().get("series", [])

        selected = []

        for category in CATEGORIES:
            candidates = [
                series
                for series in series_catalog
                if series.get("category") == category and series.get("ticker")
            ]

            sample_size = min(SAMPLE_PER_CATEGORY, len(candidates))

            sampled = rng.sample(candidates, sample_size)

            selected.extend(sampled)

            print(f"{category}: {len(candidates)} catalog series, {len(sampled)} sampled")

        results = []

        for index, series in enumerate(selected, start=1):
            ticker = series["ticker"]

            try:
                response = get_with_retry(
                    client,
                    "/markets",
                    params={
                        "series_ticker": ticker,
                        "status": "settled",
                        "limit": 100,
                        "mve_filter": "exclude",
                    },
                )

                payload = response.json()
                markets = payload.get("markets", [])

                lifetimes = []

                for market in markets:
                    opened = pd.to_datetime(
                        market.get("open_time"),
                        utc=True,
                        errors="coerce",
                    )
                    closed = pd.to_datetime(
                        market.get("close_time"),
                        utc=True,
                        errors="coerce",
                    )

                    if pd.notna(opened) and pd.notna(closed):
                        lifetime = (closed - opened).total_seconds() / 3600

                        if lifetime >= 0:
                            lifetimes.append(lifetime)

                results.append(
                    {
                        "category": series.get("category"),
                        "series": ticker,
                        "contracts": len(markets),
                        "events": len(
                            {
                                market.get("event_ticker")
                                for market in markets
                                if market.get("event_ticker")
                            }
                        ),
                        "over_24h": sum(lifetime >= 24 for lifetime in lifetimes),
                        "over_7d": sum(lifetime >= 168 for lifetime in lifetimes),
                        "max_lifetime_days": (max(lifetimes) / 24 if lifetimes else None),
                        "more_pages": bool(payload.get("cursor")),
                    }
                )

            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                print(f"Error inspecting {ticker}: {exc}")
                continue

            if index % 10 == 0:
                print(f"Inspected {index}/{len(selected)} series")

    df = pd.DataFrame(results)

    if df.empty:
        print("No series could be inspected.")
        return

    df = df.sort_values(
        ["over_24h", "events"],
        ascending=False,
    )

    print("\nTOP LONG-LIVED CANDIDATES")
    print(df.head(25).to_string(index=False))

    print("\nCATEGORY SUMMARY")
    print(
        df.groupby("category")
        .agg(
            series_checked=("series", "count"),
            series_with_settled=("contracts", lambda x: (x > 0).sum()),
            series_with_long_lived=("over_24h", lambda x: (x > 0).sum()),
            long_lived_contracts=("over_24h", "sum"),
        )
        .to_string()
    )


if __name__ == "__main__":
    main()
