"""Discover settled monthly rainfall market populations on Kalshi.

Read-only API requests. Prints series-level and event-level summaries.
Does not download historical candlesticks or write files.
"""

import re

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

KNOWN_SERIES = {"KXRAINAUSM", "KXRAINMIAM"}
MAX_CANDIDATES = 60

# Prefer rainfall series with monthly wording in catalog metadata.
RAIN_PATTERN = re.compile(r"rain|precipitation", re.IGNORECASE)
MONTH_PATTERN = re.compile(r"month|monthly", re.IGNORECASE)


def discover_candidates(client: httpx.Client) -> list[dict]:
    response = get_with_retry(
        client,
        "/series",
        params={"limit": 200},
    )

    response.raise_for_status()
    catalog = response.json().get("series", [])

    candidates = []

    for item in catalog:
        ticker = item.get("ticker", "")
        title = item.get("title") or ""
        category = item.get("category") or ""
        text = f"{ticker} {title}"

        if category != "Climate and Weather":
            continue

        if not RAIN_PATTERN.search(text):
            continue

        if not (MONTH_PATTERN.search(text) or ticker in KNOWN_SERIES or ticker.endswith("M")):
            continue

        candidates.append(
            {
                "series": ticker,
                "title": title,
                "category": category,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["series"] not in KNOWN_SERIES,
            item["series"],
        )
    )

    return candidates[:MAX_CANDIDATES]


def inspect_series(client: httpx.Client, candidate: dict) -> dict:
    ticker = candidate["series"]

    response = get_with_retry(
        client,
        "/markets",
        params={
            "series_ticker": ticker,
            "status": "settled",
            "limit": 200,
            "mve_filter": "exclude",
        },
    )

    response.raise_for_status()
    payload = response.json()
    markets = payload.get("markets", [])

    events = {market.get("event_ticker") for market in markets if market.get("event_ticker")}

    eligible_7d = 0
    eligible_14d = 0

    for market in markets:
        opened = pd.to_datetime(
            market.get("open_time"),
            utc=True,
            errors="coerce",
        )
        closed = pd.to_datetime(
            market.get("close_time"),
            utc=True,
            errors="coerce",
        )

        if pd.isna(opened) or pd.isna(closed):
            continue

        lifetime = closed - opened

        eligible_7d += lifetime >= pd.Timedelta(days=7)
        eligible_14d += lifetime >= pd.Timedelta(days=14)

    return {
        "series": ticker,
        "title": candidate["title"],
        "contracts": len(markets),
        "events": len(events),
        "eligible_7d": eligible_7d,
        "eligible_14d": eligible_14d,
        "more_pages": bool(payload.get("cursor")),
    }


def main() -> None:
    with create_kalshi_http_client() as client:
        candidates = discover_candidates(client)

        print(f"Rainfall series candidates: {len(candidates)}")

        if not candidates:
            print("No candidates found in the returned catalog.")
            return

        results = []

        for index, candidate in enumerate(candidates, start=1):
            try:
                result = inspect_series(client, candidate)
                results.append(result)
            except (
                httpx.HTTPError,
                ValueError,
                KeyError,
                TypeError,
            ) as exc:
                print(f"Failed {candidate['series']}: {exc}")

            if index % 10 == 0:
                print(f"Inspected {index}/{len(candidates)} series")

    df = pd.DataFrame(results)

    if df.empty:
        print("No series successfully inspected.")
        return

    active = df.loc[df["contracts"] > 0].copy()

    print("\nSERIES WITH SETTLED CONTRACTS")

    if active.empty:
        print("None found.")
        return

    active = active.sort_values(
        ["events", "eligible_7d", "contracts"],
        ascending=False,
    )

    print(
        active[
            [
                "series",
                "contracts",
                "events",
                "eligible_7d",
                "eligible_14d",
                "more_pages",
                "title",
            ]
        ].to_string(index=False)
    )

    print("\nPOPULATION SUMMARY")
    print(f"Series with settled contracts: {len(active)}")
    print(f"Observed event IDs: {active['events'].sum()}")
    print(f"Contracts inspected: {active['contracts'].sum()}")
    print(f"Seven-day eligible contracts: {active['eligible_7d'].sum()}")
    print(f"Series requiring pagination: {active['more_pages'].sum()}")

    print(
        "\nNote: these counts describe returned market pages, "
        "not necessarily complete historical populations."
    )


if __name__ == "__main__":
    main()
