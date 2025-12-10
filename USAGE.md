# Singapore Economic Stress Monitor - Usage Guide

This guide provides detailed instructions for setting up and using the Singapore Economic Stress Monitor.

## Table of Contents

1. [Installation](#installation)
2. [Data Management](#data-management)
3. [Running the Dashboard](#running-the-dashboard)
4. [Understanding the Output](#understanding-the-output)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

---

## Installation

### Prerequisites

- **Python 3.8 or higher**
- **pip** (Python package manager)
- **Internet connection** (for data fetching)

### Step 1: Download the Project

```bash
# If using Git
git clone <repository-url>
cd singapore-economic-stress-monitor

# Or download and extract the ZIP file
unzip singapore-economic-stress-monitor.zip
cd singapore-economic-stress-monitor
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pandas` (data manipulation)
- `numpy` (numerical computing)
- `matplotlib` (visualization)
- `requests` (API calls)

### Step 3: Verify Installation

```bash
python -c "import pandas, numpy, matplotlib, requests; print('✓ All dependencies installed')"
```

---

## Data Management

### Fetching Latest Data

The dashboard requires 3 CSV files with economic indicator data. You can fetch the latest data from SingStat:

#### Option 1: Fetch and Transform (Recommended)

```bash
# Step 1: Fetch raw data from SingStat API
python fetch_singstat_api.py

# Step 2: Transform to clean CSV format
python transform_data.py
```

**Output**: Creates 3 files in `data/`:
- `gdp_clean.csv` (198 quarterly records, 1976-2025)
- `cpi_clean.csv` (778 monthly records, 1961-2025)
- `unemployment_clean.csv` (135 quarterly records, 1992-2025)

#### Option 2: Manual Download (If API Fails)

1. Visit [data.gov.sg](https://data.gov.sg)
2. Download datasets:
   - GDP: `d_a5ff719648a0e6d4b4c623ee383ab686`
   - CPI: `d_bdaff844e3ef89d39fceb962ff8f0791`
   - Unemployment: `d_b816a930bca0eb19fdf20fcbfcdd4c39`
3. Place CSV files in `data/` directory
4. Run `python transform_data.py` to convert to clean format

### Data Update Frequency

- **GDP**: Quarterly (released ~1-2 months after quarter-end)
- **CPI**: Monthly (released ~2 weeks after month-end)
- **Unemployment**: Quarterly (released ~1 month after quarter-end)

**Recommendation**: Re-fetch data monthly to capture latest CPI updates.

---

## Running the Dashboard

### Basic Usage

```bash
# Full dashboard with all charts
python main.py
```

This will:
1. Load data from `data/` directory
2. Normalize indicators to 0-100 scale
3. Calculate composite stress score
4. Display summary statistics
5. Generate 4 charts in `output/` directory

**Execution time**: ~5 seconds

### Command-Line Options

#### Quiet Mode (Minimal Output)

```bash
python main.py --quiet
# or
python main.py -q
```

Shows only current status without detailed progress.

#### Skip Chart Generation

```bash
python main.py --no-charts
# or
python main.py -n
```

Faster execution (~2 seconds) when you only need the stress score.

#### Combine Options

```bash
python main.py --quiet --no-charts
```

Fastest execution, minimal output.

#### Show Version

```bash
python main.py --version
```

#### Show Help

```bash
python main.py --help
```

---

## Understanding the Output

### Console Output (Verbose Mode)

#### 1. Configuration Summary

```
SINGAPORE ECONOMIC STRESS MONITOR
Run Date: 2025-12-08 09:44:23

Configuration:
  Indicators: 3
  Weights: GDP 35%, CPI 35%, Unemployment 30%
  Rolling Window: 36 months
  Alert Thresholds: Green <40, Amber 40-64, Red ≥65
```

#### 2. Data Loading

```
DATA LOADED
  Date Range: 1992-01 to 2025-04
  Total Months: 400
```

#### 3. Normalization Summary

```
NORMALIZATION SUMMARY
   Indicator  Valid_Records  Avg_Z_Score  Avg_Normalized  Min_Score  Max_Score  Latest_Score
         GDP            377          0.1            52.4        2.6       97.9          62.2
         CPI            377          1.3            75.9        9.2       97.9          71.9
UNEMPLOYMENT            377          0.0            48.8        4.8       99.3          57.5
```

**Interpretation**:
- **Valid_Records**: Number of months with normalized scores (excludes first 23 months for z-score window)
- **Avg_Z_Score**: Mean z-score (0 = neutral, positive = above average stress)
- **Avg_Normalized**: Mean stress score on 0-100 scale
- **Latest_Score**: Current month's normalized score

#### 4. Stress Score Analysis

```
STRESS SCORE ANALYSIS
Overall Statistics:
  Date Range:  1993-12 to 2025-04
  Valid Months: 377
  Mean Score:   59.6
  Std Dev:      11.5
  Min Score:    34.6
  Max Score:    89.3

  Alert Level Distribution:
    🟢 Green (0-39):    12 months (  3.2%)
    🟡 Amber (40-64):  255 months ( 67.6%)
    🔴 Red (65-100):   110 months ( 29.2%)

  Recent Trend (Last 12 Months):
    Recent Mean:  57.3
    vs Historical: -2.3 ↓ (BELOW historical average)

  Alert Transitions:
    Total:           46
    Escalating:      23 (stress increasing)
    De-escalating:   23 (stress decreasing)
```

**Interpretation**:
- **Mean Score 59.6**: Singapore's economy typically operates in upper-Amber range
- **67.6% Amber**: Most common stress state
- **Recent Trend -2.3**: Current stress is below historical average (improving)
- **46 Transitions**: Economy has shifted between alert levels 46 times over 377 months (~12% of months)

#### 5. Current Status (Always Shown)

```
CURRENT STATUS
As of: 2025-04

  Composite Stress Score: 64.2
  Alert Level:            🟡 AMBER

  Component Breakdown:
    GDP Score:          62.2 → Contributes 21.8 points (weight: 35%)
    CPI Score:          71.9 → Contributes 25.2 points (weight: 35%)
    Unemployment Score: 57.5 → Contributes 17.3 points (weight: 30%)

  Alert Interpretation:
    ⚠ Elevated economic stress
    ⚠ Heightened vigilance recommended
    ⚠ Monitor for further deterioration
```

**Interpretation**:
- **Composite 64.2**: Very close to Red threshold (65)
- **CPI is highest driver**: 71.9 indicates elevated inflation stress
- **Amber alert**: Requires heightened vigilance, not crisis mode

### Generated Charts

#### 1. Stress Timeseries (`stress_timeseries.png`)

**What it shows**:
- Black line: Composite stress score over time
- Green/Amber/Red background bands
- Horizontal threshold lines at 40 and 65
- Annotation showing latest score

**How to read it**:
- Look for periods where line enters Red zone (stress episodes)
- Check if current trend is rising or falling
- Compare current level to historical range

**Example insights**:
- "2020 COVID spike reached 85 (Red)"
- "Current 64.2 is near Red boundary"
- "Stress has been declining since mid-2023"

#### 2. Component Breakdown (`component_breakdown.png`)

**What it shows**:
- Stacked area chart with 3 colored layers
- Blue (bottom): GDP contribution
- Orange (middle): CPI contribution
- Green (top): Unemployment contribution
- Black dashed line: Total composite score

**How to read it**:
- Thicker layers = higher contribution to stress
- When CPI layer expands = inflation driving stress
- When unemployment layer expands = jobs market weakening

**Example insights**:
- "CPI consistently accounts for ~25 points of stress"
- "GDP contribution spiked to 30+ during 2008 crisis"
- "Unemployment surged during COVID lockdown"

#### 3. Correlation Heatmap (`correlation_heatmap.png`)

**What it shows**:
- 3×3 matrix showing correlations between indicators
- Values range from -1 (perfect negative) to +1 (perfect positive)
- Color intensity shows strength of relationship

**How to read it**:
- Diagonal is always 1.00 (perfect self-correlation)
- Positive values: indicators move together
- Negative values: indicators move in opposite directions

**Example insights**:
- "GDP and unemployment are negatively correlated (-0.45)"
- "CPI and unemployment show weak correlation (0.12)"
- "Helps understand which stresses compound vs offset"

#### 4. Alert Timeline (`alert_timeline.png`)

**What it shows**:
- Top panel: Horizontal colored bars over time
- Green/Amber/Red colors show stress regime
- Bottom panel: Bar chart of time spent in each alert level

**How to read it**:
- Long Red periods = prolonged stress episodes
- Frequent color changes = volatile conditions
- Green periods are rare (only 3.2% of time)

**Example insights**:
- "Red periods cluster around 1997 Asian Crisis, 2008 GFC, 2020 COVID"
- "Economy spent 29.2% of time in Red zone"
- "Green is rare - Singapore normally operates in Amber"

---

## Configuration

### Adjusting Parameters

Edit `config.py` to customize the dashboard:

#### 1. Indicator Weights

```python
INDICATOR_WEIGHTS = {
    'gdp': 0.35,          # Economic health
    'cpi': 0.35,          # Inflation stress
    'unemployment': 0.30  # Labor market
}
```

**Requirements**:
- Must sum to 1.0 (100%)
- All weights must be positive

**Example**: Increase CPI importance
```python
INDICATOR_WEIGHTS = {
    'gdp': 0.30,
    'cpi': 0.40,  # Increased from 0.35
    'unemployment': 0.30
}
```

#### 2. Alert Thresholds

```python
THRESHOLDS = {
    'green': (0, 39),
    'amber': (40, 64),
    'red': (65, 100)
}
```

**Example**: More sensitive Red alerts
```python
THRESHOLDS = {
    'green': (0, 39),
    'amber': (40, 59),
    'red': (60, 100)  # Lowered from 65
}
```

#### 3. Normalization Window

```python
ROLLING_WINDOW_MONTHS = 36  # Default: 3 years
```

**Trade-offs**:
- **Shorter window** (24 months): More responsive to recent changes
- **Longer window** (48 months): More stable, less reactive

#### 4. Chart Settings

```python
CHART_SIZE = (12, 6)  # Width, height in inches
CHART_DPI = 100       # Resolution (higher = sharper, larger file)
```

### Validating Configuration

After editing `config.py`:

```bash
python -c "import config; config.validate_config()"
```

This checks:
- Weights sum to 1.0
- All weights are positive
- Thresholds don't overlap
- Rolling window is reasonable (≥12 months)

---

## Troubleshooting

### Common Issues

#### Issue 1: "FileNotFoundError: data/gdp_clean.csv"

**Cause**: Data files not present

**Solution**:
```bash
python fetch_singstat_api.py
python transform_data.py
```

#### Issue 2: "ModuleNotFoundError: No module named 'pandas'"

**Cause**: Dependencies not installed

**Solution**:
```bash
pip install -r requirements.txt
```

#### Issue 3: API Timeout or Connection Error

**Cause**: data.gov.sg server issues or network problems

**Solution**:
1. Check internet connection
2. Try again after 5 minutes (rate limiting)
3. Use manual download from data.gov.sg

#### Issue 4: Charts Not Generating

**Cause**: matplotlib backend issues or output directory doesn't exist

**Solution**:
```bash
mkdir -p output
python main.py
```

#### Issue 5: "ValueError: Weights must sum to 1.0"

**Cause**: Modified `config.py` with invalid weights

**Solution**:
- Check weights in `INDICATOR_WEIGHTS`
- Ensure they sum to exactly 1.0
- Example: 0.35 + 0.35 + 0.30 = 1.0 ✓

### Debug Mode

Run individual modules for debugging:

```bash
# Test data loader
python -m src.data_loader

# Test normalizer
python -m src.normalizer

# Test stress scorer
python -m src.stress_scorer

# Test visualizer
python -m src.visualizer
```

Each module has a `__main__` section that runs standalone tests.

---

## Advanced Usage

### Programmatic Usage (Python Script)

```python
from src.data_loader import load_all_data
from src.normalizer import normalize_all_indicators
from src.stress_scorer import calculate_composite_score, get_stress_summary
from src.visualizer import create_all_charts

# Load data
data, dates = load_all_data()

# Normalize
normalized = normalize_all_indicators(data)

# Score
stress_df = calculate_composite_score(normalized)
summary = get_stress_summary(stress_df)

# Get latest score
latest_score = summary['latest_score']
latest_alert = summary['latest_alert']

print(f"Current stress: {latest_score:.1f} ({latest_alert})")

# Generate charts
chart_paths = create_all_charts(stress_df, normalized)
```

### Scheduled Updates (Cron Job)

To run monthly updates automatically:

```bash
# Edit crontab
crontab -e

# Add this line (runs 1st of each month at 9 AM)
0 9 1 * * cd /path/to/singapore-economic-stress-monitor && python fetch_singstat_api.py && python transform_data.py && python main.py --quiet
```

### Exporting Data to CSV

```python
from src.stress_scorer import calculate_composite_score

# ... load and normalize data ...

stress_df = calculate_composite_score(normalized)

# Export full results
stress_df.to_csv('output/stress_scores.csv')

# Export recent scores only
stress_df.tail(12).to_csv('output/recent_12_months.csv')
```

### Custom Visualizations

```python
from src.visualizer import plot_stress_timeseries
import matplotlib.pyplot as plt

# Create custom chart
fig, ax = plt.subplots()
ax.plot(stress_df.index, stress_df['composite_score'])
ax.set_title('My Custom Chart')
plt.savefig('output/custom_chart.png')
```

---

## Best Practices

### 1. Regular Data Updates

- **Monthly**: Fetch new CPI data (released mid-month)
- **Quarterly**: Fetch GDP and unemployment data (released 1-2 months after quarter)

### 2. Version Control

- Keep old data files for reproducibility
- Version your `config.py` changes
- Document threshold adjustments

### 3. Alert Response Procedures

Based on alert level:

**🟢 Green (0-39)**:
- Routine monitoring
- Quarterly review
- No special actions required

**🟡 Amber (40-64)**:
- Monthly review
- Monitor component breakdown (which indicator is driving stress?)
- Prepare contingency plans
- Brief risk committee

**🔴 Red (65-100)**:
- Weekly monitoring
- Escalate to Board
- Activate risk response protocols
- Review withdrawal patterns
- Consider policy interventions

### 4. Validation

Always cross-check with:
- Official SingStat publications
- MAS (Monetary Authority of Singapore) economic reports
- MTI (Ministry of Trade and Industry) economic surveys
- Other authoritative economic data sources

---

## Appendix

### CSV File Format

All clean CSV files use this format:

```csv
date,value
2020-01-01,5.2
2020-02-01,5.3
2020-03-01,5.1
```

**Requirements**:
- Header row: `date,value`
- Dates in `YYYY-MM-DD` format (or parseable)
- Values as floats (decimals allowed)
- No missing values (NaN will be dropped)

### API Endpoints

```
Base URL: https://data.gov.sg/api/action/datastore_search?resource_id={ID}&limit=10000

GDP:          d_a5ff719648a0e6d4b4c623ee383ab686
CPI:          d_bdaff844e3ef89d39fceb962ff8f0791
Unemployment: d_b816a930bca0eb19fdf20fcbfcdd4c39
```

### File Sizes

Approximate sizes:
- `gdp_clean.csv`: 5 KB
- `cpi_clean.csv`: 20 KB
- `unemployment_clean.csv`: 4 KB
- Charts (4 files): ~326 KB total
- Full project: ~2 MB

---

## Support & Feedback

If you encounter issues not covered here:

1. Check `README.md` for methodology
2. Review `config.py` for parameters
3. Run module tests individually
4. Check data file integrity

---

**Last Updated**: December 2025
**Version**: 1.0.0
