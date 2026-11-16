"""Inspect recent candlesticks for one Kalshi market."""

from datetime import UTC, datetime, timedelta
from pprint import pprint

import httpx

from market_reliability.data.kalshi_client import BASE_URL

TICKER = "KXNFLSPREAD-26NOV15MINGB-MIN21"
EVENT_TICKER = "KXNFLSPREAD-26NOV15MINGB"


def main() -> None:
    """Find the series ticker and inspect recent price observations."""
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        # Step 1: Look up the event's series identifier.
        event_response = client.get(f"/events/{EVENT_TICKER}")

        print(f"Event HTTP status: {event_response.status_code}")

        if event_response.is_error:
            print(event_response.text)
            return

        event = event_response.json()["event"]
        series_ticker = event["series_ticker"]

        print(f"Series ticker: {series_ticker}")

        # Step 2: Request one-minute candlesticks.
        # Use a small interval to stay below the 5,000-candle limit.
        now = datetime.now(UTC)
        start = now - timedelta(days=2)

        response = client.get(
            f"/series/{series_ticker}/markets/{TICKER}/candlesticks",
            params={
                "start_ts": int(start.timestamp()),
                "end_ts": int(now.timestamp()),
                "period_interval": 1,
            },
        )

        print(f"Candlestick HTTP status: {response.status_code}")

        if response.is_error:
            print(response.text)
            return

        payload = response.json()
        candles = payload.get("candlesticks", [])

        print(f"Candlesticks returned: {len(candles)}")

        if candles:
            print("\nFirst candle:")
            pprint(candles[0])

            print("\nLast candle:")
            pprint(candles[-1])


if __name__ == "__main__":
    main()
