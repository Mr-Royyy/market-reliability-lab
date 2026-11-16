"""Exploratory benchmarks and event-clustered Brier uncertainty."""

import numpy as np
import pandas as pd

INPUT = "data/processed/rainfall_baseline_observations.csv"
BOOTSTRAPS = 5000
SEED = 42


def main() -> None:
    df = pd.read_csv(INPUT)

    if df.empty:
        raise ValueError("No observations")

    if df["market"].duplicated().any():
        raise ValueError("Duplicate contract observations")

    if not df["p"].between(0, 1).all():
        raise ValueError("Invalid probabilities")

    if not df["y"].isin([0, 1]).all():
        raise ValueError("Invalid outcomes")

    df["market_brier"] = (df["p"] - df["y"]) ** 2
    df["always_no_brier"] = df["y"].astype(float)
    df["half_brier"] = (0.5 - df["y"]) ** 2

    event_scores = (
        df.groupby("event")
        .agg(
            market=("market_brier", "mean"),
            always_no=("always_no_brier", "mean"),
            half=("half_brier", "mean"),
            contracts=("market", "size"),
        )
        .reset_index()
    )

    print("\nEXPLORATORY BENCHMARKS")
    print(f"Contracts: {len(df)}")
    print(f"Event groups: {len(event_scores)}")

    print("\nEQUAL-EVENT-WEIGHTED BRIER")
    print(f"Market:     {event_scores['market'].mean():.4f}")
    print(f"Always NO:  {event_scores['always_no'].mean():.4f}")
    print(f"Always 50%: {event_scores['half'].mean():.4f}")

    event_scores["improvement"] = event_scores["always_no"] - event_scores["market"]

    rng = np.random.default_rng(SEED)
    n_events = len(event_scores)

    indices = rng.integers(
        low=0,
        high=n_events,
        size=(BOOTSTRAPS, n_events),
    )

    market_scores = event_scores["market"].to_numpy()
    improvements = event_scores["improvement"].to_numpy()

    boot_market = market_scores[indices].mean(axis=1)
    boot_improvement = improvements[indices].mean(axis=1)

    market_ci = np.quantile(boot_market, [0.025, 0.975])
    improvement_ci = np.quantile(boot_improvement, [0.025, 0.975])

    print("\nEVENT-CLUSTERED BOOTSTRAP")
    print(f"Market Brier 95% interval: [{market_ci[0]:.4f}, {market_ci[1]:.4f}]")

    print(f"Improvement over always-NO: {event_scores['improvement'].mean():.4f}")

    print(f"Improvement 95% interval: [{improvement_ci[0]:.4f}, {improvement_ci[1]:.4f}]")

    print(f"Bootstrap fraction with positive improvement: {(boot_improvement > 0).mean():.3f}")

    print("\nMONTHLY EVENT-WEIGHTED SCORES")
    event_scores["month"] = event_scores["event"].str.extract(r"-(\d{2}[A-Z]{3})$")

    print(event_scores.groupby("month")[["market", "always_no", "improvement"]].mean().to_string())


if __name__ == "__main__":
    main()
