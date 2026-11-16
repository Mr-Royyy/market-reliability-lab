"""Inventory historical rainfall contracts and their settlement outcomes."""

from pathlib import Path

import pandas as pd

from market_reliability.data.candlestick_client import create_kalshi_http_client
from market_reliability.data.http_retry import get_with_retry

SERIES = (
    "KXRAINMIAM",
    "KXRAINNYCM",
    "KXRAINAUSM",
    "KXRAINHOUM",
    "KXRAINSEAM",
    "KXRAINLAXM",
    "KXRAINSFOM",
    "KXRAINDALM",
    "KXRAINDENM",
    "KXRAINCHIM",
)

MONTHS = ("26JUN", "26JUL", "26AUG", "26SEP", "26OCT")
OUTPUT = Path("data/processed/rainfall_outcome_inventory.csv")


def fetch_markets(client, series):
    markets = []
    cursor = None

    while True:
        params = {
            "series_ticker": series,
            "limit": 200,
            "mve_filter": "exclude",
        }

        if cursor:
            params["cursor"] = cursor

        response = get_with_retry(client, "/markets", params=params)
        response.raise_for_status()

        payload = response.json()
        markets.extend(payload.get("markets", []))

        cursor = payload.get("cursor")

        if not cursor:
            break

    return markets


def main():
    rows = []

    with create_kalshi_http_client() as client:
        for series in SERIES:
            markets = fetch_markets(client, series)

            selected = [
                market
                for market in markets
                if market.get("event_ticker") in {f"{series}-{month}" for month in MONTHS}
            ]

            print(f"{series}: {len(selected)} contracts")

            for market in selected:
                result = market.get("result", "")
                status = market.get("status", "")

                rows.append(
                    {
                        "series": series,
                        "event": market["event_ticker"],
                        "market": market["ticker"],
                        "status": status,
                        "result": result,
                        "resolved": (
                            status in {"settled", "finalized"} and result in {"yes", "no"}
                        ),
                        "open_time": market.get("open_time"),
                        "close_time": market.get("close_time"),
                        "settlement_ts": market.get("settlement_ts"),
                        "rules": market.get("rules_primary"),
                    }
                )

    df = pd.DataFrame(rows)

    if df.empty:
        print("No historical contracts found.")
        return

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)

    print("\nOUTCOME SUMMARY")
    print(
        df.groupby("event")
        .agg(
            contracts=("market", "size"),
            resolved=("resolved", "sum"),
            yes=("result", lambda x: (x == "yes").sum()),
            no=("result", lambda x: (x == "no").sum()),
        )
        .to_string()
    )

    print("\nTOTAL")
    print(f"Contracts: {len(df)}")
    print(f"Events: {df['event'].nunique()}")
    print(f"Resolved: {int(df['resolved'].sum())}")
    print(f"Unresolved: {int((~df['resolved']).sum())}")
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
