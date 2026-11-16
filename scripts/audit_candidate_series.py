"""Audit resolved-market availability across selected Kalshi series.

Inputs:
    Public series catalog and settled-market metadata.

Outputs:
    Per-series counts and example market durations.

Side effects:
    Read-only API requests. No files written.
"""

from collections import defaultdict
from datetime import datetime

import httpx

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

SERIES_PER_CATEGORY = 5
MARKETS_PER_SERIES = 100


def market_duration_hours(market: dict) -> float | None:
    """Return market lifetime in hours, or None if invalid."""
    try:
        opened = datetime.fromisoformat(market["open_time"])
        closed = datetime.fromisoformat(market["close_time"])

        if opened.utcoffset() is None or closed.utcoffset() is None:
            return None

        duration = (closed - opened).total_seconds() / 3600

        return duration if duration > 0 else None

    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def main() -> None:
    """Inspect a small, reproducible sample of series."""
    with create_kalshi_http_client() as client:
        catalog_response = get_with_retry(client, "/series")
        catalog = catalog_response.json()["series"]

        grouped = defaultdict(list)

        for series in catalog:
            category = series.get("category")

            if category in CATEGORIES:
                grouped[category].append(series)

        selected = []

        for category in CATEGORIES:
            candidates = sorted(
                grouped[category],
                key=lambda item: item["ticker"],
            )

            selected.extend(candidates[:SERIES_PER_CATEGORY])

        print(f"Selected series: {len(selected)}")

        for series in selected:
            ticker = series["ticker"]
            category = series["category"]

            try:
                response = get_with_retry(
                    client,
                    "/markets",
                    params={
                        "series_ticker": ticker,
                        "status": "settled",
                        "limit": MARKETS_PER_SERIES,
                        "mve_filter": "exclude",
                    },
                )

                markets = response.json()["markets"]

                binary = [
                    market
                    for market in markets
                    if market.get("market_type") == "binary"
                    and market.get("result") in ("yes", "no")
                ]

                durations = [
                    duration
                    for market in binary
                    if (duration := market_duration_hours(market)) is not None
                ]

                longest = max(durations) if durations else None

                print(
                    f"{category:24} "
                    f"{ticker:25} "
                    f"settled={len(markets):3} "
                    f"binary={len(binary):3} "
                    f"max_hours={longest}"
                )

            except (
                httpx.HTTPError,
                ValueError,
                TypeError,
                KeyError,
            ) as error:
                print(f"{category:24} {ticker:25} ERROR={type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
