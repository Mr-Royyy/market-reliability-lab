"""Calendar-anchored observation scheduling for monthly rainfall contracts."""

import re

import pandas as pd

EVENT_PATTERN = re.compile(r"^KXRAIN[A-Z]+M-(\d{2})([A-Z]{3})$")

MONTH_NUMBERS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def measurement_month(event_ticker: str) -> pd.Timestamp:
    """Return the first UTC day of the rainfall measurement month."""
    match = EVENT_PATTERN.fullmatch(event_ticker)

    if match is None:
        raise ValueError(f"Unsupported rainfall event ticker: {event_ticker}")

    year_suffix, month_abbreviation = match.groups()
    year = 2000 + int(year_suffix)
    month = MONTH_NUMBERS[month_abbreviation]

    return pd.Timestamp(year=year, month=month, day=1, tz="UTC")


def observation_checkpoints(event_ticker: str) -> dict[str, pd.Timestamp]:
    """Return fixed UTC checkpoints for the event's calendar month."""
    month_start = measurement_month(event_ticker)
    next_month = month_start + pd.DateOffset(months=1)

    return {
        "pre_month_7d": month_start - pd.Timedelta(days=7),
        "month_start": month_start,
        "month_end_minus_7d": next_month - pd.Timedelta(days=7),
    }


def contract_eligible_at(
    market: dict,
    checkpoint: pd.Timestamp,
) -> bool:
    """Check whether the contract's recorded trading window covers a time."""
    opened = pd.to_datetime(market["open_time"], utc=True)
    closed = pd.to_datetime(market["close_time"], utc=True)
    checkpoint = pd.to_datetime(checkpoint, utc=True)

    return bool(opened <= checkpoint < closed)


def schedule_contract(market: dict) -> list[dict]:
    """Create one eligibility record per calendar checkpoint."""
    event_ticker = market["event_ticker"]
    checkpoints = observation_checkpoints(event_ticker)

    return [
        {
            "series": market["event_ticker"].split("-")[0],
            "event": event_ticker,
            "market": market["ticker"],
            "checkpoint": name,
            "timestamp_utc": timestamp,
            "eligible": contract_eligible_at(market, timestamp),
        }
        for name, timestamp in checkpoints.items()
    ]
