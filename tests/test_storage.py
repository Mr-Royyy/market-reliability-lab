"""Tests for Parquet dataset storage."""

import pandas as pd
import pytest

from market_reliability.data.storage import load_parquet, save_parquet


def test_parquet_round_trip(tmp_path):
    """Saving and loading should preserve DataFrame contents."""
    original = pd.DataFrame(
        {
            "market_ticker": ["EXAMPLE", "EXAMPLE"],
            "end_period_ts": [1794770520, 1794770580],
            "trade_close": [None, 0.26],
            "midpoint": [0.245, 0.25],
            "usable_midpoint": [True, True],
            "timestamp_utc": pd.to_datetime(
                [1794770520, 1794770580],
                unit="s",
                utc=True,
            ),
        }
    )

    path = tmp_path / "processed" / "sample.parquet"

    save_parquet(original, path)
    restored = load_parquet(path)

    pd.testing.assert_frame_equal(original, restored)


def test_creates_parent_directory(tmp_path):
    """Storage should create missing parent folders."""
    df = pd.DataFrame({"value": [1, 2, 3]})
    path = tmp_path / "nested" / "directory" / "test.parquet"

    save_parquet(df, path)

    assert path.exists()


def test_missing_file_raises_error(tmp_path):
    """Loading a nonexistent dataset should fail clearly."""
    with pytest.raises(FileNotFoundError):
        load_parquet(tmp_path / "missing.parquet")
