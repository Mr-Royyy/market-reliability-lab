## Running the Research

### Requirements

- Python 3.11 or 3.12
- Internet access to retrieve historical Kalshi market data
- Access to the public Kalshi API

Run the following commands from the repository root.

### 1. Install Dependencies

Create and activate a virtual environment.

**Windows PowerShell:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

### 2. Generate Historical Data

Retrieve the settlement outcomes for the historical rainfall contracts.

```powershell
python scripts/inventory_rainfall_outcomes.py
```

Generate the September and October 2026 historical quote audits.

```powershell
python scripts/audit_cross_city_calendar.py --month 26SEP
python scripts/audit_cross_city_calendar.py --month 26OCT
```

These scripts produce:

- `data/processed/rainfall_outcome_inventory.csv`
- `data/processed/september_calendar_audit.csv`
- `data/processed/october_calendar_audit.csv`

Historical quote observations are selected at predetermined calendar checkpoints. The evaluation uses the `month_end_minus_7d` checkpoint at 18:00 UTC and the moderate quote-quality policy.

### 3. Reproduce the Baseline Evaluation

```powershell
python scripts/evaluate_rainfall_baseline.py
```

This generates `data/processed/rainfall_baseline_observations.csv`, containing the selected market probabilities, settlement outcomes, and forecast errors.

The verified historical evaluation contains 69 contracts across 20 city-month events, with a contract-weighted Brier score of approximately 0.0606.

### 4. Reproduce the Chronological ML Experiment

```powershell
python scripts/evaluate_rainfall_ml.py
```

The experiment trains on September 2026 and evaluates on October 2026. It checks that the September training labels were available before the October prediction checkpoint.

The script compares raw market probabilities, market-only logistic recalibration, and recalibration using additional quote-quality features.

Predictions are saved to `data/processed/rainfall_ml_predictions.csv`.

### 5. Generate Additional Diagnostics

```powershell
python scripts/evaluate_rainfall_uncertainty.py
python scripts/plot_rainfall_reliability.py
```

These scripts provide event-cluster bootstrap uncertainty estimates and descriptive probability-calibration visualizations.

### 6. Run Automated Checks

```powershell
python -m pytest -q
python -m ruff check .
```

At the time of the verified reproduction, all 78 automated tests passed.

### Reproducibility Notes

The historical data collection, baseline evaluation, and chronological ML prediction stages were regenerated and compared with their original outputs. The 69 baseline observations and 33 October ML prediction records matched exactly.

Generated datasets are intentionally excluded from version control and must be regenerated using the commands above.

Reproduction depends on continued availability and consistency of historical Kalshi API responses. Matching results on the development machine does not guarantee identical future API responses or establish out-of-sample generalization beyond the evaluated months.