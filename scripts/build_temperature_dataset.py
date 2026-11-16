"""Build a small labeled dataset from settled NYC temperature markets.

Inputs:
    Settled Kalshi temperature contracts and historical candlesticks.

Outputs:
    data/processed/temperature_sample.parquet

Side effects:
    Read-only API requests and one local Parquet file write.
"""

from pathlib import Path

import pandas as pd

from market_reliability.data.candlestick_client import (
    create_kalshi_http_client,
    fetch_candlestick_history,
)
from market_reliability.data.dataset import build_candle_dataframe
from market_reliability.data.http_retry import get_with_retry
from market_reliability.data.market_metadata import normalize_market_metadata
from market_reliability.data.observation_dataset import (
    build_observation_dataset,
)
from market_reliability.data.storage import save_parquet

SERIES = "KXTEMPNYCHS"
EVENTS_TO_SAMPLE = 3
HORIZONS = (15, 30, 45)
OUTPUT_PATH = Path("data/processed/temperature_sample.parquet")


def main() -> None:
    """Fetch and assemble observations for three temperature events."""
    observations = []

    with create_kalshi_http_client() as client:
        response = get_with_retry(
            client,
            "/markets",
            params={
                "series_ticker": SERIES,
                "status": "settled",
                "limit": 200,
                "mve_filter": "exclude",
            },
        )

        markets = response.json()["markets"]

        event_tickers = sorted(
            {market["event_ticker"] for market in markets if market.get("event_ticker")}
        )

        selected_events = event_tickers[:EVENTS_TO_SAMPLE]

        print(f"Selected events: {selected_events}")

        for event_ticker in selected_events:
            event_response = get_with_retry(
                client,
                f"/events/{event_ticker}",
            )

            event = event_response.json()["event"]

            event_markets = [
                market for market in markets if market.get("event_ticker") == event_ticker
            ]

            print(f"\nProcessing {event_ticker}: {len(event_markets)} contracts")

            for market in event_markets:
                metadata = normalize_market_metadata(market, event)

                candles = fetch_candlestick_history(
                    client=client,
                    series_ticker=metadata["series_ticker"],
                    market_ticker=metadata["market_ticker"],
                    start=metadata["open_time"],
                    end=metadata["close_time"],
                )

                candle_df = build_candle_dataframe(
                    metadata["market_ticker"],
                    candles,
                )

                observation_df = build_observation_dataset(
                    metadata,
                    candle_df,
                    horizons=HORIZONS,
                )

                observations.append(observation_df)

    if not observations:
        raise RuntimeError("No observations were generated")

    dataset = pd.concat(observations, ignore_index=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_parquet(dataset, OUTPUT_PATH)

    print("\nDATASET SUMMARY")
    print(f"Rows: {len(dataset)}")
    print(f"Markets: {dataset['market_ticker'].nunique()}")
    print(f"Events: {dataset['event_ticker'].nunique()}")

    print("\nSNAPSHOT COVERAGE")
    print(
        dataset.groupby("horizon_minutes")["has_snapshot"].agg(["count", "sum", "mean"]).to_string()
    )

    print("\nSAMPLE OBSERVATIONS")
    print(dataset.head(10).to_string(index=False))

    print(f"\nSaved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
