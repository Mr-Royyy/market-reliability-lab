"""Inspect rainfall event rules and contract timing.

Read-only requests. Does not write files.
"""

import json

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

SERIES = (
    "KXRAINMIAM",
    "KXRAINNYCM",
    "KXRAINAUSM",
    "KXRAINHOUM",
    "KXRAINSEAM",
)

FIELDS = (
    "ticker",
    "event_ticker",
    "title",
    "subtitle",
    "rules_primary",
    "rules_secondary",
    "open_time",
    "close_time",
    "expiration_time",
    "settlement_ts",
    "settlement_timer_seconds",
    "result",
    "status",
)


def inspect_event(client, series: str) -> None:
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

    if not markets:
        print(f"\n{series}: no settled contracts")
        return

    event_ticker = min(market["event_ticker"] for market in markets if market.get("event_ticker"))

    event_response = get_with_retry(
        client,
        f"/events/{event_ticker}",
    )

    event = event_response.json().get("event", {})

    selected = min(
        (market for market in markets if market.get("event_ticker") == event_ticker),
        key=lambda market: market["ticker"],
    )

    print(f"\n{'=' * 65}")
    print(f"SERIES: {series}")
    print(f"EVENT: {event_ticker}")

    print("\nEVENT METADATA")
    print(json.dumps(event, indent=2, default=str))

    print("\nSAMPLE CONTRACT")
    print(
        json.dumps(
            {key: selected.get(key) for key in FIELDS},
            indent=2,
            default=str,
        )
    )


def main() -> None:
    with create_kalshi_http_client() as client:
        for series in SERIES:
            inspect_event(client, series)


if __name__ == "__main__":
    main()
