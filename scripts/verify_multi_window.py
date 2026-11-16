"""Compare single-window and multi-window Kalshi candle retrieval."""

from datetime import UTC, datetime

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)

SERIES = "KXNFLSPREAD"
TICKER = "KXNFLSPREAD-26NOV15MINGB-MIN21"

START = datetime(2026, 11, 15, 19, 21, tzinfo=UTC)
END = datetime(2026, 11, 15, 21, 12, tzinfo=UTC)


def main() -> None:
    """Retrieve the same interval using two different window sizes."""
    with create_kalshi_http_client() as client:
        single = fetch_candlestick_history(
            client,
            SERIES,
            TICKER,
            START,
            END,
            max_minutes=1440,
        )

        multiple = fetch_candlestick_history(
            client,
            SERIES,
            TICKER,
            START,
            END,
            max_minutes=30,
        )

    single_by_time = {candle["end_period_ts"]: candle for candle in single}
    multiple_by_time = {candle["end_period_ts"]: candle for candle in multiple}

    single_times = set(single_by_time)
    multiple_times = set(multiple_by_time)

    print("\nMULTI-WINDOW INTEGRATION REPORT")
    print(f"Single-window candles: {len(single)}")
    print(f"Multi-window candles: {len(multiple)}")
    print(f"Missing from multi-window: {len(single_times - multiple_times)}")
    print(f"Extra in multi-window: {len(multiple_times - single_times)}")

    shared_times = single_times & multiple_times
    conflicting = sum(
        single_by_time[timestamp] != multiple_by_time[timestamp] for timestamp in shared_times
    )

    print(f"Conflicting shared records: {conflicting}")

    if single_by_time != multiple_by_time:
        raise AssertionError("Single-window and multi-window results differ.")

    print("PASS: Both retrieval methods returned identical records.")


if __name__ == "__main__":
    main()
