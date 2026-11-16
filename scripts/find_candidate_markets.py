"""Diagnose why Kalshi markets fail our initial selection criteria."""

from datetime import datetime

from market_reliability.data.kalshi_client import KalshiClient


def parse_time(value: str) -> datetime:
    """Convert an ISO timestamp into a timezone-aware datetime."""
    return datetime.fromisoformat(value)


def main() -> None:
    """Examine market activity and duration across several pages."""
    client = KalshiClient()

    cursor = None
    max_pages = 10

    counts = {
        "total": 0,
        "binary_result": 0,
        "positive_volume": 0,
        "duration_24h": 0,
        "both_conditions": 0,
        "invalid_timestamps": 0,
    }

    highest_volume = []
    longest_duration = []

    for page in range(1, max_pages + 1):
        payload = client.get_markets(
            status="settled",
            limit=200,
            cursor=cursor,
        )

        markets = payload["markets"]

        for market in markets:
            counts["total"] += 1

            if market.get("result") not in {"yes", "no"}:
                continue

            counts["binary_result"] += 1

            try:
                volume = float(market.get("volume_fp") or 0)
                opened = parse_time(market["open_time"])
                closed = parse_time(market["close_time"])
            except (ValueError, TypeError, KeyError, AttributeError):
                counts["invalid_timestamps"] += 1
                continue

            duration = (closed - opened).total_seconds() / 3600

            if volume > 0:
                counts["positive_volume"] += 1

            if duration >= 24:
                counts["duration_24h"] += 1

            if volume > 0 and duration >= 24:
                counts["both_conditions"] += 1

            record = {
                "ticker": market["ticker"],
                "title": market.get("title"),
                "volume": volume,
                "hours": duration,
            }

            highest_volume.append(record)
            longest_duration.append(record)

        print(f"Processed page {page}: {len(markets)} markets")

        next_cursor = payload.get("cursor")

        if not next_cursor or not markets or next_cursor == cursor:
            break

        cursor = next_cursor

    print("\nDIAGNOSTIC COUNTS")
    for name, value in counts.items():
        print(f"{name}: {value}")

    print("\nTOP 5 BY VOLUME")
    for market in sorted(
        highest_volume,
        key=lambda item: item["volume"],
        reverse=True,
    )[:5]:
        print(market)

    print("\nTOP 5 BY DURATION")
    for market in sorted(
        longest_duration,
        key=lambda item: item["hours"],
        reverse=True,
    )[:5]:
        print(market)


if __name__ == "__main__":
    main()
