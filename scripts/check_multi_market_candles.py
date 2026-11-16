"""Measure historical candlestick coverage across resolved markets.

Inputs:
    Ten normalized resolved markets from the sample collector.

Outputs:
    Per-market candle counts, quote coverage, and timing diagnostics.

Side effects:
    Makes read-only Kalshi API requests.
    Does not save or modify files.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd
from sample_resolved_markets import collect_sample

from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.kalshi_client import BASE_URL

SAMPLE_SIZE = 10
PERIOD_INTERVAL = 1
MAX_INTERVALS = 2880  # Two days of one-minute intervals


def fetch_market_candles(
    client: httpx.Client,
    series_ticker: str,
    market_ticker: str,
    open_time: datetime,
    close_time: datetime,
) -> list[dict]:
    """Fetch up to two days of one-minute candles before market close."""
    start_time = max(
        open_time,
        close_time - timedelta(minutes=MAX_INTERVALS),
    )

    response = client.get(
        f"/series/{series_ticker}/markets/{market_ticker}/candlesticks",
        params={
            "start_ts": int(start_time.timestamp()),
            "end_ts": int(close_time.timestamp()),
            "period_interval": PERIOD_INTERVAL,
        },
    )
    response.raise_for_status()

    return response.json()["candlesticks"]


def main() -> None:
    """Collect a small sample and report historical coverage."""
    markets, metadata_failures = collect_sample(limit=SAMPLE_SIZE)

    print(f"Metadata records: {len(markets)}")
    print(f"Metadata failures: {dict(metadata_failures)}")

    reports = []

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        for market in markets.to_dict("records"):
            ticker = market["market_ticker"]

            try:
                candles = fetch_market_candles(
                    client=client,
                    series_ticker=market["series_ticker"],
                    market_ticker=ticker,
                    open_time=market["open_time"],
                    close_time=market["close_time"],
                )

                df = build_candle_dataframe(ticker, candles)

                # A candle is only considered pre-close if its
                # entire minute ended before the market closed.
                if not df.empty:
                    df = df[
                        (df["timestamp_utc"] <= market["close_time"])
                        & (df["timestamp_utc"] > market["open_time"])
                    ].copy()

                reports.append(
                    {
                        "market_ticker": ticker,
                        "event_ticker": market["event_ticker"],
                        "candles": len(df),
                        "usable_quotes": (int(df["usable_midpoint"].sum()) if not df.empty else 0),
                        "trade_candles": (int(df["has_trade"].sum()) if not df.empty else 0),
                        "error": None,
                    }
                )

            except (
                httpx.HTTPError,
                ValueError,
                TypeError,
                KeyError,
            ) as error:
                reports.append(
                    {
                        "market_ticker": ticker,
                        "event_ticker": market["event_ticker"],
                        "candles": 0,
                        "usable_quotes": 0,
                        "trade_candles": 0,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )

    report = pd.DataFrame(reports)

    print("\nMULTI-MARKET CANDLESTICK COVERAGE")
    print(report.to_string(index=False))

    print("\nSUMMARY")
    print(f"Markets checked: {len(report)}")
    print(f"Markets with candles: {(report['candles'] > 0).sum()}")
    print(f"Total candles: {report['candles'].sum()}")
    print(f"Usable quote candles: {report['usable_quotes'].sum()}")
    print(f"Trade candles: {report['trade_candles'].sum()}")
    print(f"Request/validation failures: {report['error'].notna().sum()}")
    print(f"Unique event identifiers: {report['event_ticker'].nunique()}")
    print(f"Checked at: {datetime.now(UTC).isoformat()}")


if __name__ == "__main__":
    main()
