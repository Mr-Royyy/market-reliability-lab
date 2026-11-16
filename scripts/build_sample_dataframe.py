"""Build an exploratory DataFrame from Kalshi market candlesticks."""

from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd

from market_reliability.data.kalshi_client import BASE_URL
from market_reliability.data.normalize import normalize_candle
from market_reliability.data.storage import load_parquet, save_parquet

TICKER = "KXNFLSPREAD-26NOV15MINGB-MIN21"
SERIES = "KXNFLSPREAD"


def fetch_candles() -> list[dict]:
    """Retrieve recent one-minute candlesticks from Kalshi."""
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

        return response.json()["candlesticks"]


def build_dataframe(candles: list[dict]) -> pd.DataFrame:
    """Normalize candles into a timestamp-sorted pandas DataFrame."""
    records = [normalize_candle(TICKER, candle) for candle in candles]

    df = pd.DataFrame(records)

    if df.empty:
        return df

    df["timestamp_utc"] = pd.to_datetime(
        df["end_period_ts"],
        unit="s",
        utc=True,
    )

    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    if df["end_period_ts"].duplicated().any():
        raise ValueError("Duplicate candlestick timestamps detected.")

    return df


def main() -> None:
    """Fetch candles, build a DataFrame, and display basic diagnostics."""
    candles = fetch_candles()
    df = build_dataframe(candles)

    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    if df.empty:
        print("No candles were returned.")
        return

    print("\nFIRST FIVE ROWS")
    print(df.head().to_string(index=False))

    print("\nLAST FIVE ROWS")
    print(df.tail().to_string(index=False))

    print("\nMISSING VALUES")
    print(df.isna().sum())

    print("\nSUMMARY STATISTICS")
    print(df[["trade_close", "midpoint", "spread", "volume"]].describe())

    output_path = "data/processed/sample_nfl_candles.parquet"

    save_parquet(df, output_path)

    restored = load_parquet(output_path)
    pd.testing.assert_frame_equal(df, restored)

    print(f"\nSaved dataset: {output_path}")
    print(f"Verified rows after reload: {len(restored)}")


if __name__ == "__main__":
    main()
