"""Audit the first labeled temperature research dataset."""

from pathlib import Path

import pandas as pd

PATH = Path("data/processed/temperature_sample.parquet")


def main() -> None:
    df = pd.read_parquet(PATH)

    print("\nDATASET STRUCTURE")
    print("Rows:", len(df))
    print("Unique markets:", df["market_ticker"].nunique())
    print("Unique events:", df["event_ticker"].nunique())
    print("Unique underlying groups:", df["underlying_group"].nunique())

    print("\nOUTCOME DISTRIBUTION")
    contracts = df.drop_duplicates("market_ticker")
    print(contracts["outcome"].value_counts(dropna=False))

    print("\nSNAPSHOT COVERAGE")
    print(df.groupby("horizon_minutes")["has_snapshot"].agg(["count", "sum", "mean"]))

    usable = df.loc[df["has_snapshot"]].copy()

    print("\nPROBABILITY DISTRIBUTION")
    print(usable.groupby("horizon_minutes")["midpoint"].describe().round(3))

    print("\nUNCERTAIN FORECASTS")
    usable["uncertain"] = usable["midpoint"].between(0.2, 0.8)

    print(usable.groupby("horizon_minutes")["uncertain"].agg(["sum", "count", "mean"]))

    print("\nQUOTE TIMING CHECK")
    invalid_timing = usable.loc[
        (usable["quote_time_utc"] > usable["cutoff_utc"])
        | (usable["quote_age_minutes"] < 0)
        | (usable["quote_age_minutes"] > 5)
    ]
    print("Invalid quote timing rows:", len(invalid_timing))

    print("\nDUPLICATE OBSERVATIONS")
    duplicates = df.duplicated(["market_ticker", "horizon_minutes"]).sum()
    print("Duplicate market/horizon rows:", duplicates)

    print("\nEVENT-LEVEL OUTCOMES")
    print(contracts.groupby("event_ticker")["outcome"].agg(["count", "sum", "mean"]))


if __name__ == "__main__":
    main()
