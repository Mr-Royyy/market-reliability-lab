## NumPy and pytest

### NumPy
Used for vectorized numerical calculations.

Why:
- Efficient operations over arrays
- Widely used in scientific Python and ML
- Allows concise mathematical implementations

### pytest
Used to verify correctness through automated tests.

Why:
- Supports parameterized testing
- Integrates with VS Code and CI
- Helps catch regressions when code changes

### Engineering decision
We implemented the Brier score ourselves for transparency
and tested it against scikit-learn.

For more complex ML methods, we will generally use established
libraries rather than unnecessarily reimplementing algorithms.

### Formatting
Ruff: Used for Python linting, import organization, and automatic formatting. It enforces consistent code style and catches certain programming mistakes before code is committed. Unlike pytest, Ruff does not verify the mathematical correctness of our algorithms.