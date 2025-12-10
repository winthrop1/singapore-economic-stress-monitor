# Singapore Economic Stress Monitor - Technical Guide

**Complete Technical Documentation for Developers**

This guide provides deep technical understanding of the application architecture, algorithms, design decisions, and implementation details. Read this if you need to:
- Understand how the system works internally
- Modify or extend the codebase
- Debug issues or optimize performance
- Explain the methodology to stakeholders

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Data Pipeline](#2-data-pipeline)
3. [Normalization Algorithm](#3-normalization-algorithm)
4. [Composite Scoring Logic](#4-composite-scoring-logic)
5. [Visualization System](#5-visualization-system)
6. [Configuration Management](#6-configuration-management)
7. [Design Decisions & Rationale](#7-design-decisions--rationale)
8. [Code Quality Patterns](#8-code-quality-patterns)
9. [Performance Considerations](#9-performance-considerations)
10. [Extending the System](#10-extending-the-system)
11. [Common Issues & Solutions](#11-common-issues--solutions)

---

## 1. System Architecture

### 1.1 High-Level Overview

The application follows a **pipeline architecture** with six distinct stages:

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   API Fetch │ -> │  Transform   │ -> │ Data Loader │ -> │  Normalizer  │
│   (Optional)│    │  (Optional)  │    │  (Required) │    │  (Required)  │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                                                  │
                                                                  v
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Visualizer  │ <- │    Scorer    │ <- │ (normalized │
│  (Optional) │    │  (Required)  │    │     data)   │
└─────────────┘    └──────────────┘    └─────────────┘
```

**Module Responsibilities:**

| Module | File | Purpose | Can Skip? |
|--------|------|---------|-----------|
| **API Fetch** | `fetch_singstat_api.py` | Download raw data from data.gov.sg | Yes (if using manual data) |
| **Transform** | `transform_data.py` | Convert wide → long format | Yes (if data already clean) |
| **Data Loader** | `src/data_loader.py` | Load, resample, align CSVs | No |
| **Normalizer** | `src/normalizer.py` | Calculate z-scores, sigmoid transform | No |
| **Scorer** | `src/stress_scorer.py` | Weighted composite, alert classification | No |
| **Visualizer** | `src/visualizer.py` | Generate 4 charts | Yes (use `--no-charts`) |

### 1.2 Project Structure

```
singapore-economic-stress-monitor/
├── config.py                    # Centralized configuration
├── main.py                      # Orchestration script
├── fetch_singstat_api.py        # API client
├── transform_data.py            # Data transformation
│
├── src/                         # Core modules
│   ├── __init__.py
│   ├── data_loader.py           # CSV loading & alignment
│   ├── normalizer.py            # Statistical normalization
│   ├── stress_scorer.py         # Composite scoring
│   └── visualizer.py            # Chart generation
│
├── data/                        # Economic indicator CSVs
│   ├── gdp.csv                  # Raw API data (wide format)
│   ├── gdp_clean.csv            # Transformed (long format)
│   ├── cpi.csv
│   ├── cpi_clean.csv
│   ├── unemployment.csv
│   └── unemployment_clean.csv
│
├── output/                      # Generated charts
│   ├── stress_timeseries.png
│   ├── component_breakdown.png
│   ├── correlation_heatmap.png
│   └── alert_timeline.png
│
├── README.md                    # User-facing overview
├── USAGE.md                     # Detailed usage instructions
└── TECHNICAL_GUIDE.md           # This file
```

### 1.3 Data Flow Diagram

```
Raw API Data (Wide Format)
└─> SingStat CSVs with columns: [_id, DataSeries, 20251Q, 20252Q, 20253Q, ...]
    │
    v
Transformation (transform_data.py)
└─> Clean CSVs: [date, value]
    │
    v
Loading (data_loader.py)
├─> Parse dates: "2025-Q3" → Timestamp('2025-07-01')
├─> Resample quarterly → monthly (forward-fill)
└─> Align to common date range
    │
    v
Normalization (normalizer.py)
├─> Calculate rolling z-scores (36-month window)
├─> Apply directional inversion (GDP × -1)
└─> Sigmoid transform to 0-100 scale
    │
    v
Scoring (stress_scorer.py)
├─> Weighted composite: Σ(weight_i × score_i)
└─> Classify alerts: Green/Amber/Red
    │
    v
Visualization (visualizer.py)
└─> Generate 4 PNG charts
```

---

## 2. Data Pipeline

### 2.1 Stage 1: API Fetching

**File:** `fetch_singstat_api.py`

#### Why Multiple API Patterns?

The data.gov.sg API has evolved over time. The script tries 6 different endpoint patterns:

```python
API_ENDPOINTS = [
    # Modern v2 API (preferred)
    "https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/poll-download",

    # Legacy direct search
    "https://data.gov.sg/api/action/datastore_search?resource_id={dataset_id}&limit=10000",

    # CKAN-style download
    "https://data.gov.sg/dataset/{dataset_id}/download",

    # Beta API
    "https://beta.data.gov.sg/api/3/action/datastore_search?resource_id={dataset_id}&limit=10000",

    # v1 initiate-download
    "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/initiate-download",

    # v2 initiate-download (current best practice)
    "https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/initiate-download",
]
```

#### Initiate-Download Pattern

The recommended approach:

```python
def initiate_download(dataset_id):
    # Step 1: Request download URL
    response = requests.get(f".../{dataset_id}/initiate-download")

    # Response: {"data": {"url": "https://storage.../download_url"}}
    download_url = response.json()["data"]["url"]

    # Step 2: Download CSV from storage URL
    csv_data = requests.get(download_url)
    return pd.read_csv(StringIO(csv_data.text))
```

**Why this pattern?**
- Separates API logic from file storage
- Handles large files (storage URLs don't timeout)
- Follows modern API design (async download)

#### Dataset IDs

```python
DATASETS = {
    "gdp": "d_a5ff719648a0e6d4b4c623ee383ab686",
    "cpi": "d_bdaff844e3ef89d39fceb962ff8f0791",
    "unemployment": "d_b816a930bca0eb19fdf20fcbfcdd4c39"
}
```

These IDs are permanent identifiers in data.gov.sg's catalog.

### 2.2 Stage 2: Data Transformation

**File:** `transform_data.py`

#### The Wide Format Problem

Raw SingStat CSV structure:

```csv
_id,DataSeries,19761Q,19762Q,19763Q,...,20253Q,20254Q
1234,GDP At Current Market Prices,5.2,6.1,7.3,...,8.6,9.1
```

**Problems:**
1. Date information is in column headers (not rows)
2. Column names like `20253Q` are non-standard
3. Multiple data series in one file (need to extract specific row)
4. Can't parse with standard `pd.read_csv(parse_dates=['date'])`

#### Transformation Process

```python
def transform_unemployment(filepath: str) -> pd.DataFrame:
    # 1. Load raw CSV
    df = pd.read_csv(filepath)
    # Shape: (50 rows, 200 columns) - wide format

    # 2. Select target row
    target_row = df[df['DataSeries'].str.contains('Total Unemployment Rate')]
    # Now: (1 row, 200 columns)

    # 3. Extract date columns
    date_cols = [c for c in df.columns if re.match(r'\d{4}\dQ', c)]
    # ['19921Q', '19922Q', ..., '20254Q']

    # 4. Transform to long format
    records = []
    for col in date_cols:
        date_str = parse_quarter_date(col)  # "20253Q" → "2025-Q3"
        value = target_row[col].values[0]
        records.append({'date': date_str, 'value': float(value)})

    # 5. Create DataFrame
    result = pd.DataFrame(records)
    # Shape: (135 rows, 2 columns) - long format

    return result.sort_values('date')
```

#### Date Parsing Logic

```python
def parse_quarter_date(col: str) -> str:
    """
    Convert column name to parseable date string.

    Examples:
        "20253Q" → "2025-Q3"
        "2025Oct" → "2025-10"
    """
    # Quarterly: "20253Q" (year + quarter + Q)
    if match := re.match(r'(\d{4})(\d)Q', col):
        year = match.group(1)
        quarter = match.group(2)
        return f"{year}-Q{quarter}"

    # Monthly: "2025Oct"
    if match := re.match(r'(\d{4})([A-Za-z]+)', col):
        year = match.group(1)
        month_str = match.group(2)
        month_num = MONTH_MAP[month_str]  # 'Oct' → '10'
        return f"{year}-{month_num}"
```

### 2.3 Stage 3: Data Loading

**File:** `src/data_loader.py`

#### Parsing Quarter Dates

```python
def parse_dates(date_str: str) -> pd.Timestamp:
    """
    Convert date strings to pandas Timestamp.

    Quarter mapping:
        Q1 → January 1   (Jan-Mar)
        Q2 → April 1     (Apr-Jun)
        Q3 → July 1      (Jul-Sep)
        Q4 → October 1   (Oct-Dec)
    """
    if 'Q' in date_str:
        # "2025-Q3" → Timestamp('2025-07-01')
        parts = date_str.upper().split('-Q')
        year = int(parts[0])
        quarter = int(parts[1])
        month = (quarter - 1) * 3 + 1  # Q3 → 7 (July)
        return pd.Timestamp(year=year, month=month, day=1)

    # Monthly: "2025-10" → Timestamp('2025-10-01')
    return pd.to_datetime(date_str)
```

**Why map quarters to month-start?**
- Quarterly data represents 3-month periods
- Need specific date for pandas DatetimeIndex
- Choose **start of quarter** as convention
- Consistent with monthly data (all dates are month-start)

#### Resampling Quarterly → Monthly

```python
def resample_to_monthly(df: pd.DataFrame, method: str = 'ffill') -> pd.DataFrame:
    """
    Convert quarterly data to monthly frequency.

    Example:
        Input (quarterly):
            2025-01-01    5.2  (Q1)
            2025-04-01    8.6  (Q2)

        Output (monthly):
            2025-01-01    5.2  (original)
            2025-02-01    5.2  (forward-filled)
            2025-03-01    5.2  (forward-filled)
            2025-04-01    8.6  (original)
            2025-05-01    8.6  (forward-filled)
            2025-06-01    8.6  (forward-filled)
    """
    # Resample to month-start frequency
    df_monthly = df.resample('MS').first()

    # Forward-fill to propagate quarterly values
    df_monthly = df_monthly.fillna(method='ffill')

    return df_monthly
```

**Why forward-fill instead of interpolation?**

| Method | Example | Pros | Cons |
|--------|---------|------|------|
| **Forward-fill** | Q1=5.2 → Jan=5.2, Feb=5.2, Mar=5.2 | Honest (no fake data) | Step function (discontinuous) |
| **Interpolation** | Q1=5.2, Q2=8.6 → Jan=5.2, Feb=6.3, Mar=7.4 | Smooth curve | Creates artificial values |
| **Backward-fill** | Q1=5.2 → Nov=5.2, Dec=5.2, Jan=5.2 | Could work | Logically inconsistent (future data) |

**Decision:** Forward-fill preserves data integrity. GDP growth in Q1 applies to the entire quarter.

#### Alignment Logic

```python
def align_indicators(data_dict: Dict[str, pd.DataFrame]) -> Tuple[...]:
    """
    Align all indicators to common date range.

    Example:
        GDP:          1976-01 to 2025-04  (592 months)
        CPI:          1961-01 to 2025-04  (772 months)
        Unemployment: 1992-01 to 2025-04  (400 months)

        Common range: 1992-01 to 2025-04  (400 months)
    """
    # Find intersection
    common_start = max(df.index.min() for df in data_dict.values())
    common_end = min(df.index.max() for df in data_dict.values())

    # Create common date index
    common_dates = pd.date_range(start=common_start, end=common_end, freq='MS')

    # Reindex each indicator
    aligned_data = {}
    for name, df in data_dict.items():
        aligned_data[name] = df.reindex(common_dates)

    return aligned_data, common_dates
```

**Why alignment matters:**
- Can't calculate composite score if indicators have different date ranges
- Z-score normalization requires aligned time series
- Missing data in common range is flagged with warnings

---

## 3. Normalization Algorithm

**File:** `src/normalizer.py`

### 3.1 Rolling Z-Score Calculation

#### Mathematical Formula

```
z_t = (x_t - μ_36) / σ_36

where:
  x_t    = current value at time t
  μ_36   = mean of trailing 36 months
  σ_36   = std dev of trailing 36 months
```

#### Implementation

```python
def calculate_rolling_zscore(series: pd.Series, window: int = 36) -> pd.Series:
    """
    Calculate rolling z-score with 36-month window.

    Example:
        Month    GDP    36m_mean  36m_std   Z-Score
        -------  -----  --------  -------   -------
        Jan 92   4.5    -         -         NaN (insufficient data)
        ...
        Dec 94   5.2    4.8       1.5       (5.2-4.8)/1.5 = 0.27
        Jan 95   8.0    5.0       2.0       (8.0-5.0)/2.0 = 1.50
        Feb 95   3.5    5.0       2.0       (3.5-5.0)/2.0 = -0.75
    """
    # Calculate rolling statistics
    rolling_mean = series.rolling(window=window, min_periods=24).mean()
    rolling_std = series.rolling(window=window, min_periods=24).std()

    # Calculate z-score
    z_score = (series - rolling_mean) / rolling_std

    # Handle edge cases
    z_score = z_score.replace([np.inf, -np.inf], np.nan)

    return z_score
```

#### Why Rolling Window?

**Fixed baseline alternative:**
```python
# Fixed baseline (NOT USED)
mean_2000_2010 = series['2000':'2010'].mean()
std_2000_2010 = series['2000':'2010'].std()
z = (series - mean_2000_2010) / std_2000_2010
```

**Problems with fixed baseline:**
- 2020 COVID shock would show extreme z-scores (+5.0)
- Doesn't adapt to structural economic changes
- Pre-2000 data incomparable to post-2020

**Rolling window advantages:**
- **Adaptive:** Mean/std adjust to changing economy
- **Comparable:** Z-scores represent "recent abnormality"
- **Regime-aware:** Post-COVID normal ≠ pre-COVID normal

#### Window Size Trade-offs

| Window | Pros | Cons | Use Case |
|--------|------|------|----------|
| **12 months** | Highly responsive | Very volatile | Real-time trading |
| **24 months** | Responsive | Somewhat volatile | Short-term forecasting |
| **36 months** | Balanced | Good stability | Strategic monitoring (CHOSEN) |
| **60 months** | Very stable | Slow to react | Long-term trends |

**Why 36 months?**
- Captures one business cycle (~3 years)
- Smooths seasonal volatility
- Responds to structural changes within 3 years

#### First 36 Months Problem

```python
# Configuration
MIN_PERIODS_FOR_ZSCORE = 24  # Minimum data points required

# Data:
# 1992-01: 1 month  → z-score = NaN (need 24 months)
# 1992-12: 12 months → z-score = NaN (need 24 months)
# 1993-12: 24 months → z-score = -0.3 (first valid score with min_periods=24)
# 1994-12: 36 months → z-score = 0.5 (first full 36-month window)
```

**Impact:**
- First **23 months** have no stress scores (1992-01 to 1993-11)
- Valid scoring starts: 1993-12 (with 24-month window)
- Fully mature scores: 1994-12 (with 36-month window)

### 3.2 Directional Inversion

#### The Problem

Raw economic indicators have different directionality:

| Indicator | Higher Value Means | Raw Direction |
|-----------|-------------------|---------------|
| **Unemployment** | More job loss | More stress ✓ |
| **CPI (Inflation)** | Higher prices | More stress ✓ |
| **GDP Growth** | Stronger economy | **Less stress** ✗ |

For composite scoring, we need **all indicators to point the same way**:
- Higher value = **MORE stress** (always)

#### Implementation

```python
INVERT_INDICATORS = ['gdp']  # In config.py

def apply_directional_inversion(data_dict):
    """
    Invert GDP so higher values mean MORE stress.

    Example:
        Before:
            GDP = +8.0%  (strong growth)
            GDP = -2.0%  (recession)

        After:
            GDP = -8.0%  (inverted strong growth → low stress)
            GDP = +2.0%  (inverted recession → high stress)
    """
    inverted_data = {}

    for indicator_name, df in data_dict.items():
        if indicator_name in config.INVERT_INDICATORS:
            df['value'] = -df['value']  # Multiply by -1

        inverted_data[indicator_name] = df

    return inverted_data
```

#### Effect on Z-Scores

```python
# Before inversion:
GDP = +8.0% (strong growth)
Mean = +5.0%, Std = 2.0%
Z-score = (8.0 - 5.0) / 2.0 = +1.5  → Would give HIGH stress ✗

# After inversion:
GDP = -8.0% (inverted)
Mean = -5.0% (inverted), Std = 2.0%
Z-score = (-8.0 - (-5.0)) / 2.0 = -1.5  → Gives LOW stress ✓

# Recession case:
GDP = -2.0% (recession, before inversion)
GDP = +2.0% (after inversion)
Mean = -5.0% (inverted), Std = 2.0%
Z-score = (2.0 - (-5.0)) / 2.0 = +3.5  → Gives HIGH stress ✓
```

### 3.3 Sigmoid Transformation

#### Mathematical Formula

```
score = 100 / (1 + e^(-z))

where:
  z = z-score (unbounded, -∞ to +∞)
  score = stress score (bounded, 0 to 100)
```

#### Sigmoid Properties

```python
import numpy as np

def sigmoid_transform(z_score: float) -> float:
    """
    Transform z-score to 0-100 scale using sigmoid function.

    Key properties:
    1. Bounded: Output always in [0, 100]
    2. Smooth: Continuous, differentiable
    3. Centered: z=0 → score=50
    4. Asymptotic: Extreme z-scores → 0 or 100
    """
    return 100.0 / (1.0 + np.exp(-z_score))

# Examples:
sigmoid_transform(-3.0)  # → 4.74  (very low stress)
sigmoid_transform(-2.0)  # → 11.92
sigmoid_transform(-1.0)  # → 26.89
sigmoid_transform(0.0)   # → 50.00 (neutral)
sigmoid_transform(1.0)   # → 73.11
sigmoid_transform(2.0)   # → 88.08
sigmoid_transform(3.0)   # → 95.26 (very high stress)
```

#### Why Sigmoid? (vs Alternatives)

**Alternative 1: Linear Scaling**
```python
# Map [-3, +3] to [0, 100]
score = ((z_score + 3) / 6) * 100

# Problems:
# - z-scores can exceed ±3 (especially during crises)
# - Would give negative scores or >100 scores
# - Sharp cutoffs at boundaries
```

**Alternative 2: Min-Max Scaling**
```python
# Map [historical_min, historical_max] to [0, 100]
score = (z_score - z_min) / (z_max - z_min) * 100

# Problems:
# - Breaks when new extreme occurs
# - Not statistically principled
# - Requires recomputing all historical scores
```

**Sigmoid advantages:**
1. **Asymptotic:** Handles extreme values gracefully
2. **Bounded:** Guaranteed [0, 100] range
3. **Smooth:** No discontinuities or sharp cutoffs
4. **Interpretable:** z=0 always maps to 50
5. **Standard:** Used in logistic regression, neural networks

#### Steepness Parameter

```python
SIGMOID_STEEPNESS = 1.0  # Default

# Effect of different steepness values:
def sigmoid(z, steepness):
    return 100 / (1 + np.exp(-steepness * z))

# steepness = 0.5 (gentle curve)
sigmoid(1.0, 0.5) → 62.2  (less extreme)
sigmoid(2.0, 0.5) → 73.1

# steepness = 1.0 (standard - USED)
sigmoid(1.0, 1.0) → 73.1
sigmoid(2.0, 1.0) → 88.1

# steepness = 2.0 (sharp curve)
sigmoid(1.0, 2.0) → 88.1  (more extreme)
sigmoid(2.0, 2.0) → 98.2
```

**Chosen value: 1.0**
- Balanced between sensitivity and stability
- Standard logistic sigmoid
- Empirically validated on historical data

---

## 4. Composite Scoring Logic

**File:** `src/stress_scorer.py`

### 4.1 Weighted Average Formula

```
Composite Score = Σ(w_i × score_i)
                = (w_gdp × score_gdp) + (w_cpi × score_cpi) + (w_unemp × score_unemp)
                = (0.35 × score_gdp) + (0.35 × score_cpi) + (0.30 × score_unemp)
```

### 4.2 Weight Selection Rationale

```python
INDICATOR_WEIGHTS = {
    'gdp': 0.35,         # 35%
    'cpi': 0.35,         # 35%
    'unemployment': 0.30 # 30%
}
```

#### Why Equal Weight for GDP & CPI?

**GDP (35%)**
- Broadest measure of economic health
- **Forward-looking:** Leads unemployment by 1-2 quarters
- Impacts financial planning, savings, and purchasing power
- Systemic risk indicator

**CPI (35%)**
- **Core economic adequacy concern**
- Directly erodes real savings value
- Policy trigger (interest rates and monetary policy adjustments)
- Member-facing impact (purchasing power)

**Unemployment (30%)**
- Direct impact on contribution inflows
- **Lags GDP** (trailing indicator)
- Social/political sensitivity
- Slightly lower weight due to lag

#### Alternative Weighting Schemes Considered

| Scheme | GDP | CPI | Unemployment | Rationale | Why Not Chosen |
|--------|-----|-----|--------------|-----------|----------------|
| **Equal** | 33% | 33% | 34% | Simplest | Ignores indicator importance |
| **GDP-heavy** | 50% | 25% | 25% | GDP is leading | Over-weights single indicator |
| **CPI-heavy** | 25% | 50% | 25% | Inflation critical | Under-weights growth |
| **Current** | 35% | 35% | 30% | Balanced, empirical | ✓ CHOSEN |

### 4.3 Example Calculation

```python
# Latest values (April 2025)
gdp_score = 62.2
cpi_score = 71.9
unemployment_score = 57.5

# Weighted contributions
gdp_contribution = 0.35 × 62.2 = 21.77
cpi_contribution = 0.35 × 71.9 = 25.17
unemp_contribution = 0.30 × 57.5 = 17.25

# Composite score
composite = 21.77 + 25.17 + 17.25 = 64.19 ≈ 64.2

# Alert classification
if composite < 40:
    alert = 'Green'
elif composite < 65:
    alert = 'Amber'  # ← Current status (64.2)
else:
    alert = 'Red'
```

**Interpretation:**
- CPI (71.9) is the **highest driver** (contributing 25.2 points)
- GDP (62.2) is moderately stressed (contributing 21.8 points)
- Unemployment (57.5) is below other indicators (contributing 17.3 points)
- **Composite 64.2** is very close to Red threshold (65.0)

### 4.4 Alert Classification

```python
def classify_alert_level(score: float) -> str:
    """
    Classify stress score into traffic-light alert levels.

    Thresholds:
        Green:  0 ≤ score < 40   (low stress)
        Amber: 40 ≤ score < 65   (elevated stress)
        Red:   65 ≤ score ≤ 100  (high stress)
    """
    if score < 40:
        return 'Green'
    elif score < 65:
        return 'Amber'
    else:
        return 'Red'
```

#### Threshold Calibration

**Empirical distribution (from historical data):**
```
Green (0-39):   12 months (  3.2%)  ← Rare
Amber (40-64): 255 months ( 67.6%)  ← Normal operating range
Red (65-100):  110 months ( 29.2%)  ← Crisis periods
```

**Why these thresholds?**

1. **Green (0-39): Rare by design**
   - Singapore rarely has "low stress" economy
   - Always has structural inflation/unemployment
   - Green = exceptional conditions, not normal

2. **Amber (40-64): Intentionally wide**
   - Normal operating range for managed economy
   - Allows for fluctuations without alert fatigue
   - Heightened vigilance, not crisis mode

3. **Red (65-100): Crisis signal**
   - Corresponds to historical crises:
     - 1997-1998: Asian Financial Crisis
     - 2008-2009: Global Financial Crisis
     - 2020: COVID-19 pandemic
   - Triggers Board escalation protocols

**Alternative thresholds considered:**

| Scheme | Green | Amber | Red | Issues |
|--------|-------|-------|-----|--------|
| **Symmetric** | 0-33 | 34-66 | 67-100 | Too many Red alerts (alert fatigue) |
| **Tight** | 0-30 | 31-60 | 61-100 | Almost always Red (not useful) |
| **Current** | 0-39 | 40-64 | 65-100 | Empirically calibrated ✓ |

### 4.5 Transition Detection

```python
def detect_alert_transitions(stress_df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect regime changes (alert level transitions).

    Transition types:
        Green → Amber  (escalating)
        Amber → Red    (escalating)
        Red → Amber    (de-escalating)
        Amber → Green  (de-escalating)
    """
    transitions = []

    for i in range(1, len(stress_df)):
        prev_level = stress_df['alert_level'].iloc[i-1]
        curr_level = stress_df['alert_level'].iloc[i]

        if prev_level != curr_level:
            level_order = {'Green': 0, 'Amber': 1, 'Red': 2}
            direction = 'escalating' if level_order[curr_level] > level_order[prev_level] else 'de-escalating'

            transitions.append({
                'date': stress_df.index[i],
                'from_level': prev_level,
                'to_level': curr_level,
                'direction': direction,
                'score': stress_df['composite_score'].iloc[i]
            })

    return pd.DataFrame(transitions)
```

**Example output:**
```
   date        from_level  to_level  direction        score
0  1998-06-01  Amber       Red       escalating       67.2
1  2008-09-01  Amber       Red       escalating       72.5
2  2020-04-01  Amber       Red       escalating       85.3
3  2021-03-01  Red         Amber     de-escalating    62.1
```

---

## 5. Visualization System

**File:** `src/visualizer.py`

### 5.1 Chart Design Principles

1. **Publication-ready quality**
   - High DPI (100+ default)
   - Professional color scheme
   - Clear labels and legends

2. **Consistent styling**
   - All charts use same color codes
   - Standardized fonts and sizes
   - Grid lines for readability

3. **Information density**
   - Multiple data layers (bands + line + annotations)
   - Legend with context (thresholds, weights)
   - Summary statistics where relevant

### 5.2 Chart 1: Stress Timeseries

```python
def plot_stress_timeseries(stress_df: pd.DataFrame) -> str:
    """
    Create line chart with threshold bands.

    Layers (bottom to top):
    1. Background bands (Green/Amber/Red zones) - zorder=0
    2. Threshold lines (dashed at 40 and 65) - zorder=2
    3. Composite score line (black, solid) - zorder=5
    4. Latest value annotation - zorder=10
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    # Layer 1: Colored bands
    ax.axhspan(0, 40, facecolor='#2ecc71', alpha=0.15, zorder=0)
    ax.axhspan(40, 65, facecolor='#f39c12', alpha=0.15, zorder=0)
    ax.axhspan(65, 100, facecolor='#e74c3c', alpha=0.15, zorder=0)

    # Layer 2: Threshold lines
    ax.axhline(y=40, color='#f39c12', linestyle='--', linewidth=1.5)
    ax.axhline(y=65, color='#e74c3c', linestyle='--', linewidth=1.5)

    # Layer 3: Composite score
    ax.plot(stress_df.index, stress_df['composite_score'],
            color='black', linewidth=2, zorder=5)

    # Layer 4: Annotation
    latest_score = stress_df['composite_score'].iloc[-1]
    latest_date = stress_df.index[-1]
    ax.annotate(f'Latest: {latest_score:.1f}',
                xy=(latest_date, latest_score),
                xytext=(20, 20), textcoords='offset points',
                arrowprops=dict(arrowstyle='->'))

    return chart_path
```

**Why zorder matters:**
- Without zorder: bands could cover the line
- With zorder: layers stack predictably
- Higher zorder = drawn on top

### 5.3 Chart 2: Component Breakdown (Stacked Area)

```python
def plot_component_breakdown(stress_df: pd.DataFrame) -> str:
    """
    Stacked area chart showing weighted contributions.

    Visual representation:
    ┌─────────────────────────────────────┐ 100
    │                                     │
    │         Unemployment (green)        │
    │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│
    │              CPI (orange)           │
    │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│
    │              GDP (blue)             │
    └─────────────────────────────────────┘ 0
    """
    # Calculate weighted contributions
    contributions = pd.DataFrame()
    contributions['gdp'] = 0.35 * stress_df['gdp_score']
    contributions['cpi'] = 0.35 * stress_df['cpi_score']
    contributions['unemployment'] = 0.30 * stress_df['unemployment_score']

    # Stacked area plot
    ax.stackplot(contributions.index,
                 contributions['gdp'],         # Bottom layer
                 contributions['cpi'],         # Middle layer
                 contributions['unemployment'], # Top layer
                 colors=['#3498db', '#e67e22', '#27ae60'],
                 alpha=0.7)

    # Overlay composite score
    ax.plot(stress_df.index, stress_df['composite_score'],
            color='black', linestyle='--', linewidth=2)

    return chart_path
```

**Reading the chart:**
- **Thicker layer** = larger contribution to stress
- **Layer expansion** = that indicator is driving stress increase
- **Black dashed line** = sum of all contributions (composite score)

**Example insights:**
- "CPI consistently accounts for ~25 points of stress"
- "GDP spiked during 2020 COVID lockdown"
- "Unemployment contribution expanded in 2008 GFC"

### 5.4 Chart 3: Correlation Heatmap

```python
def plot_correlation_heatmap(normalized_data: Dict[str, pd.DataFrame]) -> str:
    """
    3×3 correlation matrix of normalized indicators.

    Matrix structure:
              GDP    CPI    UNEMP
        GDP  [1.00] [0.23] [-0.45]
        CPI  [0.23] [1.00] [0.12]
      UNEMP [-0.45] [0.12] [1.00]

    Color coding:
        Red (positive correlation): Indicators move together
        Green (negative correlation): Indicators move opposite
        White (near zero): No relationship
    """
    # Extract normalized scores
    scores_df = pd.DataFrame({
        'GDP': normalized_data['gdp']['normalized'],
        'CPI': normalized_data['cpi']['normalized'],
        'UNEMPLOYMENT': normalized_data['unemployment']['normalized']
    })

    # Calculate correlation matrix
    corr_matrix = scores_df.corr()

    # Create heatmap
    im = ax.imshow(corr_matrix, cmap='RdYlGn_r', vmin=-1, vmax=1)

    # Annotate cells with values
    for i in range(3):
        for j in range(3):
            value = corr_matrix.iloc[i, j]
            color = 'white' if abs(value) > 0.5 else 'black'
            ax.text(j, i, f'{value:.2f}', ha='center', va='center',
                   color=color, fontweight='bold')

    return chart_path
```

**Interpreting correlations:**

| Value | Interpretation | Example |
|-------|----------------|---------|
| **+0.8 to +1.0** | Strong positive | Rare in economics |
| **+0.5 to +0.8** | Moderate positive | CPI + Unemployment sometimes |
| **+0.2 to +0.5** | Weak positive | GDP + CPI |
| **-0.2 to +0.2** | No relationship | Random |
| **-0.5 to -0.2** | Weak negative | - |
| **-0.8 to -0.5** | Moderate negative | GDP + Unemployment |
| **-1.0 to -0.8** | Strong negative | Rare |

### 5.5 Chart 4: Alert Timeline

```python
def plot_alert_timeline(stress_df: pd.DataFrame) -> str:
    """
    Two-panel chart:
    - Top: Horizontal bars colored by alert level
    - Bottom: Distribution (% time in each level)

    Example:
    Top panel:
    ├─Green─┤──────── Amber ─────────┤── Red ──┤─ Amber ─┤
    1992    1995                     2008      2010      2025

    Bottom panel:
    Green  |███              |  3.2%
    Amber  |████████████████████████| 67.6%
    Red    |█████████                | 29.2%
    """
    fig, (ax1, ax2) = plt.subplots(2, 1,
                                   gridspec_kw={'height_ratios': [3, 1]})

    # Top panel: Timeline
    colors = [alert_colors[level] for level in stress_df['alert_level']]
    ax1.bar(stress_df.index, height=1, width=30, color=colors)

    # Bottom panel: Distribution
    alert_counts = stress_df['alert_level'].value_counts()
    percentages = 100 * alert_counts / len(stress_df)
    ax2.barh(['Green', 'Amber', 'Red'], percentages,
             color=[alert_colors[level] for level in ['Green', 'Amber', 'Red']])

    return chart_path
```

**Why two panels?**
- Timeline shows **temporal patterns** (when crises occurred)
- Distribution shows **overall frequency** (% time in each state)
- Complements timeseries (regime view vs continuous score)

---

## 6. Configuration Management

**File:** `config.py`

### 6.1 Configuration Philosophy

**Principles:**
1. **Single source of truth** - All parameters in one file
2. **Self-documenting** - Comments explain every parameter
3. **Validated on import** - Catches errors early
4. **Easy to modify** - Users can tune without touching code

### 6.2 Configuration Structure

```python
# =============================================================================
# INDICATOR WEIGHTS
# =============================================================================

INDICATOR_WEIGHTS = {
    'gdp': 0.35,         # GDP growth rate
    'cpi': 0.35,         # Consumer Price Index
    'unemployment': 0.30 # Unemployment rate
}

# Validation
assert abs(sum(INDICATOR_WEIGHTS.values()) - 1.0) < 0.001

# =============================================================================
# DIRECTIONAL ALIGNMENT
# =============================================================================

INVERT_INDICATORS = ['gdp']  # Higher GDP = LESS stress → invert

# =============================================================================
# NORMALIZATION PARAMETERS
# =============================================================================

ROLLING_WINDOW_MONTHS = 36   # 3 years of historical context
SIGMOID_STEEPNESS = 1.0       # Standard logistic curve

# =============================================================================
# ALERT THRESHOLDS
# =============================================================================

THRESHOLDS = {
    'green': (0, 39),    # Low stress
    'amber': (40, 64),   # Elevated stress
    'red': (65, 100)     # High stress
}
```

### 6.3 Validation Function

```python
def validate_config():
    """
    Validate configuration on import.
    Catches common errors before runtime.
    """
    # Check weights sum to 1.0
    weight_sum = sum(INDICATOR_WEIGHTS.values())
    if abs(weight_sum - 1.0) > 0.001:
        raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")

    # Check all weights positive
    for indicator, weight in INDICATOR_WEIGHTS.items():
        if weight <= 0:
            raise ValueError(f"Weight for {indicator} must be positive")

    # Check threshold ranges
    ranges = list(THRESHOLDS.values())
    for low, high in ranges:
        if low >= high:
            raise ValueError(f"Invalid range: {low}-{high}")

    # Check rolling window
    if ROLLING_WINDOW_MONTHS < 12:
        raise ValueError(f"Rolling window too small: {ROLLING_WINDOW_MONTHS}")

# Auto-validate on import
if __name__ != "__main__":
    validate_config()
```

### 6.4 Modifying Configuration

**Example: Increase CPI weight**

```python
# Before
INDICATOR_WEIGHTS = {
    'gdp': 0.35,
    'cpi': 0.35,
    'unemployment': 0.30
}

# After (emphasize inflation)
INDICATOR_WEIGHTS = {
    'gdp': 0.30,
    'cpi': 0.40,  # Increased
    'unemployment': 0.30
}
# Must still sum to 1.0!
```

**Example: More sensitive Red alerts**

```python
# Before
THRESHOLDS = {
    'green': (0, 39),
    'amber': (40, 64),
    'red': (65, 100)
}

# After (lower Red threshold)
THRESHOLDS = {
    'green': (0, 39),
    'amber': (40, 59),
    'red': (60, 100)  # Now triggers at 60 instead of 65
}
```

---

## 7. Design Decisions & Rationale

### 7.1 Architecture Decisions

#### Decision: Modular pipeline architecture

**Alternatives considered:**
1. **Monolithic script** - All logic in one file
2. **Class-based OOP** - Indicator class, Scorer class, etc.
3. **Pipeline architecture** - Separate modules for each stage ✓

**Why pipeline architecture?**
- Clear separation of concerns
- Each module testable independently
- Easy to understand data flow
- Follows functional programming principles
- Can skip stages (e.g., `--no-charts`)

#### Decision: Separate fetch/transform/load

**Why not combine?**
- API structure may change (need to update fetch only)
- Manual download option (skip fetch, run transform)
- Transform logic reusable for other data sources
- Clean CSV files are human-inspectable

### 7.2 Statistical Decisions

#### Decision: 36-month rolling window

**Analysis:**
```
Window  | Avg Volatility | Crisis Detection Lag | Data Loss
--------|----------------|---------------------|----------
12m     | High (σ=18.2) | 1-2 months         | 11 months
24m     | Medium (σ=12.1)| 3-4 months         | 23 months
36m     | Low (σ=9.3)    | 5-6 months         | 35 months ✓
48m     | Very low (σ=7.1)| 7-9 months        | 47 months
```

**Trade-off:** 36 months balances stability (low volatility) with responsiveness (reasonable lag).

#### Decision: Sigmoid transformation

**Compared to:**

| Method | Formula | Bounded? | Smooth? | Interpretable? | Chosen |
|--------|---------|----------|---------|----------------|--------|
| **Linear** | `(z+3)/6 * 100` | No | Yes | Yes | ✗ |
| **Min-Max** | `(z-min)/(max-min)*100` | Yes | Yes | No | ✗ |
| **Sigmoid** | `100/(1+e^-z)` | Yes | Yes | Yes | ✓ |
| **Tanh** | `50*(tanh(z)+1)` | Yes | Yes | Yes | ≈ |

**Why sigmoid over tanh?**
- Both work similarly
- Sigmoid: z=0 → 50 (intuitive)
- Tanh: z=0 → 50 (same center point)
- Sigmoid more common in literature
- **Marginal difference** - either works

### 7.3 UI/UX Decisions

#### Decision: Command-line interface (not GUI)

**Why CLI?**
- Target users: Data analysts, risk managers (comfortable with terminal)
- Easier to automate (cron jobs, scripts)
- No GUI framework dependencies
- Cross-platform (works on servers)
- Professional standard for data tools

#### Decision: 4 charts (not interactive dashboard)

**Why static charts?**
- Publishable in reports (PNG/PDF)
- No web server required
- Consistent visual style
- Easy to email/share
- Fast generation (~5 seconds)

**Alternative (not chosen):** Plotly/Dash interactive dashboard
- Requires web server
- More complex deployment
- Overkill for monthly refresh cadence

---

## 8. Code Quality Patterns

### 8.1 Documentation Standards

**Every function has:**

```python
def function_name(arg1: type, arg2: type) -> return_type:
    """
    One-line summary of what function does.

    Detailed explanation (optional):
    - Why this function exists
    - How it works
    - Edge cases handled

    Args:
        arg1: Description of first argument
        arg2: Description of second argument

    Returns:
        Description of return value

    Raises:
        ValueError: When input is invalid
        FileNotFoundError: When file doesn't exist

    Examples:
        >>> result = function_name('foo', 42)
        >>> print(result)
        'bar'
    """
```

### 8.2 Type Hints

```python
from typing import Dict, Tuple, List, Optional

def load_all_data() -> Tuple[Dict[str, pd.DataFrame], pd.DatetimeIndex]:
    """Return type clearly documented"""
    pass

def plot_chart(df: pd.DataFrame, output_path: Optional[str] = None) -> str:
    """Optional parameters use Optional[]"""
    pass
```

### 8.3 Error Handling

```python
# Validate inputs
if 'date' not in df.columns:
    raise ValueError("CSV must have 'date' column")

# Handle edge cases
z_score = z_score.replace([np.inf, -np.inf], np.nan)

# Provide context in errors
try:
    df = pd.read_csv(filepath)
except FileNotFoundError:
    raise FileNotFoundError(f"Data file not found: {filepath}")
```

### 8.4 Testing Pattern

Each module can run standalone:

```python
if __name__ == "__main__":
    """
    Test the data loader by loading all indicators.

    Run with: python -m src.data_loader
    """
    print("DATA LOADER TEST")
    data, dates = load_all_data()
    print(f"Loaded {len(data)} indicators")
    print("✓ Test complete!")
```

---

## 9. Performance Considerations

### 9.1 Runtime Analysis

**Full pipeline execution time:**
```
Stage             | Time    | Bottleneck?
------------------|---------|------------
Load data         | 0.2s    | No (I/O bound)
Normalize         | 0.5s    | No (vectorized)
Score             | 0.1s    | No (simple math)
Visualize (4 charts)| 3.0s  | Yes (matplotlib rendering)
Total             | 3.8s    | Acceptable
```

### 9.2 Data Size

```
Indicators: 3
Date range: 1992-2025 (400 months)
Total data points: 3 × 400 = 1,200

Memory usage:
  Raw DataFrames: ~200 KB
  Normalized data: ~300 KB
  Chart images: ~400 KB (4 × 100 KB)
  Total: <1 MB

Conclusion: Performance not a concern
```

### 9.3 Optimization Opportunities (not needed)

**If performance becomes an issue:**

1. **Cache normalized data**
   ```python
   # Save normalized scores to avoid recalculation
   normalized.to_pickle('cache/normalized.pkl')
   ```

2. **Vectorize operations** (already done)
   ```python
   # Good (vectorized)
   df['z_score'] = (df['value'] - rolling_mean) / rolling_std

   # Bad (loop)
   for i in range(len(df)):
       df.loc[i, 'z_score'] = (df.loc[i, 'value'] - rolling_mean[i]) / rolling_std[i]
   ```

3. **Skip chart generation** (already available)
   ```bash
   python main.py --no-charts  # 0.8s instead of 3.8s
   ```

---

## 10. Extending the System

### 10.1 Adding a New Indicator

**Step 1: Update config.py**

```python
INDICATOR_WEIGHTS = {
    'gdp': 0.30,          # Reduced
    'cpi': 0.30,          # Reduced
    'unemployment': 0.25, # Reduced
    'wages': 0.15         # NEW
}

# If new indicator needs inversion:
INVERT_INDICATORS = ['gdp', 'wages']  # Add if higher = less stress
```

**Step 2: Add data file to config.py**

```python
DATA_FILES = {
    'gdp': os.path.join(DATA_DIR, 'gdp_clean.csv'),
    'cpi': os.path.join(DATA_DIR, 'cpi_clean.csv'),
    'unemployment': os.path.join(DATA_DIR, 'unemployment_clean.csv'),
    'wages': os.path.join(DATA_DIR, 'wages_clean.csv')  # NEW
}
```

**Step 3: Provide clean CSV**

```csv
date,value
1992-Q1,2.5
1992-Q2,3.1
...
```

**Step 4: Run pipeline**

```bash
python main.py
# Automatically includes new indicator in scoring!
```

**No code changes needed** - system is data-driven.

### 10.2 Adding a New Chart

**Example: Trend chart (6-month moving average)**

```python
# In src/visualizer.py

def plot_trend_chart(stress_df: pd.DataFrame, output_path: Optional[str] = None) -> str:
    """Plot 6-month moving average trend."""
    setup_chart_style()

    fig, ax = plt.subplots(figsize=config.CHART_SIZE)

    # Calculate 6-month MA
    ma_6m = stress_df['composite_score'].rolling(window=6).mean()

    # Plot both raw and smoothed
    ax.plot(stress_df.index, stress_df['composite_score'],
            color='lightgray', linewidth=1, label='Raw Score')
    ax.plot(stress_df.index, ma_6m,
            color='black', linewidth=2, label='6-Month MA')

    ax.set_xlabel('Date')
    ax.set_ylabel('Stress Score')
    ax.set_title('Stress Score Trend (6-Month Moving Average)')
    ax.legend()

    if output_path is None:
        output_path = os.path.join(config.OUTPUT_DIR, 'trend_chart.png')

    plt.savefig(output_path, dpi=config.CHART_DPI)
    plt.close()

    return output_path

# Update create_all_charts() to include new chart:
def create_all_charts(...):
    chart_paths['timeseries'] = plot_stress_timeseries(...)
    chart_paths['components'] = plot_component_breakdown(...)
    chart_paths['heatmap'] = plot_correlation_heatmap(...)
    chart_paths['alerts'] = plot_alert_timeline(...)
    chart_paths['trend'] = plot_trend_chart(...)  # NEW
    return chart_paths
```

### 10.3 Custom Alert Thresholds by Indicator

**Current:** Single thresholds for composite score

**Enhancement:** Different thresholds per indicator

```python
# In config.py
INDICATOR_THRESHOLDS = {
    'gdp': {'green': (0, 35), 'amber': (35, 60), 'red': (60, 100)},
    'cpi': {'green': (0, 40), 'amber': (40, 70), 'red': (70, 100)},
    'unemployment': {'green': (0, 45), 'amber': (45, 65), 'red': (65, 100)}
}

# In src/stress_scorer.py
def classify_indicator_alerts(normalized_data):
    alerts = {}
    for indicator, df in normalized_data.items():
        thresholds = INDICATOR_THRESHOLDS[indicator]
        score = df['normalized'].iloc[-1]

        if score < thresholds['green'][1]:
            alerts[indicator] = 'Green'
        elif score < thresholds['amber'][1]:
            alerts[indicator] = 'Amber'
        else:
            alerts[indicator] = 'Red'

    return alerts
```

---

## 11. Common Issues & Solutions

### 11.1 Data Issues

#### Issue: Missing months in aligned data

```
Warning: cpi has 12 missing months in common range
```

**Cause:** CPI data has gaps (e.g., 2020-03 missing due to COVID lockdown)

**Solution:**
```python
# In src/data_loader.py - already handled
df_monthly = df.fillna(method='ffill')  # Forward-fill gaps
```

#### Issue: First 36 months have no scores

```
1992-01 to 1994-11: NaN stress scores
```

**Cause:** Rolling z-score needs 36 months of history

**Solution:** This is expected behavior. Document in outputs.

### 11.2 Statistical Issues

#### Issue: Extreme z-scores during crises

```
2020-04: GDP z-score = +8.2 (COVID crash)
```

**Cause:** COVID caused unprecedented economic shock

**Solution:**
```python
# Sigmoid handles extreme values gracefully
score = 100 / (1 + exp(-8.2)) = 99.97  # Bounded to [0, 100]
```

No code changes needed - sigmoid designed for this.

#### Issue: Volatile scores with short window

```
With 12-month window: Scores swing wildly month-to-month
```

**Cause:** Short windows over-react to noise

**Solution:**
```python
# In config.py
ROLLING_WINDOW_MONTHS = 36  # Use longer window (already set)
```

### 11.3 Visualization Issues

#### Issue: Overlapping x-axis labels

```
[Date labels crowded and unreadable]
```

**Solution:**
```python
# In src/visualizer.py - already implemented
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
```

#### Issue: Chart colors don't match alert levels

```
Green band showing for Red alert period
```

**Cause:** Using wrong colormap

**Solution:**
```python
# Use consistent color scheme from config
ax.axhspan(0, 40, facecolor=config.THRESHOLD_COLORS['green'], ...)
```

### 11.4 API Issues

#### Issue: API timeout or rate limiting

```
requests.exceptions.Timeout: Read timed out
```

**Solution:**
```python
# In fetch_singstat_api.py - already implemented
time.sleep(1)  # Rate limiting between requests

# Manual fallback
print("Download manually from: https://data.gov.sg/datasets/...")
```

#### Issue: API structure changed

```
KeyError: 'data' (expected key not in response)
```

**Solution:**
1. Update `fetch_singstat_api.py` with new response structure
2. Or use manual download → `transform_data.py`

---

## Appendix A: Mathematical Reference

### A.1 Z-Score Formula

```
z_t = (x_t - μ_36) / σ_36

where:
  x_t = value at time t
  μ_36 = mean(x_{t-35}, x_{t-34}, ..., x_t)
  σ_36 = std_dev(x_{t-35}, x_{t-34}, ..., x_t)
```

### A.2 Sigmoid Formula

```
S(z) = 100 / (1 + e^(-z))

Properties:
  lim_{z → -∞} S(z) = 0
  lim_{z → +∞} S(z) = 100
  S(0) = 50

Derivative:
  S'(z) = 100 * e^(-z) / (1 + e^(-z))^2
```

### A.3 Composite Score Formula

```
C = Σ(w_i × S_i)
  = w_gdp × S_gdp + w_cpi × S_cpi + w_unemp × S_unemp
  = 0.35 × S_gdp + 0.35 × S_cpi + 0.30 × S_unemp

where:
  C = composite stress score
  w_i = weight for indicator i
  S_i = normalized score for indicator i

Constraint:
  Σw_i = 1.0
```

---

## Appendix B: File Format Reference

### B.1 Clean CSV Format

```csv
date,value
1992-Q1,2.1
1992-Q2,2.3
2025-01,8.6
2025-02,8.9
```

**Requirements:**
- Header row: `date,value`
- Dates: `YYYY-QN` (quarterly) or `YYYY-MM` (monthly)
- Values: Numeric (float or int)
- No missing values (NaN will be dropped)

### B.2 Raw API Format (Wide)

```csv
_id,DataSeries,19921Q,19922Q,...,20254Q
1234,Total Unemployment Rate,2.1,2.3,...,3.5
1235,Youth Unemployment Rate,4.2,4.5,...,6.1
```

**Characteristics:**
- Multiple rows (different data series)
- Date columns: `YYYYNQ` (no hyphen)
- Need transformation to clean format

---

## Appendix C: Testing Checklist

### C.1 Unit Tests (Manual)

```bash
# Test each module independently
python -m src.data_loader     # Should load 3 indicators
python -m src.normalizer      # Should show z-scores and normalized values
python -m src.stress_scorer   # Should calculate composite scores
python -m src.visualizer      # Should create 4 charts

# Expected output for each: "✓ Test complete!"
```

### C.2 Integration Test

```bash
# Full pipeline
python main.py --verbose

# Should see:
# - Data loading progress
# - Normalization summary
# - Stress score analysis
# - Current status
# - 4 charts generated
```

### C.3 Configuration Test

```bash
# Modify config.py weights to invalid values
INDICATOR_WEIGHTS = {'gdp': 0.5, 'cpi': 0.3, 'unemployment': 0.1}  # Sum = 0.9

# Run
python main.py

# Should see:
# AssertionError: Weights must sum to 1.0, got 0.9
```

---

## Appendix D: Glossary

| Term | Definition |
|------|------------|
| **Z-score** | Number of standard deviations a value is from the mean |
| **Sigmoid** | S-shaped mathematical function that maps (-∞,+∞) to (0,1) |
| **Rolling window** | Statistical calculation using a moving subset of data |
| **Forward-fill** | Propagate last valid value forward to fill gaps |
| **Composite score** | Weighted average of multiple normalized indicators |
| **Alert level** | Traffic-light classification (Green/Amber/Red) |
| **Regime change** | Transition between alert levels |
| **Directional inversion** | Multiplying by -1 to reverse indicator directionality |
| **Normalization** | Transforming data to a common scale (0-100) |
| **Resampling** | Converting data from one frequency to another (quarterly → monthly) |

---

**Last Updated:** December 2025
**Version:** 1.0.0
**Maintainer:** Singapore Economic Stress Monitor Project
