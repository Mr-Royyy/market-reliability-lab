"""Audit historical quote freshness at fixed rainfall forecast horizons.

Fetches up to 24 hours of preceding candles per eligible cutoff.
Read-only: prints summaries without writing files.
"""

import httpx
import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry

SERIES = ("KXRAINAUSM", "KXRAINMIAM")
HORIZON_DAYS = (1, 7, 14)
LOOKBACK_HOURS = 24


def audit_cutoff(
    client: httpx.Client,
    series: str,
    market: dict,
    days: int,
) -> dict:
    """Find the freshest valid quote at or before one cutoff."""
    ticker = market["ticker"]
    opened = pd.Timestamp(market["open_time"])
    closed = pd.Timestamp(market["close_time"])
    cutoff = closed - pd.Timedelta(days=days)

    row = {
        "series": series,
        "event": market["event_ticker"],
        "market": ticker,
        "horizon_days": days,
        "eligible": opened <= cutoff < closed,
        "has_quote": False,
        "quote_age_minutes": float("nan"),
        "midpoint": float("nan"),
        "spread": float("nan"),
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

    # Only use candle periods ending at or before the cutoff.
    valid = df.loc[
        (df["timestamp_utc"] >= start) & (df["timestamp_utc"] <= cutoff) & df["has_valid_quotes"]
    ].sort_values("timestamp_utc")

    if valid.empty:
        return row

    latest = valid.iloc[-1]
    age = (cutoff - latest["timestamp_utc"]).total_seconds() / 60

    row.update(
        {
            "has_quote": True,
            "quote_age_minutes": age,
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

            markets = response.json().get("markets", [])

            print(f"\n{series}: {len(markets)} contracts")

            for index, market in enumerate(markets, start=1):
                for days in HORIZON_DAYS:
                    try:
                        row = audit_cutoff(client, series, market, days)
                        rows.append(row)
                    except (
                        httpx.HTTPError,
                        ValueError,
                        KeyError,
                        TypeError,
                    ) as exc:
                        print(f"Failed {market['ticker']}, {days}d: {exc}")

                if index % 10 == 0:
                    print(f"Processed {index}/{len(markets)} contracts")

    if not rows:
        print("No results.")
        return

    df = pd.DataFrame(rows)

    print("\nFRESHNESS COVERAGE")
    summary = []

    for (series, days), group in df.groupby(["series", "horizon_days"]):
        eligible = group.loc[group["eligible"]]
        quoted = eligible.loc[eligible["has_quote"]]

        summary.append(
            {
                "series": series,
                "horizon_days": days,
                "eligible": len(eligible),
                "any_quote_24h": len(quoted),
                "within_5m": int((quoted["quote_age_minutes"] <= 5).sum()),
                "within_60m": int((quoted["quote_age_minutes"] <= 60).sum()),
                "within_24h": int((quoted["quote_age_minutes"] <= 1440).sum()),
            }
        )

    print(pd.DataFrame(summary).to_string(index=False))

    quoted = df.loc[df["has_quote"]]

    print("\nQUOTE AGE DISTRIBUTION (MINUTES)")
    if quoted.empty:
        print("No valid quotes found.")
    else:
        print(
            quoted.groupby(["series", "horizon_days"])["quote_age_minutes"]
            .describe(percentiles=[0.25, 0.5, 0.75, 0.9])
            .to_string()
        )

        print("\nSPREAD DISTRIBUTION")
        print(quoted.groupby(["series", "horizon_days"])["spread"].describe().to_string())

        print("\nUNCERTAINTY BY HORIZON")
        quoted = quoted.copy()
        quoted["uncertain"] = quoted["midpoint"].between(0.2, 0.8)

        print(
            quoted.groupby(["series", "horizon_days"])
            .agg(
                quotes=("market", "count"),
                uncertain_quotes=("uncertain", "sum"),
                distinct_events=("event", "nunique"),
            )
            .to_string()
        )


if __name__ == "__main__":
    main()
