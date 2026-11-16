"""Tests for monthly rainfall snapshot scheduling."""

import pandas as pd
import pytest

from market_reliability.data.rainfall_schedule import (
    contract_eligible_at,
    measurement_month,
    observation_checkpoints,
    schedule_contract,
)


@pytest.fixture
def miami_contracts():
    return [
        {
            "series_ticker": "KXRAINMIAM",
            "event_ticker": "KXRAINMIAM-26NOV",
            "ticker": "KXRAINMIAM-26NOV-1",
            "open_time": "2026-10-02T03:55:59Z",
            "close_time": "2026-11-02T13:00:23Z",
        },
        {
            "series_ticker": "KXRAINMIAM",
            "event_ticker": "KXRAINMIAM-26NOV",
            "ticker": "KXRAINMIAM-26NOV-9",
            "open_time": "2026-11-01T18:41:00Z",
            "close_time": "2026-12-01T04:59:59Z",
        },
    ]


def test_measurement_month():
    assert measurement_month("KXRAINMIAM-26NOV") == pd.Timestamp("2026-11-01T00:00:00Z")


def test_invalid_event_ticker():
    with pytest.raises(ValueError):
        measurement_month("INVALID-EVENT")


def test_checkpoints():
    checkpoints = observation_checkpoints("KXRAINMIAM-26NOV")

    assert checkpoints["pre_month_7d"] == pd.Timestamp("2026-10-25T00:00:00Z")
    assert checkpoints["month_start"] == pd.Timestamp("2026-11-01T00:00:00Z")
    assert checkpoints["month_end_minus_7d"] == pd.Timestamp("2026-11-24T00:00:00Z")


def test_early_settled_contract(miami_contracts):
    contract = miami_contracts[0]
    checkpoints = observation_checkpoints(contract["event_ticker"])

    assert contract_eligible_at(contract, checkpoints["pre_month_7d"])
    assert contract_eligible_at(contract, checkpoints["month_start"])
    assert not contract_eligible_at(contract, checkpoints["month_end_minus_7d"])


def test_later_listed_contract(miami_contracts):
    contract = miami_contracts[1]
    checkpoints = observation_checkpoints(contract["event_ticker"])

    assert not contract_eligible_at(contract, checkpoints["pre_month_7d"])
    assert not contract_eligible_at(contract, checkpoints["month_start"])
    assert contract_eligible_at(contract, checkpoints["month_end_minus_7d"])


def test_schedule_has_three_rows(miami_contracts):
    rows = schedule_contract(miami_contracts[0])

    assert len(rows) == 3
    assert sum(row["eligible"] for row in rows) == 2


def test_schedule_without_series_ticker(miami_contracts):
    contract = miami_contracts[0].copy()
    contract.pop("series_ticker")

    rows = schedule_contract(contract)

    assert len(rows) == 3
    assert all(row["series"] == "KXRAINMIAM" for row in rows)
