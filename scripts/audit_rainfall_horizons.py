"""Audit eligible forecast horizons for monthly rainfall contracts.

Inputs:
    Settled Kalshi rainfall contracts.

Outputs:
    Contract and event counts eligible for each forecast horizon.

Side effects:
    Read-only API requests.
"""

import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

SERIES = ("KXRAINAUSM", "KXRAINMIAM")
HORIZON_DAYS = (1, 7, 14)


def main() -> None:
    rows = []

    with create_kalshi_http_client() as client:
        for series in SERIES:
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

                for days in HORIZON_DAYS:
                    cutoff = closed - pd.Timedelta(days=days)

                    rows.append(
                        {
                            "series": series,
                            "event": market.get("event_ticker"),
                            "market": market["ticker"],
                            "horizon_days": days,
                            "eligible": opened <= cutoff < closed,
                        }
                    )

    df = pd.DataFrame(rows)

    print("\nHORIZON ELIGIBILITY")
    print(
        df.groupby(["series", "horizon_days"])
        .agg(
            contracts=("market", "nunique"),
            eligible_contracts=("eligible", "sum"),
        )
        .to_string()
    )

    print("\nELIGIBLE EVENTS")
    eligible = df.loc[df["eligible"]]

    print(eligible.groupby(["series", "horizon_days"])["event"].nunique().to_string())


if __name__ == "__main__":
    main()
