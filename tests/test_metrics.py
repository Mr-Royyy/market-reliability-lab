"""Tests for probability forecast evaluation metrics."""

import pytest
from sklearn.metrics import brier_score_loss

from market_reliability.evaluation.metrics import brier_score


def test_perfect_predictions():
    """Perfect predictions should produce zero error."""
    result = brier_score([1.0, 0.0], [1, 0])

    assert result == pytest.approx(0.0)


def test_known_example():
    """Compare the function against a manually calculated result."""
    result = brier_score([0.8, 0.4, 0.7], [1, 0, 1])

    assert result == pytest.approx(0.0966666667)


def test_matches_sklearn():
    """Verify agreement with scikit-learn's implementation."""
    probabilities = [0.2, 0.6, 0.9]
    outcomes = [0, 1, 1]

    result = brier_score(probabilities, outcomes)
    expected = brier_score_loss(outcomes, probabilities)

    assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    "probabilities,outcomes",
    [
        ([], []),
        ([0.2], [0, 1]),
        ([1.2], [1]),
        ([float("nan")], [0]),
        ([0.5], [2]),
        ([[0.2, 0.3]], [[0, 1]]),
    ],
)
def test_invalid_inputs(probabilities, outcomes):
    """Invalid data should be rejected."""
    with pytest.raises(ValueError):
        brier_score(probabilities, outcomes)
