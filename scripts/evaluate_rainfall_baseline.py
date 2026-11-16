"""Evaluate a descriptive rainfall probability baseline across two months."""

from pathlib import Path

import numpy as np
import pandas as pd

AUDITS = [
    Path("data/processed/september_calendar_audit.csv"),
    Path("data/processed/october_calendar_audit.csv"),
]

OUTCOMES = Path("data/processed/rainfall_outcome_inventory.csv")
OUTPUT = Path("data/processed/rainfall_baseline_observations.csv")

CHECKPOINT = "month_end_minus_7d"
HOUR_UTC = 18


def main() -> None:
    quotes = pd.concat(
        [pd.read_csv(path) for path in AUDITS],
        ignore_index=True,
    )
    outcomes = pd.read_csv(OUTCOMES)

    selected = quotes.loc[
        quotes["checkpoint"].eq(CHECKPOINT)
        & quotes["hour_utc"].eq(HOUR_UTC)
        & quotes["eligibility_status"].eq("eligible")
        & quotes["moderate"].eq(True)
        & ~quotes["error"].eq(True)
    ].copy()

    if selected["market"].duplicated().any():
        raise ValueError("Duplicate contract observations")

    labels = outcomes.loc[
        outcomes["resolved"].eq(True),
        ["market", "event", "result"],
    ].copy()

    if labels["market"].duplicated().any():
        raise ValueError("Duplicate outcome labels")

    data = selected.merge(
        labels,
        on="market",
        how="left",
        validate="one_to_one",
        suffixes=("", "_outcome"),
    )

    if data["result"].isna().any():
        raise ValueError("Missing outcome labels")

    if not data["event"].eq(data["event_outcome"]).all():
        raise ValueError("Event identifiers disagree")

    data["y"] = data["result"].eq("yes").astype(int)
    data["p"] = pd.to_numeric(data["midpoint"], errors="raise")

    if not data["p"].between(0, 1).all():
        raise ValueError("Probabilities outside [0, 1]")

    data["brier"] = (data["p"] - data["y"]) ** 2

    p_safe = data["p"].clip(1e-6, 1 - 1e-6)
    data["log_loss"] = -(data["y"] * np.log(p_safe) + (1 - data["y"]) * np.log(1 - p_safe))

    print("\nCOMBINED RAINFALL BASELINE")
    print(f"Contracts: {len(data)}")
    print(f"City-month events: {data['event'].nunique()}")
    print(f"YES outcomes: {int(data['y'].sum())}")
    print(f"Mean market probability: {data['p'].mean():.4f}")
    print(f"Observed YES rate: {data['y'].mean():.4f}")

    print("\nCONTRACT-WEIGHTED SCORES")
    print(f"Brier: {data['brier'].mean():.4f}")
    print(f"Log loss: {data['log_loss'].mean():.4f}")

    event_scores = (
        data.groupby("event")
        .agg(
            contracts=("market", "size"),
            brier=("brier", "mean"),
            log_loss=("log_loss", "mean"),
        )
        .reset_index()
    )

    print("\nEQUAL-EVENT-WEIGHTED SCORES")
    print(f"Brier: {event_scores['brier'].mean():.4f}")
    print(f"Log loss: {event_scores['log_loss'].mean():.4f}")

    print("\nMONTHLY RESULTS")
    data["month"] = data["event"].str.extract(r"-(\d{2}[A-Z]{3})$")
    print(
        data.groupby("month")
        .agg(
            contracts=("market", "size"),
            events=("event", "nunique"),
            yes=("y", "sum"),
            brier=("brier", "mean"),
            log_loss=("log_loss", "mean"),
        )
        .to_string()
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT, index=False)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
