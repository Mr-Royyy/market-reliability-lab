# Market Reliability Lab

**Evaluating prediction-market probability reliability through historical market data, quote-quality analysis, and machine learning.**

Market Reliability Lab is a Python research project that investigates how reliably prediction-market prices forecast real-world outcomes.

The project uses historical Kalshi rainfall contracts to examine three questions:

1. How frequently are usable market quotes available at predetermined observation times?
2. How well do quoted market probabilities correspond to realized outcomes?
3. Can simple machine-learning models improve probability estimates using historical market probabilities and quote-quality features?

The research combines API data collection, historical market reconstruction, statistical evaluation, and chronological machine-learning experiments.

## Research Overview

Prediction-market prices are often interpreted as estimates of event probabilities. However, the reliability of those estimates depends on several factors, including quote availability, market liquidity, bid-ask spreads, and the timing of observations.

A quoted probability can be recent and have a narrow spread while still producing a substantial forecasting error.

Market Reliability Lab investigates this distinction between **quote quality** and **forecast accuracy**, with particular attention to avoiding look-ahead bias and misleading historical evaluations.

## Technology Stack

- **Python** — data collection, processing, and modeling
- **httpx** — Kalshi API requests
- **pandas and NumPy** — historical data processing
- **scikit-learn** — regularized logistic regression
- **SciPy** — statistical analysis
- **Matplotlib** — reliability visualization
- **pytest** — automated regression tests
- **Ruff** — linting and formatting

## Data Pipeline

The project collects historical rainfall-market information from Kalshi and reconstructs market observations at fixed calendar checkpoints.

The pipeline includes:

1. **Market discovery:** Identify rainfall market series, monthly events, and individual threshold contracts.
2. **Historical data retrieval:** Request historical candlestick data and handle pagination, time windows, retries, and duplicate records.
3. **Observation scheduling:** Establish predetermined calendar checkpoints rather than selecting observation times based on contract settlement or closure.
4. **Contract eligibility:** Include contracts only when their opening and closing times make them eligible for observation.
5. **Quote-quality filtering:** Evaluate historical quote freshness and bid-ask spread.
6. **Outcome matching:** Join historical observations to resolved YES/NO contract outcomes.
7. **Forecast evaluation:** Calculate Brier scores, log loss, and calibration diagnostics.

### Avoiding Look-Ahead Bias

A major methodological consideration is that rainfall threshold contracts may close before the end of their nominal observation period.

Selecting historical observations relative to a contract's actual closing time can introduce outcome-dependent timing.

To address this, the project uses fixed calendar checkpoints and evaluates whether each contract was eligible at the predetermined observation time.

The machine-learning experiment also verifies that training contracts were settled before the subsequent test prediction checkpoint.

## Historical Dataset

The current evaluation covers rainfall threshold contracts across ten city-level market series.

| Dataset characteristic | Value |
|---|---:|
| Historical months | September–October 2026 |
| City-month events | 20 |
| Selected contract observations | 69 |
| September observations | 36 |
| October observations | 33 |
| YES outcomes | 10 |
| NO outcomes | 59 |

The evaluation uses the 18:00 UTC checkpoint seven days before the end of each calendar month, subject to contract eligibility and a moderate quote-quality policy.

The moderate policy requires a quote age of at most 60 minutes and a bid-ask spread of at most 10 percentage points.

These filters define the evaluated subset; they do not imply that every listed rainfall contract had an eligible, usable quote.

## Baseline Probability Evaluation

Market midpoint probabilities are compared with final binary outcomes using proper scoring rules.

**Brier score** measures the squared difference between a predicted probability and its realized binary outcome:

\[
\text{Brier}=\frac{1}{N}\sum_{i=1}^{N}(p_i-y_i)^2
\]

**Log loss** penalizes incorrect predictions, particularly highly confident ones.

### Baseline Results

| Metric | Result |
|---|---:|
| Contract-weighted Brier score | 0.0606 |
| Contract-weighted log loss | 0.2035 |
| Equal-event-weighted Brier score | 0.0640 |
| Equal-event-weighted log loss | 0.2084 |

The equal-event-weighted evaluation first averages contract errors within each city-month event, then averages across events. This reduces the influence of events containing more selected contracts.

### Reliability Analysis

Observed calibration varies across probability ranges.

| Quoted probability range | Contracts | Mean predicted probability | Observed YES frequency |
|---|---:|---:|---:|
| 0–10% | 45 | 4.2% | 0.0% |
| 10–30% | 8 | 21.8% | 12.5% |
| 30–60% | 6 | 44.2% | 16.7% |
| 60–100% | 10 | 83.1% | 80.0% |

These results are exploratory. Several probability ranges contain too few contracts to support strong calibration conclusions.

## Machine-Learning Experiment

Two regularized logistic regression models are compared against the unmodified market probabilities.

**Model 1 — Market-only recalibration**

Uses the log-odds transformation of the market midpoint probability.

**Model 2 — Market probability + quote quality**

Uses the market log-odds, bid-ask spread, and quote age.

Both models use standardized features and L2-regularized logistic regression.

### Chronological Evaluation

The experiment trains on September 2026 observations and evaluates on October 2026 observations.

- Training: 36 contracts across 10 city-month events
- Testing: 33 contracts across 10 city-month events
- All 36 training labels verified as settled before the October 25 test checkpoint
- No overlapping training and testing events

### October Test Results

| Model | Brier score ↓ | Log loss ↓ | Equal-event-weighted Brier ↓ |
|---|---:|---:|---:|
| Raw market probability | 0.0357 | 0.1396 | 0.0442 |
| Market-only recalibration | **0.0307** | 0.1391 | 0.0343 |
| Market + quote quality | 0.0334 | **0.1356** | **0.0339** |

Market-only recalibration achieved an approximately **14% reduction in contract-weighted Brier score** relative to the raw market on the October evaluation set.

Adding quote-quality features produced the lowest log loss and equal-event-weighted Brier score, but did not improve contract-weighted Brier score relative to market-only recalibration.

These findings demonstrate an exploratory out-of-time comparison, not established predictive superiority across future markets.

## Engineering and Validation

The project includes reusable modules for:

- API access and HTTP retry handling
- Historical candlestick retrieval
- Market metadata normalization
- Observation scheduling and eligibility
- Historical quote reconstruction
- Data storage and dataset construction
- Forecast evaluation
- Chronological training-label validation

Automated tests cover the data-processing components and historical evaluation safeguards.

The chronological validation checks that training observations precede testing, training and testing events do not overlap, and training outcomes were available before test predictions.

### Running Tests

```bash
python -m pytest -q
python -m ruff check .
```

At the current development milestone, the project passes 78 automated tests.

## Running the Research

Install the project dependencies from the repository's Python project configuration.

From the repository root, the main research scripts include:

```bash
# Inventory resolved rainfall outcomes
python scripts/inventory_rainfall_outcomes.py

# Evaluate historical market probabilities
python scripts/evaluate_rainfall_baseline.py

# Analyze uncertainty
python scripts/evaluate_rainfall_uncertainty.py

# Generate reliability analysis
python scripts/plot_rainfall_reliability.py

# Run the chronological ML comparison
python scripts/evaluate_rainfall_ml.py
```

Some scripts depend on previously generated files in `data/processed/`. Execute the relevant upstream data-collection and evaluation stages before running downstream analyses.

## Limitations

**Limited historical coverage.** The current experiment covers only September and October 2026. Two months are insufficient to establish stable performance across seasons, cities, or market conditions.

**Small sample size.** The machine-learning experiment uses 36 training contracts and 33 test contracts. Results may be sensitive to individual outcomes.

**Correlated contracts.** Multiple rainfall threshold contracts within the same city-month event are related. Weather outcomes across cities in the same calendar month may also be correlated. Contract-level observations should not be interpreted as independent experiments.

**Selection bias.** The quote-quality policy excludes contracts without qualifying historical quotes. Results describe the selected subset rather than the entire market population.

**Historical quote limitations.** Reconstructed midpoint probabilities from candlestick data are not necessarily executable order-book prices. The project does not establish transaction costs, achievable fills, or trading profitability.

**Exploratory model development.** October outcomes were examined during the broader research process. The October comparison therefore should not be treated as a completely untouched prospective validation set.

**No demonstrated trading profitability.** Improvements in probability scoring do not necessarily translate into profitable trading strategies.

## Future Work

Potential extensions include expanding historical coverage, testing additional weather-market categories, introducing rolling chronological evaluation, comparing uncertainty-aware models, and examining whether quote-quality signals improve forecasts across independent market periods.

## Project Status

**Research prototype with validated chronological evaluation and automated testing.**

The current implementation establishes a reproducible foundation for studying prediction-market reliability. The primary focus is methodological rigor, historical data engineering, and interpretable statistical and machine-learning evaluation.