"""Inspect Kalshi's boundary between recent and archived market data."""

from pprint import pprint

import httpx

from market_reliability.data.kalshi_client import BASE_URL


def main() -> None:
    """Retrieve the historical-data cutoff without modifying anything."""
    with httpx.Client(timeout=20.0) as client:
        response = client.get(f"{BASE_URL}/historical/cutoff")

        print(f"HTTP status: {response.status_code}")

        if response.is_error:
            print(response.text)
            return

        print("\nHistorical cutoff response:")
        pprint(response.json())


if __name__ == "__main__":
    main()
