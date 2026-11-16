"""Tests for multi-window Kalshi candlestick retrieval."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from market_reliability.data.candlestick_client import (
    fetch_candlestick_history,
)


def test_combines_and_deduplicates_windows():
    """Overlapping boundary candles should appear only once."""
    start = datetime(2026, 11, 15, tzinfo=UTC)
    end = start + timedelta(hours=2)

    first_boundary = int((start + timedelta(hours=1)).timestamp())

    def handler(request: httpx.Request) -> httpx.Response:
        start_ts = int(request.url.params["start_ts"])

        if start_ts == int(start.timestamp()):
            candles = [
                {"end_period_ts": int(start.timestamp()) + 60},
                {"end_period_ts": first_boundary},
            ]
        else:
            candles = [
                {"end_period_ts": first_boundary},
                {"end_period_ts": int(end.timestamp())},
            ]

        return httpx.Response(200, json={"candlesticks": candles})

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        base_url="https://example.com",
        transport=transport,
    ) as client:
        result = fetch_candlestick_history(
            client,
            "SERIES",
            "MARKET",
            start,
            end,
            max_minutes=60,
        )

    assert len(result) == 3
    assert [item["end_period_ts"] for item in result] == sorted(
        item["end_period_ts"] for item in result
    )


def test_rejects_conflicting_duplicates():
    """Conflicting records at the same timestamp should fail."""
    start = datetime(2026, 11, 15, tzinfo=UTC)
    end = start + timedelta(hours=2)

    boundary = int((start + timedelta(hours=1)).timestamp())
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        return httpx.Response(
            200,
            json={
                "candlesticks": [
                    {
                        "end_period_ts": boundary,
                        "volume_fp": str(request_count),
                    }
                ]
            },
        )

    with (
        httpx.Client(
            base_url="https://example.com",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(ValueError),
    ):
        fetch_candlestick_history(
            client,
            "SERIES",
            "MARKET",
            start,
            end,
            max_minutes=60,
        )


def test_rejects_invalid_response_structure():
    """Malformed API payloads should raise an error."""
    start = datetime(2026, 11, 15, tzinfo=UTC)
    end = start + timedelta(hours=1)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candlesticks": "invalid"},
        )

    with (
        httpx.Client(
            base_url="https://example.com",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(TypeError),
    ):
        fetch_candlestick_history(
            client,
            "SERIES",
            "MARKET",
            start,
            end,
        )
