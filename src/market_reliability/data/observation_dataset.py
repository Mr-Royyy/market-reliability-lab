"""Build research observations from normalized market data."""

import pandas as pd

from market_reliability.data.observations import build_observation
from market_reliability.data.snapshots import select_quote_snapshot


def build_observation_dataset(
    metadata: dict,
    candles: pd.DataFrame,
    horizons: tuple[int, ...] = (15, 30, 45),
    max_quote_age_minutes: int = 5,
) -> pd.DataFrame:
    """Build one observation per requested forecast horizon.

    Inputs:
        metadata: Normalized metadata for one resolved contract.
        candles: Normalized candle DataFrame for that contract.
        horizons: Forecast horizons in minutes.
        max_quote_age_minutes: Maximum eligible quote age.

    Outputs:
        DataFrame with one observation per horizon.

    Side effects:
        None. No API requests or file writes.
    """
    if not horizons:
        raise ValueError("At least one horizon is required")

    if len(set(horizons)) != len(horizons):
        raise ValueError("Horizons must be unique")

    if any(horizon <= 0 for horizon in horizons):
        raise ValueError("Horizons must be positive")

    if not candles.empty:
        if "market_ticker" not in candles.columns:
            raise ValueError("Candles missing market_ticker column")

        candle_markets = set(candles["market_ticker"].dropna())

        if candle_markets != {metadata["market_ticker"]}:
            raise ValueError(
                "Candles belong to a different market or contain missing market identifiers"
            )

        if candles["market_ticker"].isna().any():
            raise ValueError("Candles contain missing market identifiers")

    close_time = pd.Timestamp(metadata["close_time"])

    rows = []

    for horizon in horizons:
        cutoff = close_time - pd.Timedelta(minutes=horizon)

        snapshot = select_quote_snapshot(
            candles,
            cutoff,
            max_age_minutes=max_quote_age_minutes,
        )

        observation = build_observation(
            metadata,
            snapshot,
            horizon_minutes=horizon,
        )

        rows.append(observation)

    return pd.DataFrame(rows)
