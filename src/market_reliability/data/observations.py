"""Construct labeled research observations from market metadata and quotes."""

from datetime import datetime

import pandas as pd


def build_observation(
    metadata: dict,
    snapshot: dict | None,
    horizon_minutes: int,
) -> dict:
    """Combine one market's metadata and forecast snapshot.

    Inputs:
        metadata: Normalized market metadata, including resolved outcome.
        snapshot: Point-in-time quote snapshot, or None.
        horizon_minutes: Forecast horizon before market close.

    Returns:
        One observation dictionary.

    Side effects:
        None. Does not modify inputs or write files.
    """
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be positive")

    required = {
        "market_ticker",
        "event_ticker",
        "series_ticker",
        "outcome",
        "close_time",
    }

    missing = required - set(metadata)

    if missing:
        raise ValueError(f"Missing metadata fields: {sorted(missing)}")

    close_time = pd.Timestamp(metadata["close_time"])

    if close_time.tzinfo is None:
        raise ValueError("close_time must be timezone-aware")

    cutoff = close_time - pd.Timedelta(minutes=horizon_minutes)

    if snapshot is not None:
        if snapshot["market_ticker"] != metadata["market_ticker"]:
            raise ValueError("Snapshot belongs to a different market")

        snapshot_cutoff = pd.Timestamp(snapshot["cutoff_utc"])

        if snapshot_cutoff != cutoff:
            raise ValueError("Snapshot cutoff does not match horizon")

    event_ticker = metadata["event_ticker"]

    # Example: KXTEMPNYCHS-26NOV1506 -> KXTEMPNYCHS-2026-11-15
    event_date = datetime.strptime(
        event_ticker.split("-")[1][:7],
        "%y%b%d",
    ).date()

    underlying_group = f"{metadata['series_ticker']}-{event_date.isoformat()}"

    return {
        "market_ticker": metadata["market_ticker"],
        "event_ticker": event_ticker,
        "series_ticker": metadata["series_ticker"],
        "underlying_group": underlying_group,
        "horizon_minutes": horizon_minutes,
        "cutoff_utc": cutoff,
        "outcome": metadata["outcome"],
        "has_snapshot": snapshot is not None,
        "quote_time_utc": (snapshot["quote_time_utc"] if snapshot is not None else None),
        "quote_age_minutes": (snapshot["quote_age_minutes"] if snapshot is not None else None),
        "midpoint": (snapshot["midpoint"] if snapshot is not None else None),
        "spread": (snapshot["spread"] if snapshot is not None else None),
    }
