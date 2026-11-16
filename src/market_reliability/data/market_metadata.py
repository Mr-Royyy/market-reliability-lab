"""Normalize Kalshi market metadata for reproducible research."""

from datetime import datetime
from typing import Any


def parse_timestamp(value: str | None) -> datetime | None:
    """Convert an ISO timestamp into a timezone-aware datetime."""
    if value is None:
        return None

    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Market timestamps must include a timezone.")

    return parsed


def normalize_market_metadata(
    market: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """Convert market and event API responses into one research record.

    Inputs:
        market: Kalshi market object.
        event: Kalshi parent event object.

    Returns:
        A flat dictionary with market identity, timing, and outcome.

    Side effects:
        None. Does not modify inputs, call the API, or save files.
    """
    if market["event_ticker"] != event["event_ticker"]:
        raise ValueError("Market and event identifiers do not match.")

    if market["market_type"] != "binary":
        raise ValueError("Only binary markets are supported.")

    result = market["result"]

    if result not in ("yes", "no"):
        raise ValueError("Market must have a resolved YES/NO outcome.")

    outcome = 1 if result == "yes" else 0

    open_time = parse_timestamp(market.get("open_time"))
    close_time = parse_timestamp(market.get("close_time"))
    settlement_time = parse_timestamp(market.get("settlement_ts"))

    if open_time is None or close_time is None:
        raise ValueError("Market opening and closing times are required.")

    if open_time >= close_time:
        raise ValueError("Market must close after opening.")

    if settlement_time is not None and settlement_time < close_time:
        raise ValueError("Settlement cannot precede market close.")

    return {
        "market_ticker": market["ticker"],
        "event_ticker": market["event_ticker"],
        "series_ticker": event["series_ticker"],
        "category": event.get("category"),
        "market_title": market.get("title"),
        "event_title": event.get("title"),
        "status": market["status"],
        "outcome": outcome,
        "open_time": open_time,
        "close_time": close_time,
        "settlement_time": settlement_time,
        "expiration_time": parse_timestamp(market.get("expiration_time")),
    }
