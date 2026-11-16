"""Tests for assembling observation datasets."""

import pandas as pd
import pytest

from market_reliability.data.observation_dataset import (
    build_observation_dataset,
)


def make_metadata() -> dict:
    return {
        "market_ticker": "KXTEMPNYCHS-26NOV1506-T38.99",
        "event_ticker": "KXTEMPNYCHS-26NOV1506",
        "series_ticker": "KXTEMPNYCHS",
        "outcome": 0,
        "close_time": pd.Timestamp("2026-11-15T11:00:00Z"),
    }


def make_candles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "market_ticker": [
                "KXTEMPNYCHS-26NOV1506-T38.99",
            ]
            * 2,
            "timestamp_utc": pd.to_datetime(
                [
                    "2026-11-15T10:30:00Z",
                    "2026-11-15T10:45:00Z",
                ],
                utc=True,
            ),
            "usable_midpoint": [True, True],
            "midpoint": [0.55, 0.32],
            "spread": [0.08, 0.04],
        }
    )


def test_builds_multiple_horizons() -> None:
    dataset = build_observation_dataset(
        make_metadata(),
        make_candles(),
        horizons=(30, 15),
    )

    assert len(dataset) == 2

    assert dataset["horizon_minutes"].tolist() == [30, 15]
    assert dataset["midpoint"].tolist() == pytest.approx([0.55, 0.32])
    assert dataset["has_snapshot"].all()


def test_preserves_missing_horizon() -> None:
    dataset = build_observation_dataset(
        make_metadata(),
        make_candles(),
        horizons=(45, 30),
    )

    assert len(dataset) == 2
    assert not dataset.iloc[0]["has_snapshot"]
    assert pd.isna(dataset.iloc[0]["midpoint"])
    assert dataset.iloc[1]["has_snapshot"]


def test_rejects_duplicate_horizons() -> None:
    with pytest.raises(ValueError, match="unique"):
        build_observation_dataset(
            make_metadata(),
            make_candles(),
            horizons=(30, 30),
        )


def test_rejects_empty_horizons() -> None:
    with pytest.raises(ValueError, match="At least one"):
        build_observation_dataset(
            make_metadata(),
            make_candles(),
            horizons=(),
        )


def test_rejects_candles_from_different_market() -> None:
    candles = make_candles()
    candles["market_ticker"] = "OTHER-MARKET"

    with pytest.raises(ValueError, match="different market"):
        build_observation_dataset(
            make_metadata(),
            candles,
            horizons=(30,),
        )


def test_rejects_mixed_market_candles() -> None:
    candles = make_candles()
    candles.loc[1, "market_ticker"] = "OTHER-MARKET"

    with pytest.raises(ValueError, match="different market"):
        build_observation_dataset(
            make_metadata(),
            candles,
            horizons=(30,),
        )
