"""Audit fixed calendar checkpoints across October 2026 rainfall markets.

Read-only Kalshi API requests. Produces a local CSV with one row per
contract, checkpoint, and UTC observation hour.
"""

import argparse
from pathlib import Path

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry
from market_reliability.data.rainfall_schedule import observation_checkpoints

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

MONTH_OUTPUTS = {
    "26SEP": "september_calendar_audit.csv",
    "26OCT": "october_calendar_audit.csv",
}
HOURS_UTC = (0, 12, 18)
LOOKBACK_HOURS = 24

POLICIES = {
    "strict": (5, 0.05),
    "moderate": (60, 0.10),
    "exploratory": (1440, 0.20),
}

OUTPUT = Path("data/processed/september_calendar_audit.csv")


def classify_market(
    opened: pd.Timestamp,
    closed: pd.Timestamp,
    cutoff: pd.Timestamp,
    now: pd.Timestamp,
) -> str:
    if cutoff > now:
        return "not_yet_observed"
    if cutoff < opened:
        return "not_yet_open"
    if cutoff >= closed:
        return "already_closed"
    return "eligible"


def fetch_series_markets(client: httpx.Client, series: str) -> list[dict]:
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

        response = get_with_retry(
            client,
            "/markets",
            params=params,
        )
        response.raise_for_status()
        payload = response.json()
        markets.extend(payload.get("markets", []))

        cursor = payload.get("cursor")
        if not cursor:
            break

    return markets


def audit_observation(
    client: httpx.Client,
    series: str,
    market: dict,
    checkpoint: str,
    cutoff: pd.Timestamp,
    now: pd.Timestamp,
) -> dict:
    opened = pd.to_datetime(market["open_time"], utc=True)
    closed = pd.to_datetime(market["close_time"], utc=True)
    status = classify_market(opened, closed, cutoff, now)

    row = {
        "series": series,
        "event": market["event_ticker"],
        "market": market["ticker"],
        "checkpoint": checkpoint,
        "hour_utc": cutoff.hour,
        "timestamp_utc": cutoff,
        "open_time_utc": opened,
        "close_time_utc": closed,
        "eligibility_status": status,
        "has_quote": False,
        "quote_timestamp_utc": pd.NaT,
        "age_minutes": float("nan"),
        "midpoint": float("nan"),
        "spread": float("nan"),
        "error": False,
    }

    if status != "eligible":
        return row

    start = max(
        opened,
        cutoff - pd.Timedelta(hours=LOOKBACK_HOURS),
    )

    try:
        candles = fetch_candlestick_history(
            client=client,
            series_ticker=series,
            market_ticker=market["ticker"],
            start=start,
            end=cutoff,
        )

        df = build_candle_dataframe(market["ticker"], candles)

        if df.empty:
            return row

        valid = df.loc[
            df["has_valid_quotes"]
            & (df["timestamp_utc"] >= start)
            & (df["timestamp_utc"] <= cutoff)
        ].sort_values("timestamp_utc")

        if valid.empty:
            return row

        latest = valid.iloc[-1]
        age = (cutoff - latest["timestamp_utc"]).total_seconds() / 60

        if age < 0:
            raise ValueError("Quote timestamp exceeds observation cutoff")

        row.update(
            {
                "has_quote": True,
                "quote_timestamp_utc": latest["timestamp_utc"],
                "age_minutes": age,
                "midpoint": float(latest["midpoint"]),
                "spread": float(latest["spread"]),
            }
        )

    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        row["error"] = True
        row["error_message"] = str(exc)

    return row


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit fixed rainfall calendar checkpoints."
    )
    parser.add_argument(
        "--month",
        choices=MONTH_OUTPUTS,
        required=True,
        help="Rainfall event month to audit.",
    )
    args = parser.parse_args()

    month_suffix = args.month
    output = Path("data/processed") / MONTH_OUTPUTS[month_suffix]

    rows = []
    now = pd.Timestamp.now(tz="UTC")

    with create_kalshi_http_client() as client:
        for series in SERIES:
            event = f"{series}-{month_suffix}"
            markets = [
                market
                for market in fetch_series_markets(client, series)
                if market.get("event_ticker") == event
            ]

            print(f"{event}: {len(markets)} contracts")

            checkpoints = observation_checkpoints(event)

            for market in markets:
                for checkpoint, base_time in checkpoints.items():
                    for hour in HOURS_UTC:
                        cutoff = base_time + pd.Timedelta(hours=hour)
                        rows.append(
                            audit_observation(
                                client,
                                series,
                                market,
                                checkpoint,
                                cutoff,
                                now,
                            )
                        )

    df = pd.DataFrame(rows)

    if df.empty:
        print("No observations returned.")
        return

    eligible = df["eligibility_status"].eq("eligible")

    for policy, (max_age, max_spread) in POLICIES.items():
        df[policy] = (
            eligible
            & ~df["error"]
            & df["has_quote"]
            & df["age_minutes"].le(max_age)
            & df["spread"].le(max_spread)
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)

    print("\nELIGIBILITY STATUS")
    print(df["eligibility_status"].value_counts().to_string())

    summary = (
        df.groupby(["checkpoint", "hour_utc"], sort=False)
        .agg(
            eligible=("eligibility_status", lambda x: (x == "eligible").sum()),
            quoted=("has_quote", "sum"),
            errors=("error", "sum"),
            strict=("strict", "sum"),
            moderate=("moderate", "sum"),
            exploratory=("exploratory", "sum"),
        )
        .reset_index()
    )

    print("\nCHECKPOINT SUMMARY")
    print(summary.to_string(index=False))

    print("\nMODERATE COVERAGE BY SERIES")
    series_summary = (
        df.loc[eligible & df["hour_utc"].eq(18)]
        .groupby("series")
        .agg(
            eligible=("market", "size"),
            moderate=("moderate", "sum"),
            quoted=("has_quote", "sum"),
        )
        .reset_index()
    )
    print(series_summary.to_string(index=False))

    print("\nINDEPENDENT EVENT COUNTS")
    for hour in HOURS_UTC:
        subset = df.loc[eligible & df["hour_utc"].eq(hour) & df["moderate"]]
        print(
            f"{hour:02d}:00 UTC: "
            f"{subset['event'].nunique()} city-month events "
            f"with at least one moderate-quality quote"
        )

    print(f"\nSaved: {output}")


if __name__ == "__main__":
    main()
