"""Exploratory reliability diagram for rainfall prediction markets."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

INPUT = Path("data/processed/rainfall_baseline_observations.csv")
OUTPUT = Path("data/processed/rainfall_reliability.png")

BINS = [0.0, 0.10, 0.30, 0.60, 1.0]


def main() -> None:
    df = pd.read_csv(INPUT)

    if df.empty:
        raise ValueError("No observations")

    if not df["p"].between(0, 1).all():
        raise ValueError("Invalid probabilities")

    df["bin"] = pd.cut(
        df["p"],
        bins=BINS,
        include_lowest=True,
    )

    calibration = (
        df.groupby("bin", observed=True)
        .agg(
            count=("y", "size"),
            predicted=("p", "mean"),
            observed=("y", "mean"),
            yes=("y", "sum"),
        )
        .reset_index()
    )

    print("\nRELIABILITY TABLE")
    print(calibration.to_string(index=False))

    fig, ax = plt.subplots(figsize=(7, 6))

    ax.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        color="gray",
        label="Perfect calibration",
    )

    ax.scatter(
        calibration["predicted"],
        calibration["observed"],
        s=calibration["count"] * 18,
        alpha=0.8,
        label="Observed bins",
    )

    for row in calibration.itertuples():
        ax.annotate(
            f"n={row.count}",
            (row.predicted, row.observed),
            xytext=(7, 7),
            textcoords="offset points",
        )

    ax.set(
        xlabel="Mean market-implied probability",
        ylabel="Observed YES frequency",
        title="Rainfall Market Reliability (Sep–Oct 2026)",
        xlim=(0, 1),
        ylim=(0, 1),
    )

    ax.legend()
    ax.grid(alpha=0.2)

    fig.text(
        0.5,
        0.01,
        "Exploratory: 69 selected contracts across 20 dependent city-month events",
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(rect=(0, 0.04, 1, 1))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=180)
    plt.close(fig)

    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
