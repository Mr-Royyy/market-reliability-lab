"""Tests for historical training-label availability."""

import pandas as pd
import pytest

from market_reliability.evaluation.chronology import validate_chronology


@pytest.fixture
def valid_data():
    train = pd.DataFrame(
        {
            "market": ["SEP-A", "SEP-B"],
            "event": ["SEP-EVENT", "SEP-EVENT"],
            "timestamp_utc": [
                "2026-09-24T18:00:00Z",
                "2026-09-24T18:00:00Z",
            ],
        }
    )

    test = pd.DataFrame(
        {
            "market": ["OCT-A"],
            "event": ["OCT-EVENT"],
            "timestamp_utc": ["2026-10-25T18:00:00Z"],
        }
    )

    settlements = pd.DataFrame(
        {
            "market": ["SEP-A", "SEP-B"],
            "settlement_ts": [
                "2026-10-01T12:00:00Z",
                "2026-10-02T12:00:00Z",
            ],
        }
    )

    return train, test, settlements


def test_valid_chronology_passes(valid_data):
    train, test, settlements = valid_data

    assert validate_chronology(train, test, settlements) == 2


def test_late_settlement_rejected(valid_data):
    train, test, settlements = valid_data
    settlements.loc[1, "settlement_ts"] = "2026-10-26T12:00:00Z"

    with pytest.raises(ValueError, match="not all available"):
        validate_chronology(train, test, settlements)


def test_missing_settlement_rejected(valid_data):
    train, test, settlements = valid_data
    settlements.loc[1, "settlement_ts"] = None

    with pytest.raises(ValueError, match="Missing training settlement"):
        validate_chronology(train, test, settlements)


def test_duplicate_settlement_rejected(valid_data):
    train, test, settlements = valid_data

    settlements = pd.concat(
        [settlements, settlements.iloc[[0]]],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Duplicate settlement"):
        validate_chronology(train, test, settlements)


def test_overlapping_events_rejected(valid_data):
    train, test, settlements = valid_data
    test.loc[0, "event"] = "SEP-EVENT"

    with pytest.raises(ValueError, match="event overlap"):
        validate_chronology(train, test, settlements)
