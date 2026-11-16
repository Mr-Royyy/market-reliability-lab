"""Inspect Kalshi market metadata before designing our research schema.

Inputs:
    A known Kalshi market ticker.

Outputs:
    Available metadata fields and selected values.

Side effects:
    Makes two read-only API requests. Does not save files.
"""

from pprint import pprint

import httpx

from market_reliability.data.kalshi_client import BASE_URL

TICKER = "KXNFLSPREAD-26NOV15MINGB-MIN21"

MARKET_FIELDS = [
    "ticker",
    "event_ticker",
    "status",
    "result",
    "market_type",
    "created_time",
    "open_time",
    "close_time",
    "expiration_time",
    "latest_expiration_time",
    "settlement_ts",
    "settlement_timer_seconds",
    "volume_fp",
    "open_interest_fp",
    "title",
    "rules_primary",
]

EVENT_FIELDS = [
    "event_ticker",
    "series_ticker",
    "title",
    "category",
    "mutually_exclusive",
    "strike_date",
]


def main() -> None:
    """Fetch a market and its parent event, then inspect their metadata."""
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        market_response = client.get(f"/markets/{TICKER}")
        market_response.raise_for_status()
        market = market_response.json()["market"]

        event_ticker = market["event_ticker"]

        event_response = client.get(f"/events/{event_ticker}")
        event_response.raise_for_status()
        event = event_response.json()["event"]

    print("\nMARKET: ALL AVAILABLE FIELD NAMES")
    pprint(sorted(market.keys()))

    print("\nMARKET: SELECTED FIELD VALUES")
    for field in MARKET_FIELDS:
        print(f"{field}: {market.get(field)!r}")

    print("\nEVENT: ALL AVAILABLE FIELD NAMES")
    pprint(sorted(event.keys()))

    print("\nEVENT: SELECTED FIELD VALUES")
    for field in EVENT_FIELDS:
        print(f"{field}: {event.get(field)!r}")


if __name__ == "__main__":
    main()
