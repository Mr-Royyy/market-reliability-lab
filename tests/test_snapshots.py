"""Tests for point-in-time snapshot selection."""

import pandas as pd
import pytest

from market_reliability.data.snapshots import select_quote_snapshot


def make_candles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "market_ticker": ["TEST"] * 3,
            "timestamp_utc": pd.to_datetime(
                [
                    "2026-11-15T13:24:00Z",
                    "2026-11-15T13:28:00Z",
                    "2026-11-15T13:31:00Z",
                ],
                utc=True,
            ),
            "usable_midpoint": [True, True, True],
            "midpoint": [0.40, 0.45, 0.90],
            "spread": [0.02, 0.01, 0.01],
        }
    )


def test_selects_latest_quote_before_cutoff() -> None:
    snapshot = select_quote_snapshot(
        make_candles(),
        pd.Timestamp("2026-11-15T13:30:00Z"),
    )

    assert snapshot is not None
    assert snapshot["midpoint"] == pytest.approx(0.45)
    assert snapshot["quote_age_minutes"] == pytest.approx(2.0)


def test_rejects_stale_quote() -> None:
    df = make_candles().iloc[:1]

    snapshot = select_quote_snapshot(
        df,
        pd.Timestamp("2026-11-15T13:30:00Z"),
        max_age_minutes=5,
    )

    assert snapshot is None


def test_rejects_future_quote() -> None:
    df = make_candles().iloc[2:]

    snapshot = select_quote_snapshot(
        df,
        pd.Timestamp("2026-11-15T13:30:00Z"),
    )

    assert snapshot is None


def test_skips_unusable_latest_quote() -> None:
    df = make_candles()
    df.loc[1, "usable_midpoint"] = False

    snapshot = select_quote_snapshot(
        df,
        pd.Timestamp("2026-11-15T13:30:00Z"),
    )

    assert snapshot is None


def test_requires_timezone_aware_cutoff() -> None:
    with pytest.raises(ValueError):
        select_quote_snapshot(
            make_candles(),
            pd.Timestamp("2026-11-15 13:30:00"),
        )
