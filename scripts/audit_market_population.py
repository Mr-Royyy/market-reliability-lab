"""Audit the composition of settled Kalshi markets.

Inputs:
    Paginated settled-market metadata from Kalshi.

Outputs:
    Counts by duration, result, and ticker prefix.

Side effects:
    Makes read-only API requests. Does not write files.
"""

from collections import Counter
from datetime import datetime

from market_reliability.data.kalshi_client import KalshiClient

PAGES = 5
PAGE_SIZE = 200


def parse_time(value: str | None) -> datetime | None:
    """Parse a timezone-aware ISO timestamp."""
    if not value:
        return None

    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone.")

    return parsed


def classify_duration(hours: float) -> str:
    """Assign a market lifetime to a duration bucket."""
    if hours < 1:
        return "<1 hour"
    if hours < 24:
        return "1-24 hours"
    if hours < 168:
        return "1-7 days"
    if hours < 720:
        return "7-30 days"
    return "30+ days"


def main() -> None:
    """Audit a bounded sample of settled-market pages."""
    api = KalshiClient()
    cursor = None

    durations = Counter()
    results = Counter()
    series = Counter()
    invalid = Counter()
    total = 0

    for page_number in range(1, PAGES + 1):
        response = api.get_markets(
            status="settled",
            limit=PAGE_SIZE,
            mve_filter="exclude",
            cursor=cursor,
        )

        markets = response.get("markets", [])
        total += len(markets)

        for market in markets:
            results[market.get("result", "missing")] += 1

            ticker = market.get("ticker", "")
            series[ticker.split("-")[0]] += 1

            try:
                opened = parse_time(market.get("open_time"))
                closed = parse_time(market.get("close_time"))

                if opened is None or closed is None:
                    invalid["missing_times"] += 1
                    continue

                hours = (closed - opened).total_seconds() / 3600

                if hours <= 0:
                    invalid["invalid_duration"] += 1
                    continue

                durations[classify_duration(hours)] += 1

            except ValueError:
                invalid["invalid_timestamp"] += 1

        print(f"Page {page_number}: {len(markets)} markets, cumulative {total}")

        cursor = response.get("cursor")

        if not cursor or not markets:
            break

    print("\nMARKET POPULATION AUDIT")
    print(f"Total contracts: {total}")

    print("\nMARKET LIFETIMES")
    for bucket in [
        "<1 hour",
        "1-24 hours",
        "1-7 days",
        "7-30 days",
        "30+ days",
    ]:
        print(f"{bucket}: {durations[bucket]}")

    print("\nRESULT DISTRIBUTION")
    for result, count in results.most_common():
        print(f"{result}: {count}")

    print("\nTOP 15 SERIES")
    for ticker, count in series.most_common(15):
        print(f"{ticker}: {count}")

    print("\nINVALID OR MISSING METADATA")
    print(dict(invalid))


if __name__ == "__main__":
    main()
