"""Descriptive October rainfall calibration baseline.

Uses one predetermined calendar checkpoint and hour per contract.
Does not claim independent contract-level observations.
"""

from pathlib import Path

import numpy as np
import pandas as pd

QUOTES = Path("data/processed/october_calendar_audit.csv")
OUTCOMES = Path("data/processed/rainfall_outcome_inventory.csv")
OUTPUT = Path("data/processed/october_baseline_observations.csv")

CHECKPOINT = "month_end_minus_7d"
HOUR_UTC = 18


def main() -> None:
    quotes = pd.read_csv(QUOTES)
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
        raise ValueError("Some quoted contracts have no resolved outcome")

    if not data["event"].eq(data["event_outcome"]).all():
        raise ValueError("Event identifiers disagree")

    if not data["result"].isin(["yes", "no"]).all():
        raise ValueError("Unexpected outcome label")

    data["y"] = data["result"].eq("yes").astype(int)
    data["p"] = pd.to_numeric(data["midpoint"], errors="raise")

    if not data["p"].between(0, 1).all():
        raise ValueError("Probabilities outside [0, 1]")

    data["brier"] = (data["p"] - data["y"]) ** 2

    epsilon = 1e-6
    p_safe = data["p"].clip(epsilon, 1 - epsilon)

    data["log_loss"] = -(data["y"] * np.log(p_safe) + (1 - data["y"]) * np.log(1 - p_safe))

    print("\nOCTOBER BASELINE")
    print(f"Checkpoint: {CHECKPOINT}, {HOUR_UTC:02d}:00 UTC")
    print(f"Contracts: {len(data)}")
    print(f"City-month events: {data['event'].nunique()}")
    print(f"YES outcomes: {int(data['y'].sum())}")
    print(f"Mean Brier score: {data['brier'].mean():.4f}")
    print(f"Mean log loss: {data['log_loss'].mean():.4f}")

    event_scores = (
        data.groupby("event")
        .agg(
            contracts=("market", "size"),
            yes=("y", "sum"),
            mean_probability=("p", "mean"),
            brier=("brier", "mean"),
            log_loss=("log_loss", "mean"),
        )
        .reset_index()
    )

    print("\nEVENT-LEVEL RESULTS")
    print(event_scores.to_string(index=False))

    print("\nEQUAL-EVENT-WEIGHTED METRICS")
    print(f"Brier: {event_scores['brier'].mean():.4f}")
    print(f"Log loss: {event_scores['log_loss'].mean():.4f}")

    print("\nPROBABILITY DISTRIBUTION")
    print(data["p"].describe().to_string())

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT, index=False)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
