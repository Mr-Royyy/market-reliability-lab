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

Data-quality diagnostics: Before excluding records, measure how many fail each filter and why. This prevents silent data loss and helps identify selection bias. Initial market discovery is exploratory; final inclusion criteria will be justified using the observed data distribution.

Candlestick data quality: The initial NFL market returned 102 one-minute observations, including 76 candles with trade prices and 102 structurally valid bid–ask pairs. We will preserve missing prices, record quote spreads, detect missing timestamps, and avoid treating repeated observations from one market as independent outcomes. Quote midpoints and trade prices will be evaluated as separate baselines. These findings are exploratory and do not establish general market-wide data quality.

Candlestick normalization: Raw Kalshi JSON is converted into flat Python dictionaries using a pure, independently tested transformation function. Missing trade prices remain None; invalid probabilities, negative volumes, and crossed quotes are rejected. Bid–ask spreads and midpoints are calculated only when both quotes are available. We preserve raw data separately so normalization can be audited and reproduced.

Pandas dataset builder: We use pandas to combine normalized candlesticks into chronologically ordered research tables. Explicit quality flags distinguish transaction prices, structurally valid quotes, and quote midpoints passing an exploratory spread threshold. We preserve flagged observations rather than deleting them, allowing sensitivity analyses and transparent reporting of data exclusions. The builder is a pure transformation and is tested without network access.

Parquet and PyArrow: We use Parquet for persistent, column-oriented research datasets and PyArrow as the serialization engine. This preserves timestamps and numeric types while supporting efficient storage and later analysis with pandas or DuckDB. Storage functions are isolated from API retrieval and normalization, with round-trip tests verifying data integrity. Exploratory output files are excluded from Git.

### Formatting
Ruff: Used for Python linting, import organization, and automatic formatting. It enforces consistent code style and catches certain programming mistakes before code is committed. Unlike pytest, Ruff does not verify the mathematical correctness of our algorithms.

## HTTPX and Kalshi REST API

### HTTPX
Purpose: Retrieve market data over HTTP.

Why:
- Explicit request timeouts
- HTTP status error handling
- Connection management
- Supports asynchronous requests if needed later

### Kalshi REST API
Purpose: Obtain real prediction-market records.

Initial endpoint:
GET /trade-api/v2/markets

Initial design:
- Public, read-only requests
- No trading credentials
- Small sample requests before bulk collection
- Inspect response schemas before defining data models

### Research safeguards
- Do not treat current market fields as historical observations.
- Distinguish market close, expiration, and settlement times.
- Verify that features existed before the forecast timestamp.
- Preserve raw values and missing-data information.

### Point-in-Time Snapshot Design

The project constructs forecast observations from historical Kalshi candlesticks using fixed horizons before market close.

The current exploratory horizons are 15, 30, and 45 minutes. Each snapshot uses the most recent usable bid–ask midpoint within a five-minute freshness window, subject to the existing quote-validity and maximum-spread filters.

A five-event NYC hourly temperature audit examined 47 contracts per horizon. Snapshot coverage was 91.5% at 15 minutes, 89.4% at 30 minutes, and 87.2% at 45 minutes.

These results demonstrate preliminary data availability, not predictive accuracy or population-wide coverage.

Contracts within the same Kalshi event share an underlying hourly temperature measurement. Consecutive hourly events within the same city and date may also be dependent. The planned evaluation will therefore use grouped, chronological splits rather than random contract-level splits.

**Current limitations:** Candlestick bid–ask midpoint availability does not guarantee executable prices, quote freshness within the candle, or absence of information leakage. Spread and freshness thresholds remain provisional. The dataset must preserve missing snapshots, observation timestamps, forecast horizons, and grouping identifiers.