"""Compare historical quote availability across predetermined UTC hours.

Read-only API requests. Does not write files.
"""

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry
from market_reliability.data.rainfall_schedule import (
    observation_checkpoints,
)

SERIES = "KXRAINMIAM"
EVENT = "KXRAINMIAM-26OCT"

HOURS_UTC = (0, 12, 18)
LOOKBACK_HOURS = 24

POLICIES = {
    "strict": (5, 0.05),
    "moderate": (60, 0.10),
    "exploratory": (1440, 0.20),
}


def audit_market_hour(
    client: httpx.Client,
    market: dict,
    checkpoint_name: str,
    cutoff: pd.Timestamp,
) -> dict:
    """Inspect the latest valid historical quote before a cutoff."""
    opened = pd.to_datetime(market["open_time"], utc=True)
    closed = pd.to_datetime(market["close_time"], utc=True)

    eligible = bool(opened <= cutoff < closed)

    row = {
        "market": market["ticker"],
        "checkpoint": checkpoint_name,
        "hour_utc": cutoff.hour,
        "eligible": eligible,
        "has_quote": False,
        "age_minutes": float("nan"),
        "midpoint": float("nan"),
        "spread": float("nan"),
        "error": False,
    }

    if not eligible:
        return row

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
    age_minutes = (cutoff - latest["timestamp_utc"]).total_seconds() / 60

    if age_minutes < 0:
        raise ValueError("Historical quote occurs after cutoff")

    row.update(
        {
            "has_quote": True,
            "age_minutes": age_minutes,
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
            raise RuntimeError("Market pagination required")

        markets = [
            market for market in payload.get("markets", []) if market.get("event_ticker") == EVENT
        ]

        checkpoints = observation_checkpoints(EVENT)

        print(f"Event: {EVENT}")
        print(f"Contracts: {len(markets)}")

        for market in markets:
            for checkpoint_name, base_time in checkpoints.items():
                for hour in HOURS_UTC:
                    cutoff = base_time + pd.Timedelta(hours=hour)

                    try:
                        row = audit_market_hour(
                            client,
                            market,
                            checkpoint_name,
                            cutoff,
                        )
                    except (
                        httpx.HTTPError,
                        ValueError,
                        KeyError,
                        TypeError,
                    ) as exc:
                        print(f"ERROR {market['ticker']} {checkpoint_name} {hour:02d}:00: {exc}")
                        row = {
                            "market": market["ticker"],
                            "checkpoint": checkpoint_name,
                            "hour_utc": hour,
                            "eligible": False,
                            "has_quote": False,
                            "age_minutes": float("nan"),
                            "midpoint": float("nan"),
                            "spread": float("nan"),
                            "error": True,
                        }

                    rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        print("No observations")
        return

    for name, (max_age, max_spread) in POLICIES.items():
        df[name] = (
            df["eligible"]
            & ~df["error"]
            & df["has_quote"]
            & (df["age_minutes"] <= max_age)
            & (df["spread"] <= max_spread)
        )

    summary = []

    for (checkpoint, hour), group in df.groupby(
        ["checkpoint", "hour_utc"],
        sort=False,
    ):
        eligible = group.loc[group["eligible"]]

        result = {
            "checkpoint": checkpoint,
            "hour_utc": hour,
            "eligible": len(eligible),
            "quoted": int(eligible["has_quote"].sum()),
            "errors": int(group["error"].sum()),
        }

        for policy in POLICIES:
            accepted = eligible.loc[eligible[policy]]
            result[policy] = len(accepted)
            result[f"{policy}_uncertain"] = int(accepted["midpoint"].between(0.2, 0.8).sum())

        summary.append(result)

    print("\nCHECKPOINT-HOUR SUMMARY")
    print(pd.DataFrame(summary).to_string(index=False))

    print("\nOVERALL")
    print(f"Scheduled rows: {len(df)}")
    print(f"Request errors: {int(df['error'].sum())}")

    print("\nMODERATE COVERAGE BY HOUR")

    for hour in HOURS_UTC:
        group = df.loc[(df["hour_utc"] == hour) & df["eligible"]]

        accepted = int(group["moderate"].sum())
        total = len(group)

        coverage = 100 * accepted / total if total else 0

        print(f"{hour:02d}:00 UTC: {accepted}/{total} ({coverage:.1f}%)")


if __name__ == "__main__":
    main()
