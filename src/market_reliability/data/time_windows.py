"""Plan bounded time windows for historical candlestick API requests."""

from datetime import datetime, timedelta


def make_time_windows(
    start: datetime,
    end: datetime,
    max_minutes: int = 1440,
) -> list[tuple[int, int]]:
    """Split a time range into consecutive Unix-second request windows.

    Inputs:
        start: Beginning of the requested period.
        end: End of the requested period.
        max_minutes: Maximum duration of each request window.

    Returns:
        List of (start_ts, end_ts) integer timestamp pairs.

    Side effects:
        None. No network requests or file writes.
    """
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("Start must be timezone-aware.")

    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("End must be timezone-aware.")

    if start >= end:
        raise ValueError("Start must be earlier than end.")

    if type(max_minutes) is not int or max_minutes <= 0:
        raise ValueError("max_minutes must be a positive integer.")

    windows = []
    current = start

    while current < end:
        window_end = min(
            current + timedelta(minutes=max_minutes),
            end,
        )

        windows.append(
            (
                int(current.timestamp()),
                int(window_end.timestamp()),
            )
        )

        current = window_end

    return windows
