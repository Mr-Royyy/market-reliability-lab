"""Discover candidate Kalshi series for reliability research.

Inputs:
    Public Kalshi settled-market API responses.

Outputs:
    Console summary of candidate market populations.

Side effects:
    Read-only API requests. No files written.
"""

from collections import Counter

import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

CANDIDATE_SERIES = [
    "KXTEMPNYCHS",
    "KXESOCCERGAME",
    "KXPLATINUMH",
    "KXWTIH",
    "CONTROLH",
    "CONTROLS",
]

PAGE_SIZE = 200


def summarize_series(
    series_ticker: str,
    markets: list[dict],
) -> dict:
    """Summarize settled contracts returned for one series."""
    rows = []

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

        lifetime_hours = None

        if pd.notna(opened) and pd.notna(closed):
            lifetime_hours = (closed - opened).total_seconds() / 3600

        result = market.get("result")

        rows.append(
            {
                "event_ticker": market.get("event_ticker"),
                "lifetime_hours": lifetime_hours,
                "result": result,
            }
        )

    df = pd.DataFrame(
        rows,
        columns=[
            "event_ticker",
            "lifetime_hours",
            "result",
        ],
    )

    valid_lifetimes = df["lifetime_hours"].dropna()

    outcomes = Counter(df["result"])

    return {
        "series": series_ticker,
        "contracts": len(df),
        "events": df["event_ticker"].nunique(),
        "median_lifetime_h": (valid_lifetimes.median() if not valid_lifetimes.empty else None),
        "contracts_over_24h": int((df["lifetime_hours"] >= 24).sum()),
        "contracts_over_7d": int((df["lifetime_hours"] >= 168).sum()),
        "yes": outcomes.get("yes", 0),
        "no": outcomes.get("no", 0),
    }


def main() -> None:
    summaries = []

    with create_kalshi_http_client() as client:
        for series in CANDIDATE_SERIES:
            response = get_with_retry(
                client,
                "/markets",
                params={
                    "series_ticker": series,
                    "status": "settled",
                    "limit": PAGE_SIZE,
                    "mve_filter": "exclude",
                },
            )

            payload = response.json()
            markets = payload.get("markets", [])

            summary = summarize_series(series, markets)
            summary["more_pages"] = bool(payload.get("cursor"))

            summaries.append(summary)

            print(f"Processed {series}: {summary['contracts']} contracts")

    result = pd.DataFrame(summaries)

    print("\nCANDIDATE MARKET POPULATIONS")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
