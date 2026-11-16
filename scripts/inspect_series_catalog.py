"""Inspect Kalshi's public series catalog.

Inputs:
    Public series metadata from Kalshi.

Outputs:
    Series count, categories, and example metadata.

Side effects:
    Read-only API request. No files written.
"""

from collections import Counter

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)


def main() -> None:
    """Inspect the structure and composition of the series catalog."""
    with create_kalshi_http_client() as client:
        response = client.get(
            "/series",
            params={"limit": 200},
        )
        response.raise_for_status()
        payload = response.json()

    print("\nTOP-LEVEL RESPONSE KEYS")
    print(list(payload))

    series = payload.get("series", [])

    print(f"\nSERIES RETURNED: {len(series)}")
    print(f"CURSOR PRESENT: {bool(payload.get('cursor'))}")

    categories = Counter(item.get("category", "missing") for item in series)

    print("\nCATEGORY DISTRIBUTION")
    for category, count in categories.most_common():
        print(f"{category}: {count}")

    print("\nEXAMPLE SERIES")
    for item in series[:12]:
        print(
            {
                "ticker": item.get("ticker"),
                "title": item.get("title"),
                "category": item.get("category"),
                "frequency": item.get("frequency"),
                "contract_terms_url": item.get("contract_terms_url"),
            }
        )

    if series:
        print("\nFIRST SERIES — ALL AVAILABLE FIELDS")
        print(sorted(series[0]))


if __name__ == "__main__":
    main()
