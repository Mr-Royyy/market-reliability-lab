"""Tests for bounded HTTP retry behavior."""

import httpx
import pytest

from market_reliability.data.http_retry import get_with_retry


def test_successful_request_needs_one_attempt():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, json={"ok": True})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = get_with_retry(client, "https://example.com")

    assert response.status_code == 200
    assert attempts == 1


def test_retries_temporary_server_failure():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            return httpx.Response(503)

        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = get_with_retry(
            client,
            "https://example.com",
            base_delay=0,
        )

    assert response.status_code == 200
    assert attempts == 3


def test_does_not_retry_permanent_error():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(404)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        get_with_retry(client, "https://example.com", base_delay=0)

    assert attempts == 1


def test_stops_after_maximum_attempts():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        get_with_retry(
            client,
            "https://example.com",
            max_attempts=3,
            base_delay=0,
        )

    assert attempts == 3


def test_rejects_invalid_attempt_count():
    with httpx.Client() as client, pytest.raises(ValueError):
        get_with_retry(
            client,
            "https://example.com",
            max_attempts=0,
        )
