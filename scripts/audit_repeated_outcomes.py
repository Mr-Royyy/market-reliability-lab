"""Compare known populated Kalshi series for research suitability.

Inputs:
    Settled-market metadata for selected series.

Outputs:
    Per-series counts, event diversity, and market lifetime statistics.

Side effects:
    Read-only HTTP requests. No files written.
"""

from datetime import datetime

import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

SERIES = [
    "KXTEMPNYCHS",
    "KXTEMPLAXHS",
    "KXTEMPCHIHS",
    "KXPLATINUMH",
    "KXPALLADIUMH",
    "KXWTIH",
    "KXESOCCERGAME",
    "CONTROLH",
]

PAGE_SIZE = 200


def duration_hours(market: dict) -> float | None:
    """Calculate the lifetime of a contract."""
    try:
        opened = datetime.fromisoformat(market["open_time"])
        closed = datetime.fromisoformat(market["close_time"])

        if opened.utcoffset() is None or closed.utcoffset() is None:
            return None

        hours = (closed - opened).total_seconds() / 3600
        return hours if hours > 0 else None

    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def main() -> None:
    """Compare the first page of settled contracts per series."""
    reports = []

    with create_kalshi_http_client() as client:
        for ticker in SERIES:
            response = get_with_retry(
                client,
                "/markets",
                params={
                    "series_ticker": ticker,
                    "status": "settled",
                    "limit": PAGE_SIZE,
                    "mve_filter": "exclude",
                },
            )

            payload = response.json()
            markets = payload["markets"]

            binary = [
                market
                for market in markets
                if market.get("market_type") == "binary" and market.get("result") in ("yes", "no")
            ]

            durations = [
                hours for market in binary if (hours := duration_hours(market)) is not None
            ]

            reports.append(
                {
                    "series": ticker,
                    "contracts": len(binary),
                    "unique_events": len(
                        {market["event_ticker"] for market in binary if market.get("event_ticker")}
                    ),
                    "median_hours": (
                        round(pd.Series(durations).median(), 1) if durations else None
                    ),
                    "max_hours": (round(max(durations), 1) if durations else None),
                    "more_pages": bool(payload.get("cursor")),
                }
            )

    report = pd.DataFrame(reports)

    print("\nREPEATED-OUTCOME SERIES AUDIT")
    print(report.to_string(index=False))

    print("\nNOTE: Counts cover only the first returned page of each series.")


if __name__ == "__main__":
    main()
