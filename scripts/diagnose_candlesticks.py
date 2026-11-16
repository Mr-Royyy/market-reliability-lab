"""Inspect trade and quote quality in Kalshi candlesticks."""

from datetime import UTC, datetime, timedelta

import httpx

from market_reliability.data.kalshi_client import BASE_URL

TICKER = "KXNFLSPREAD-26NOV15MINGB-MIN21"
SERIES = "KXNFLSPREAD"


def read_price(candle: dict, field: str) -> float | None:
    """Read a closing dollar price, returning None when missing."""
    value = candle.get(field, {}).get("close_dollars")
    return float(value) if value is not None else None


def main() -> None:
    """Fetch recent candles and summarize their data quality."""
    now = datetime.now(UTC)
    start = now - timedelta(days=2)

    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        response = client.get(
            f"/series/{SERIES}/markets/{TICKER}/candlesticks",
            params={
                "start_ts": int(start.timestamp()),
                "end_ts": int(now.timestamp()),
                "period_interval": 1,
            },
        )
        response.raise_for_status()
        candles = response.json()["candlesticks"]

    counts = {
        "total": len(candles),
        "trade_price_present": 0,
        "positive_volume": 0,
        "both_quotes_present": 0,
        "valid_quote_pair": 0,
        "spread_at_most_10_cents": 0,
    }

    timestamps = []

    for candle in candles:
        timestamps.append(candle["end_period_ts"])

        trade = read_price(candle, "price")
        bid = read_price(candle, "yes_bid")
        ask = read_price(candle, "yes_ask")
        volume = float(candle["volume_fp"])

        if trade is not None:
            counts["trade_price_present"] += 1

        if volume > 0:
            counts["positive_volume"] += 1

        if bid is not None and ask is not None:
            counts["both_quotes_present"] += 1

            if 0 <= bid <= ask <= 1:
                counts["valid_quote_pair"] += 1

                if ask - bid <= 0.10:
                    counts["spread_at_most_10_cents"] += 1

    print("CANDLESTICK QUALITY REPORT")

    for name, value in counts.items():
        print(f"{name}: {value}")

    print(f"Unique timestamps: {len(set(timestamps))}")

    if timestamps:
        first = datetime.fromtimestamp(min(timestamps), UTC)
        last = datetime.fromtimestamp(max(timestamps), UTC)

        print(f"First candle: {first.isoformat()}")
        print(f"Last candle: {last.isoformat()}")


if __name__ == "__main__":
    main()
