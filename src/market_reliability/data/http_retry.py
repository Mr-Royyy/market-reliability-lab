"""Retry temporary HTTP failures with bounded exponential backoff."""

import time

import httpx

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    params: dict | None = None,
    max_attempts: int = 3,
    base_delay: float = 0.5,
) -> httpx.Response:
    """Perform a GET request, retrying selected temporary failures.

    Inputs:
        client: Existing HTTPX client.
        url: Endpoint path.
        params: Optional query parameters.
        max_attempts: Total attempts, including the first.
        base_delay: Initial delay between retries, in seconds.

    Returns:
        Successful HTTPX response.

    Side effects:
        Makes network requests and may sleep between attempts.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    if base_delay < 0:
        raise ValueError("base_delay cannot be negative.")

    for attempt in range(max_attempts):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as error:
            status = error.response.status_code

            if status not in RETRYABLE_STATUSES or attempt == max_attempts - 1:
                raise

        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == max_attempts - 1:
                raise

        time.sleep(base_delay * (2**attempt))

    raise RuntimeError("Unreachable retry state.")
