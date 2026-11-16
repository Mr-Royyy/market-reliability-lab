"""Inspect a small sample of resolved Kalshi markets.

Inputs:
    Up to 20 settled markets from Kalshi's public API.

Outputs:
    Market counts, outcome distribution, event counts, and sample records.

Side effects:
    Read-only network requests. No files are written.
"""

from collections import Counter

import httpx
import pandas as pd

from market_reliability.data.kalshi_client import BASE_URL, KalshiClient
from market_reliability.data.market_metadata import normalize_market_metadata


def collect_sample(limit: int = 20) -> tuple[pd.DataFrame, Counter]:
    """Collect resolved markets and normalize their metadata."""
    api = KalshiClient()
    response = api.get_markets(
        status="settled",
        limit=limit,
        mve_filter="exclude",
    )

    records = []
    failures = Counter()
    event_cache = {}

    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        for market in response["markets"]:
            if market.get("result") not in ("yes", "no"):
                failures["unresolved_outcome"] += 1
                continue

            event_ticker = market.get("event_ticker")

            try:
                if event_ticker not in event_cache:
                    event_response = client.get(f"/events/{event_ticker}")
                    event_response.raise_for_status()
                    event_cache[event_ticker] = event_response.json()["event"]

                record = normalize_market_metadata(
                    market,
                    event_cache[event_ticker],
                )
                records.append(record)

            except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
                failures[type(error).__name__] += 1

    return pd.DataFrame(records), failures


def main() -> None:
    """Print the results of the sample collection."""
    df, failures = collect_sample()

    print("\nMULTI-MARKET COLLECTION REPORT")
    print(f"Validated markets: {len(df)}")

    if df.empty:
        print(f"Failures: {dict(failures)}")
        return

    print(f"Unique events: {df['event_ticker'].nunique()}")
    print(f"Unique series: {df['series_ticker'].nunique()}")

    print("\nOUTCOME DISTRIBUTION")
    print(df["outcome"].value_counts().sort_index())

    print("\nCATEGORY DISTRIBUTION")
    print(df["category"].value_counts(dropna=False))

    print("\nMARKETS PER EVENT")
    print(df.groupby("event_ticker").size().sort_values(ascending=False).head(10))

    print("\nSAMPLE MARKETS")
    print(
        df[
            [
                "market_ticker",
                "event_ticker",
                "category",
                "outcome",
                "open_time",
                "close_time",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nVALIDATION FAILURES")
    print(dict(failures))


if __name__ == "__main__":
    main()
