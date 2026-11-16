"""Tests for constructing research observations."""

import pandas as pd
import pytest

from market_reliability.data.observations import build_observation


def make_metadata() -> dict:
    return {
        "market_ticker": "KXTEMPNYCHS-26NOV1506-T38.99",
        "event_ticker": "KXTEMPNYCHS-26NOV1506",
        "series_ticker": "KXTEMPNYCHS",
        "outcome": 0,
        "close_time": pd.Timestamp("2026-11-15T11:00:00Z"),
    }


def make_snapshot() -> dict:
    return {
        "market_ticker": "KXTEMPNYCHS-26NOV1506-T38.99",
        "cutoff_utc": pd.Timestamp("2026-11-15T10:30:00Z"),
        "quote_time_utc": pd.Timestamp("2026-11-15T10:29:00Z"),
        "quote_age_minutes": 1.0,
        "midpoint": 0.55,
        "spread": 0.08,
    }


def test_builds_labeled_observation() -> None:
    observation = build_observation(
        make_metadata(),
        make_snapshot(),
        horizon_minutes=30,
    )

    assert observation["outcome"] == 0
    assert observation["midpoint"] == pytest.approx(0.55)
    assert observation["has_snapshot"] is True
    assert observation["underlying_group"] == ("KXTEMPNYCHS-2026-11-15")


def test_preserves_missing_snapshot() -> None:
    observation = build_observation(
        make_metadata(),
        None,
        horizon_minutes=30,
    )

    assert observation["has_snapshot"] is False
    assert observation["midpoint"] is None
    assert observation["outcome"] == 0


def test_rejects_mismatched_market() -> None:
    snapshot = make_snapshot()
    snapshot["market_ticker"] = "OTHER"

    with pytest.raises(ValueError, match="different market"):
        build_observation(make_metadata(), snapshot, 30)


def test_rejects_mismatched_cutoff() -> None:
    snapshot = make_snapshot()
    snapshot["cutoff_utc"] = pd.Timestamp("2026-11-15T10:45:00Z")

    with pytest.raises(ValueError, match="cutoff"):
        build_observation(make_metadata(), snapshot, 30)


def test_rejects_invalid_horizon() -> None:
    with pytest.raises(ValueError, match="positive"):
        build_observation(make_metadata(), make_snapshot(), 0)
