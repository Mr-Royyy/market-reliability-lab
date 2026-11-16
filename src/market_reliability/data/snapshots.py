"""Select point-in-time quote snapshots from candle data."""

import pandas as pd


def select_quote_snapshot(
    df: pd.DataFrame,
    cutoff: pd.Timestamp,
    max_age_minutes: int = 5,
) -> dict | None:
    """Select the latest usable quote at or before a cutoff.

    Returns a dictionary containing the quote and its age,
    or None when no eligible observation exists.

    Does not modify the input DataFrame.
    """
    if max_age_minutes < 0:
        raise ValueError("max_age_minutes must be nonnegative")

    cutoff = pd.Timestamp(cutoff)

    if cutoff.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")

    if df.empty:
        return None

    required = {
        "timestamp_utc",
        "usable_midpoint",
        "midpoint",
        "spread",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    timestamps = pd.to_datetime(df["timestamp_utc"], utc=True)

    if timestamps.isna().any():
        raise ValueError("Invalid candle timestamps")

    cutoff = cutoff.tz_convert("UTC")

    eligible = df.loc[
        (timestamps <= cutoff)
        & (timestamps >= cutoff - pd.Timedelta(minutes=max_age_minutes))
        & df["usable_midpoint"].eq(True)
    ].copy()

    if eligible.empty:
        return None

    eligible = eligible.sort_values("timestamp_utc")
    latest = eligible.iloc[-1]

    quote_time = pd.Timestamp(latest["timestamp_utc"]).tz_convert("UTC")
    age_minutes = (cutoff - quote_time).total_seconds() / 60

    return {
        "market_ticker": latest["market_ticker"],
        "cutoff_utc": cutoff,
        "quote_time_utc": quote_time,
        "quote_age_minutes": age_minutes,
        "midpoint": float(latest["midpoint"]),
        "spread": float(latest["spread"]),
    }
