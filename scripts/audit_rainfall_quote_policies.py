"""Compare joint quote freshness and spread policies for rainfall markets.

Uses the latest valid quote at or before each eligible forecast cutoff.
Read-only API requests; prints summaries without saving files.
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

POLICIES = {
    "strict": (5, 0.05),
    "moderate": (60, 0.10),
    "exploratory": (1440, 0.20),
}


def get_cutoff_quote(
    client: httpx.Client,
    series: str,
    market: dict,
    horizon_days: int,
) -> dict:
    """Find one latest valid historical quote for a fixed cutoff."""
    ticker = market["ticker"]
    opened = pd.Timestamp(market["open_time"])
    closed = pd.Timestamp(market["close_time"])
    cutoff = closed - pd.Timedelta(days=horizon_days)

    result = {
        "series": series,
        "event": market["event_ticker"],
        "market": ticker,
        "horizon_days": horizon_days,
        "eligible": opened <= cutoff < closed,
        "has_quote": False,
        "quote_age_minutes": float("nan"),
        "midpoint": float("nan"),
        "spread": float("nan"),
        "error": False,
    }

    if not result["eligible"]:
        return result

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
        return result

    valid = df.loc[
        (df["timestamp_utc"] >= start) & (df["timestamp_utc"] <= cutoff) & df["has_valid_quotes"]
    ].sort_values("timestamp_utc")

    if valid.empty:
        return result

    latest = valid.iloc[-1]

    result.update(
        {
            "has_quote": True,
            "quote_age_minutes": (cutoff - latest["timestamp_utc"]).total_seconds() / 60,
            "midpoint": float(latest["midpoint"]),
            "spread": float(latest["spread"]),
        }
    )

    return result


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
                        rows.append(get_cutoff_quote(client, series, market, days))
                    except (
                        httpx.HTTPError,
                        ValueError,
                        KeyError,
                        TypeError,
                    ) as exc:
                        print(f"Failed {market['ticker']}, {days}d: {exc}")
                        rows.append(
                            {
                                "series": series,
                                "event": market["event_ticker"],
                                "market": market["ticker"],
                                "horizon_days": days,
                                "eligible": False,
                                "has_quote": False,
                                "quote_age_minutes": float("nan"),
                                "midpoint": float("nan"),
                                "spread": float("nan"),
                                "error": True,
                            }
                        )

                if index % 10 == 0:
                    print(f"Processed {index}/{len(markets)} contracts")

    df = pd.DataFrame(rows)

    if df.empty:
        print("No results.")
        return

    # Apply every policy to the same latest valid quote.
    df["any_valid_quote"] = df["eligible"] & df["has_quote"]

    for name, (max_age, max_spread) in POLICIES.items():
        df[name] = (
            df["eligible"]
            & df["has_quote"]
            & (df["quote_age_minutes"] <= max_age)
            & (df["spread"] <= max_spread)
        )

    print("\nPOLICY COVERAGE BY HORIZON")

    summary = []

    for (series, days), group in df.groupby(["series", "horizon_days"]):
        eligible = group.loc[group["eligible"]]

        for policy in ("any_valid_quote", *POLICIES):
            accepted = eligible.loc[eligible[policy]]

            summary.append(
                {
                    "series": series,
                    "horizon_days": days,
                    "policy": policy,
                    "eligible": len(eligible),
                    "accepted": len(accepted),
                    "coverage_pct": round(100 * len(accepted) / len(eligible), 1)
                    if len(eligible)
                    else float("nan"),
                    "events": accepted["event"].nunique(),
                    "uncertain": int(accepted["midpoint"].between(0.2, 0.8).sum()),
                }
            )

    print(pd.DataFrame(summary).to_string(index=False))

    print("\nOVERALL POLICY SUMMARY")

    overall = []

    for policy in ("any_valid_quote", *POLICIES):
        accepted = df.loc[df[policy]]

        overall.append(
            {
                "policy": policy,
                "accepted": len(accepted),
                "eligible": int(df["eligible"].sum()),
                "distinct_contracts": accepted["market"].nunique(),
                "distinct_events": accepted["event"].nunique(),
                "uncertain_snapshots": int(accepted["midpoint"].between(0.2, 0.8).sum()),
            }
        )

    print(pd.DataFrame(overall).to_string(index=False))

    print("\nREJECTION REASONS")

    eligible = df.loc[df["eligible"]]

    print(
        pd.Series(
            {
                "no_valid_quote": int((~eligible["has_quote"]).sum()),
                "stale_over_5m": int(
                    (eligible["has_quote"] & (eligible["quote_age_minutes"] > 5)).sum()
                ),
                "spread_over_0.05": int(
                    (eligible["has_quote"] & (eligible["spread"] > 0.05)).sum()
                ),
                "stale_over_60m": int(
                    (eligible["has_quote"] & (eligible["quote_age_minutes"] > 60)).sum()
                ),
                "spread_over_0.10": int(
                    (eligible["has_quote"] & (eligible["spread"] > 0.10)).sum()
                ),
                "request_errors": int(df["error"].sum()),
            }
        ).to_string()
    )

    print("\nNote: rejection reasons overlap; a quote may be both stale and wide.")


if __name__ == "__main__":
    main()
