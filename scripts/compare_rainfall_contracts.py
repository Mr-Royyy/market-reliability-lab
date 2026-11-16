"""Compare settlement timing for two thresholds in one rainfall event."""

import json

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
)
from market_reliability.data.http_retry import get_with_retry

TICKERS = (
    "KXRAINMIAM-26NOV-1",
    "KXRAINMIAM-26NOV-9",
)

FIELDS = (
    "ticker",
    "event_ticker",
    "title",
    "rules_primary",
    "rules_secondary",
    "open_time",
    "close_time",
    "expiration_time",
    "settlement_ts",
    "status",
    "result",
    "yes_bid",
    "yes_ask",
    "last_price",
)


def main() -> None:
    with create_kalshi_http_client() as client:
        for ticker in TICKERS:
            response = get_with_retry(client, f"/markets/{ticker}")
            response.raise_for_status()

            market = response.json()["market"]

            print(f"\n{'=' * 65}")
            print(f"CONTRACT: {ticker}")
            print(
                json.dumps(
                    {field: market.get(field) for field in FIELDS},
                    indent=2,
                    default=str,
                )
            )


if __name__ == "__main__":
    main()
