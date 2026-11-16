"""Exploratory September-to-October rainfall probability modeling."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from market_reliability.evaluation.chronology import validate_chronology

INPUT = Path("data/processed/rainfall_baseline_observations.csv")
OUTPUT = Path("data/processed/rainfall_ml_predictions.csv")

TRAIN_MONTH = "26SEP"
TEST_MONTH = "26OCT"


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def evaluate(name: str, y: np.ndarray, p: np.ndarray) -> None:
    print(
        f"{name:<28}Brier={brier_score_loss(y, p):.4f}  LogLoss={log_loss(y, p, labels=[0, 1]):.4f}"
    )


def main() -> None:
    df = pd.read_csv(INPUT)

    required = ["market", "event", "month", "p", "spread", "age_minutes", "y"]
    if df[required].isna().any().any():
        raise ValueError("Missing required data")

    if df["market"].duplicated().any():
        raise ValueError("Duplicate market observations")

    if not df["p"].between(0, 1).all():
        raise ValueError("Invalid probabilities")

    if not df["y"].isin([0, 1]).all():
        raise ValueError("Invalid outcome labels")

    df["market_logit"] = logit(df["p"].to_numpy())

    train = df.loc[df["month"].eq(TRAIN_MONTH)].copy()
    test = df.loc[df["month"].eq(TEST_MONTH)].copy()

    if train.empty or test.empty:
        raise ValueError("Missing training or testing month")

    if train["y"].nunique() != 2:
        raise ValueError("Training data must contain both classes")

    outcomes = pd.read_csv("data/processed/rainfall_outcome_inventory.csv")

    verified_count = validate_chronology(
        train=train,
        test=test,
        settlements=outcomes,
    )

    print(f"Chronological label check passed: {verified_count} training labels available.")

    print("\nCHRONOLOGICAL ML EXPERIMENT")
    print(f"Training: {TRAIN_MONTH}, {len(train)} contracts, {train['event'].nunique()} events")
    print(f"Testing:  {TEST_MONTH}, {len(test)} contracts, {test['event'].nunique()} events")

    y_train = train["y"].to_numpy()
    y_test = test["y"].to_numpy()

    variants = {
        "Market-only recalibration": ["market_logit"],
        "Market + quote quality": ["market_logit", "spread", "age_minutes"],
    }

    predictions = test[["market", "event", "month", "y", "p"]].copy()
    predictions = predictions.rename(columns={"p": "raw_market"})

    print("\nOCTOBER TEST PERFORMANCE")
    evaluate("Raw market", y_test, test["p"].to_numpy())

    for name, features in variants.items():
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=1.0,
                max_iter=1000,
                random_state=42,
            ),
        )

        model.fit(train[features], y_train)

        p_pred = model.predict_proba(test[features])[:, 1]

        column = "market_only" if len(features) == 1 else "market_plus_quality"
        predictions[column] = p_pred

        evaluate(name, y_test, p_pred)

    print("\nEQUAL-EVENT-WEIGHTED OCTOBER BRIER")
    for column in [
        "raw_market",
        "market_only",
        "market_plus_quality",
    ]:
        scores = (
            predictions.assign(squared_error=(predictions[column] - predictions["y"]) ** 2)
            .groupby("event")["squared_error"]
            .mean()
        )
        print(f"{column:<25}{scores.mean():.4f}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUT, index=False)

    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
