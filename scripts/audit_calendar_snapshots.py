"""Audit calendar-anchored rainfall snapshots for one event.

Read-only Kalshi requests. No files written.
"""

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry
from market_reliability.data.rainfall_schedule import schedule_contract

SERIES = "KXRAINMIAM"
EVENT = "KXRAINMIAM-26NOV"
LOOKBACK_HOURS = 24

POLICIES = {
    "strict": (5, 0.05),
    "moderate": (60, 0.10),
    "exploratory": (1440, 0.20),
}


def audit_checkpoint(
    client: httpx.Client,
    market: dict,
    scheduled: dict,
) -> dict:
    """Retrieve the latest valid quote at or before a checkpoint."""
    row = {
        **scheduled,
        "has_quote": False,
        "quote_timestamp_utc": pd.NaT,
        "age_minutes": float("nan"),
        "midpoint": float("nan"),
        "spread": float("nan"),
        "error": False,
    }

    if not row["eligible"]:
        return row

    cutoff = scheduled["timestamp_utc"]
    opened = pd.to_datetime(market["open_time"], utc=True)
    start = max(
        opened,
        cutoff - pd.Timedelta(hours=LOOKBACK_HOURS),
    )

    candles = fetch_candlestick_history(
        client=client,
        series_ticker=SERIES,
        market_ticker=market["ticker"],
        start=start,
        end=cutoff,
    )

    df = build_candle_dataframe(market["ticker"], candles)

    if df.empty:
        return row

    valid = df.loc[
        df["has_valid_quotes"] & (df["timestamp_utc"] >= start) & (df["timestamp_utc"] <= cutoff)
    ].sort_values("timestamp_utc")

    if valid.empty:
        return row

    latest = valid.iloc[-1]
    quote_time = latest["timestamp_utc"]

    row.update(
        {
            "has_quote": True,
            "quote_timestamp_utc": quote_time,
            "age_minutes": (cutoff - quote_time).total_seconds() / 60,
            "midpoint": float(latest["midpoint"]),
            "spread": float(latest["spread"]),
        }
    )

    return row


def main() -> None:
    rows = []

    with create_kalshi_http_client() as client:
        response = get_with_retry(
            client,
            "/markets",
            params={
                "series_ticker": SERIES,
                "limit": 200,
                "mve_filter": "exclude",
            },
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("cursor"):
            raise RuntimeError("Market pagination required; refusing partial audit.")

        markets = [
            market for market in payload.get("markets", []) if market.get("event_ticker") == EVENT
        ]

        print(f"Event: {EVENT}")
        print(f"Contracts found: {len(markets)}")

        for market in markets:
            for scheduled in schedule_contract(market):
                try:
                    row = audit_checkpoint(
                        client,
                        market,
                        scheduled,
                    )
                except (
                    httpx.HTTPError,
                    ValueError,
                    KeyError,
                    TypeError,
                ) as exc:
                    print(f"ERROR {market['ticker']} {scheduled['checkpoint']}: {exc}")
                    row = {
                        **scheduled,
                        "has_quote": False,
                        "quote_timestamp_utc": pd.NaT,
                        "age_minutes": float("nan"),
                        "midpoint": float("nan"),
                        "spread": float("nan"),
                        "error": True,
                    }

                rows.append(row)

    if not rows:
        print("No matching contracts found.")
        return

    df = pd.DataFrame(rows)

    # Keep API errors separate from eligibility.
    for policy, (max_age, max_spread) in POLICIES.items():
        df[policy] = (
            df["eligible"]
            & ~df["error"]
            & df["has_quote"]
            & (df["age_minutes"] <= max_age)
            & (df["spread"] <= max_spread)
        )

    # No historical quote may occur after its observation checkpoint.
    quoted = df.loc[df["has_quote"]]
    assert (quoted["quote_timestamp_utc"] <= quoted["timestamp_utc"]).all()

    print("\nCHECKPOINT SUMMARY")

    summary = []

    for checkpoint, group in df.groupby("checkpoint", sort=False):
        eligible = group.loc[group["eligible"]]

        result = {
            "checkpoint": checkpoint,
            "eligible": len(eligible),
            "quoted": int(eligible["has_quote"].sum()),
            "errors": int(eligible["error"].sum()),
        }

        for policy in POLICIES:
            accepted = eligible.loc[eligible[policy]]
            result[policy] = len(accepted)
            result[f"{policy}_uncertain"] = int(accepted["midpoint"].between(0.2, 0.8).sum())

        summary.append(result)

    print(pd.DataFrame(summary).to_string(index=False))

    print("\nOVERALL")
    print(f"Scheduled rows: {len(df)}")
    print(f"Eligible rows: {int(df['eligible'].sum())}")
    print(f"Request errors: {int(df['error'].sum())}")
    print(f"Quoted rows: {int((df['eligible'] & df['has_quote']).sum())}")

    print("\nSAMPLE ROWS")
    print(
        df[
            [
                "market",
                "checkpoint",
                "eligible",
                "has_quote",
                "age_minutes",
                "spread",
                "moderate",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
