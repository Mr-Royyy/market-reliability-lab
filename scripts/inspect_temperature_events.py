"""Inspect the structure of recurring temperature market events.

Inputs:
    Settled contracts from three temperature series.

Outputs:
    Event identifiers, titles, contract counts, and example rules.

Side effects:
    Read-only API requests. No files written.
"""

from collections import defaultdict

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

SERIES = [
    "KXTEMPNYCHS",
    "KXTEMPLAXHS",
    "KXTEMPCHIHS",
]

PAGE_SIZE = 200
MAX_EVENTS_TO_PRINT = 8


def main() -> None:
    """Inspect event grouping within recurring temperature markets."""
    with create_kalshi_http_client() as client:
        for series_ticker in SERIES:
            response = get_with_retry(
                client,
                "/markets",
                params={
                    "series_ticker": series_ticker,
                    "status": "settled",
                    "limit": PAGE_SIZE,
                    "mve_filter": "exclude",
                },
            )

            markets = response.json()["markets"]

            grouped = defaultdict(list)

            for market in markets:
                event_ticker = market.get("event_ticker")

                if event_ticker:
                    grouped[event_ticker].append(market)

            print(f"\nSERIES: {series_ticker}")
            print(f"Contracts returned: {len(markets)}")
            print(f"Unique event identifiers: {len(grouped)}")

            for event_ticker in sorted(grouped)[:MAX_EVENTS_TO_PRINT]:
                contracts = grouped[event_ticker]

                print(f"\nEVENT: {event_ticker}")
                print(f"Contracts in sampled page: {len(contracts)}")

                for market in contracts[:3]:
                    print(
                        {
                            "ticker": market.get("ticker"),
                            "title": market.get("title"),
                            "result": market.get("result"),
                            "open_time": market.get("open_time"),
                            "close_time": market.get("close_time"),
                            "rules_primary": market.get("rules_primary"),
                        }
                    )


if __name__ == "__main__":
    main()
