"""Save and load validated research datasets using Parquet."""

from pathlib import Path

import pandas as pd


def save_parquet(df: pd.DataFrame, path: str | Path) -> None:
    """Save a DataFrame to Parquet without modifying the input.

    Parameters
    ----------
    df:
        DataFrame to save.
    path:
        Destination file path.

    Side effects
    ------------
    Creates parent directories when necessary.
    Writes a Parquet file, replacing an existing file at the same path.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(destination, index=False, engine="pyarrow")


def load_parquet(path: str | Path) -> pd.DataFrame:
    """Load a previously saved Parquet dataset.

    Raises FileNotFoundError when the file does not exist.
    Does not modify the stored file.
    """
    return pd.read_parquet(path, engine="pyarrow")
