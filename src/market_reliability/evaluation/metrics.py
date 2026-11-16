"""Metrics for evaluating binary probability forecasts."""

import numpy as np
from numpy.typing import ArrayLike


def brier_score(
    probabilities: ArrayLike,
    outcomes: ArrayLike,
) -> float:
    """
    Compute the mean Brier score.

    The Brier score measures accuracy of predictions (squared prediction error):

        mean((predicted_probability - actual_outcome) ** 2)

    Parameters
    ----------
    probabilities:
        One-dimensional collection of predicted probabilities
        between 0 and 1.

    outcomes:
        Corresponding observed binary outcomes (0 or 1).

    Returns
    -------
    float:
        Average squared error. Lower is better.

    Notes
    -----
    This function does not modify inputs or save data.
    """
    # Convert the inputs into numerical NumPy arrays.
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(outcomes, dtype=float)

    # Require one-dimensional, nonempty, equally sized arrays.
    if p.ndim != 1 or y.ndim != 1:
        raise ValueError("Inputs must be one-dimensional.")

    if p.size == 0 or p.size != y.size:
        raise ValueError("Inputs must be nonempty and equal in length.")

    # Missing values and infinity would invalidate the result.
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(y)):
        raise ValueError("Inputs must contain only finite values.")

    # Forecasts are probabilities, so values must be in [0, 1].
    if np.any((p < 0) | (p > 1)):
        raise ValueError("Probabilities must be between 0 and 1.")

    # We currently evaluate only binary event outcomes.
    if not np.all((y == 0) | (y == 1)):
        raise ValueError("Outcomes must be binary (0 or 1).")

    # Calculate the squared error for each observation.
    squared_errors = (p - y) ** 2

    # Return the mean as a standard Python float.
    return float(np.mean(squared_errors))
