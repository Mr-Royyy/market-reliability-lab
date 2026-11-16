"""Chronological validation for historical prediction experiments."""

import pandas as pd


def validate_chronology(
    train: pd.DataFrame,
    test: pd.DataFrame,
    settlements: pd.DataFrame,
) -> int:
    """Ensure training observations and labels precede test predictions."""

    required_train = {"market", "event", "timestamp_utc"}
    required_test = {"event", "timestamp_utc"}
    required_settlements = {"market", "settlement_ts"}

    for name, frame, required in [
        ("training", train, required_train),
        ("testing", test, required_test),
        ("settlement", settlements, required_settlements),
    ]:
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Missing {name} columns: {sorted(missing)}")

        if frame.empty:
            raise ValueError(f"Empty {name} data")

    if train["market"].isna().any():
        raise ValueError("Missing training market identifiers")

    if train["market"].duplicated().any():
        raise ValueError("Duplicate training markets")

    if settlements["market"].duplicated().any():
        raise ValueError("Duplicate settlement records")

    if set(train["event"]) & set(test["event"]):
        raise ValueError("Train/test event overlap")

    train_time = pd.to_datetime(train["timestamp_utc"], utc=True, errors="coerce")
    test_time = pd.to_datetime(test["timestamp_utc"], utc=True, errors="coerce")

    if train_time.isna().any() or test_time.isna().any():
        raise ValueError("Missing or invalid observation timestamps")

    test_start = test_time.min()

    if train_time.max() >= test_start:
        raise ValueError("Observation checkpoints overlap")

    settlement_data = settlements[["market", "settlement_ts"]].copy()

    settlement_data["settlement_ts"] = pd.to_datetime(
        settlement_data["settlement_ts"],
        utc=True,
        errors="coerce",
    )

    matched = train[["market"]].merge(
        settlement_data,
        on="market",
        how="left",
        validate="one_to_one",
    )

    if matched["settlement_ts"].isna().any():
        raise ValueError("Missing training settlement timestamps")

    if not (matched["settlement_ts"] < test_start).all():
        raise ValueError("Training labels were not all available before testing")

    return len(matched)
