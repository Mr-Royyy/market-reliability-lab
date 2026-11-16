"""Audit seven-day historical quote quality across rainfall cities.

Read-only API requests. No files written.
"""

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
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

HORIZON_DAYS = 7
LOOKBACK_HOURS = 24

POLICIES = {
    "strict": (5, 0.05),
    "moderate": (60, 0.10),
    "exploratory": (1440, 0.20),
}


def inspect_contract(
    client: httpx.Client,
    series: str,
    market: dict,
) -> dict:
    ticker = market["ticker"]
    opened = pd.to_datetime(market["open_time"], utc=True)
    closed = pd.to_datetime(market["close_time"], utc=True)
    cutoff = closed - pd.Timedelta(days=HORIZON_DAYS)

    row = {
        "series": series,
        "event": market["event_ticker"],
        "market": ticker,
        "eligible": opened <= cutoff < closed,
        "has_quote": False,
        "age_minutes": float("nan"),
        "midpoint": float("nan"),
        "spread": float("nan"),
        "error": False,
    }

    if not row["eligible"]:
        return row

    start = max(opened, cutoff - pd.Timedelta(hours=LOOKBACK_HOURS))

    candles = fetch_candlestick_history(
        client=client,
        series_ticker=series,
        market_ticker=ticker,
        start=start,
        end=cutoff,
    )

    df = build_candle_dataframe(ticker, candles)

    if df.empty:
        return row

    valid = df.loc[
        (df["timestamp_utc"] >= start) & (df["timestamp_utc"] <= cutoff) & df["has_valid_quotes"]
    ].sort_values("timestamp_utc")

    if valid.empty:
        return row

    latest = valid.iloc[-1]

    row.update(
        {
            "has_quote": True,
            "age_minutes": (cutoff - latest["timestamp_utc"]).total_seconds() / 60,
            "midpoint": float(latest["midpoint"]),
            "spread": float(latest["spread"]),
        }
    )

    return row


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

            payload = response.json()
            markets = payload.get("markets", [])

            if payload.get("cursor"):
                print(f"WARNING: {series} has additional pages")

            print(f"\n{series}: {len(markets)} contracts")

            for index, market in enumerate(markets, start=1):
                try:
                    rows.append(inspect_contract(client, series, market))
                except (
                    httpx.HTTPError,
                    ValueError,
                    KeyError,
                    TypeError,
                ) as exc:
                    print(f"ERROR {market['ticker']}: {exc}")
                    rows.append(
                        {
                            "series": series,
                            "event": market["event_ticker"],
                            "market": market["ticker"],
                            "eligible": False,
                            "has_quote": False,
                            "age_minutes": float("nan"),
                            "midpoint": float("nan"),
                            "spread": float("nan"),
                            "error": True,
                        }
                    )

                if index % 10 == 0:
                    print(f"Processed {index}/{len(markets)}")

    df = pd.DataFrame(rows)

    if df.empty:
        print("No observations.")
        return

    for name, (max_age, max_spread) in POLICIES.items():
        df[name] = (
            df["eligible"]
            & df["has_quote"]
            & (df["age_minutes"] <= max_age)
            & (df["spread"] <= max_spread)
        )

    print("\nSERIES SUMMARY")

    summaries = []

    for series, group in df.groupby("series"):
        eligible = group.loc[group["eligible"]]

        result = {
            "series": series,
            "contracts": len(group),
            "eligible": len(eligible),
            "quoted": int(eligible["has_quote"].sum()),
            "events": eligible["event"].nunique(),
            "errors": int(group["error"].sum()),
        }

        for policy in POLICIES:
            accepted = eligible.loc[eligible[policy]]
            result[f"{policy}_contracts"] = len(accepted)
            result[f"{policy}_events"] = accepted["event"].nunique()
            result[f"{policy}_uncertain"] = int(accepted["midpoint"].between(0.2, 0.8).sum())

        summaries.append(result)

    print(pd.DataFrame(summaries).to_string(index=False))

    print("\nOVERALL SUMMARY")

    eligible = df.loc[df["eligible"]]

    print(f"Contracts inspected: {len(df)}")
    print(f"Eligible contracts: {len(eligible)}")
    print(f"Quotes within 24 hours: {eligible['has_quote'].sum()}")
    print(f"Eligible event IDs: {eligible['event'].nunique()}")
    print(f"Request errors: {df['error'].sum()}")

    for policy in POLICIES:
        accepted = eligible.loc[eligible[policy]]
        uncertain = accepted["midpoint"].between(0.2, 0.8)

        print(
            f"{policy}: "
            f"{len(accepted)} contracts, "
            f"{accepted['event'].nunique()} events, "
            f"{uncertain.sum()} uncertain snapshots"
        )


if __name__ == "__main__":
    main()
