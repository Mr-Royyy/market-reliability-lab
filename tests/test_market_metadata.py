"""Tests for Kalshi market metadata normalization."""

from copy import deepcopy

import pytest

from market_reliability.data.market_metadata import (
    normalize_market_metadata,
    parse_timestamp,
)


@pytest.fixture
def market():
    return {
        "ticker": "EXAMPLE-YES",
        "event_ticker": "EVENT-1",
        "market_type": "binary",
        "status": "finalized",
        "result": "no",
        "title": "Will the event happen?",
        "open_time": "2026-11-15T19:21:00Z",
        "close_time": "2026-11-15T21:09:52Z",
        "settlement_ts": "2026-11-15T21:11:54Z",
        "expiration_time": "2026-11-17T18:00:00Z",
    }


@pytest.fixture
def event():
    return {
        "event_ticker": "EVENT-1",
        "series_ticker": "SERIES-1",
        "category": "Sports",
        "title": "Example event",
    }


def test_normalizes_resolved_market(market, event):
    result = normalize_market_metadata(market, event)

    assert result["market_ticker"] == "EXAMPLE-YES"
    assert result["event_ticker"] == "EVENT-1"
    assert result["outcome"] == 0
    assert result["category"] == "Sports"


def test_yes_outcome_becomes_one(market, event):
    market["result"] = "yes"

    result = normalize_market_metadata(market, event)

    assert result["outcome"] == 1


def test_preserves_distinct_timestamps(market, event):
    result = normalize_market_metadata(market, event)

    assert result["close_time"] < result["settlement_time"]
    assert result["settlement_time"] < result["expiration_time"]


def test_does_not_modify_inputs(market, event):
    original_market = deepcopy(market)
    original_event = deepcopy(event)

    normalize_market_metadata(market, event)

    assert market == original_market
    assert event == original_event


def test_rejects_mismatched_event(market, event):
    event["event_ticker"] = "DIFFERENT-EVENT"

    with pytest.raises(ValueError):
        normalize_market_metadata(market, event)


def test_rejects_unresolved_market(market, event):
    market["result"] = ""

    with pytest.raises(ValueError):
        normalize_market_metadata(market, event)


def test_rejects_invalid_chronology(market, event):
    market["close_time"] = "2026-11-15T18:00:00Z"

    with pytest.raises(ValueError):
        normalize_market_metadata(market, event)


def test_rejects_timezone_naive_timestamp():
    with pytest.raises(ValueError):
        parse_timestamp("2026-11-15T19:21:00")
