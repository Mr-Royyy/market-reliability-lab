"""Retrieve historical Kalshi candlesticks across multiple time windows."""

from datetime import datetime
from typing import Any

import httpx

from market_reliability.data.http_retry import get_with_retry
from market_reliability.data.kalshi_client import BASE_URL
from market_reliability.data.time_windows import make_time_windows


def fetch_candlestick_history(
    client: httpx.Client,
    series_ticker: str,
    market_ticker: str,
    start: datetime,
    end: datetime,
    max_minutes: int = 1440,
) -> list[dict[str, Any]]:
    """Fetch and combine historical one-minute candlesticks.

    Inputs:
        client: Configured HTTPX client.
        series_ticker: Kalshi market series identifier.
        market_ticker: Individual contract identifier.
        start/end: Time range to retrieve.
        max_minutes: Maximum duration per API request.

    Returns:
        Candlesticks sorted by timestamp, with duplicates removed.

    Side effects:
        Makes read-only HTTP requests.
        Does not save files or modify input data.
    """
    windows = make_time_windows(start, end, max_minutes=max_minutes)
    candles_by_timestamp = {}

    for start_ts, end_ts in windows:
        response = get_with_retry(
            client,
            f"/series/{series_ticker}/markets/{market_ticker}/candlesticks",
            params={
                "start_ts": start_ts,
                "end_ts": end_ts,
                "period_interval": 1,
            },
        )

        payload = response.json()
        candles = payload["candlesticks"]

        if not isinstance(candles, list):
            raise TypeError("Expected candlesticks to be a list.")

        for candle in candles:
            timestamp = candle["end_period_ts"]

            if timestamp in candles_by_timestamp:
                if candles_by_timestamp[timestamp] != candle:
                    raise ValueError(f"Conflicting candles at timestamp {timestamp}.")
            else:
                candles_by_timestamp[timestamp] = candle

    return [candles_by_timestamp[timestamp] for timestamp in sorted(candles_by_timestamp)]


def create_kalshi_http_client() -> httpx.Client:
    """Create a reusable HTTP client for public Kalshi endpoints."""
    return httpx.Client(
        base_url=BASE_URL,
        timeout=30.0,
    )
