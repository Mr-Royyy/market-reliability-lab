"""Inspect a small sample of Kalshi market records."""

from pprint import pprint

import httpx

from market_reliability.data.kalshi_client import KalshiClient


def main() -> None:
    """Fetch markets and display their available fields."""
    client = KalshiClient()

    try:
        payload = client.get_markets(
            status="settled",
            limit=20,
        )
    except (httpx.HTTPError, ValueError) as error:
        print(f"Kalshi request failed: {error}")
        return

    markets = payload["markets"]

    print(f"Markets returned: {len(markets)}")
    print(f"Pagination cursor present: {bool(payload.get('cursor'))}")

    if not markets:
        print("No markets returned for this request.")
        return

    first_market = markets[0]

    print("\nAvailable fields:")
    pprint(sorted(first_market.keys()))

    print("\nSelected values:")
    for field in (
        "ticker",
        "title",
        "status",
        "result",
        "created_time",
        "close_time",
        "expiration_time",
        "settlement_ts",
        "yes_bid_dollars",
        "yes_ask_dollars",
        "last_price_dollars",
        "volume_fp",
    ):
        print(f"{field}: {first_market.get(field)}")


if __name__ == "__main__":
    main()
