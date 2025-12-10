"""
Configuration File for Singapore Economic Stress Monitor

This file contains all configurable parameters for the stress scoring system:
- Indicator weights
- Alert thresholds
- Data file paths
- Normalization parameters

You can adjust these values to fine-tune the dashboard behavior.
"""

import os

# =============================================================================
# PROJECT PATHS
# =============================================================================

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directories
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

# Clean CSV files (transformed from API data)
DATA_FILES = {
    'gdp': os.path.join(DATA_DIR, 'gdp_clean.csv'),
    'cpi': os.path.join(DATA_DIR, 'cpi_clean.csv'),
    'unemployment': os.path.join(DATA_DIR, 'unemployment_clean.csv'),
}

# =============================================================================
# INDICATOR WEIGHTS
# =============================================================================

# Weights for each indicator in the composite stress score
# These must sum to 1.0 (100%)
#
# Rationale:
# - GDP (35%): Primary measure of overall economic health
# - CPI (35%): Inflation directly erodes purchasing power and savings value
# - Unemployment (30%): Direct impact on economic participation and income

INDICATOR_WEIGHTS = {
    'gdp': 0.35,         # GDP growth rate
    'cpi': 0.35,         # Consumer Price Index (inflation)
    'unemployment': 0.30 # Unemployment rate
}

# Verify weights sum to 1.0
_weight_sum = sum(INDICATOR_WEIGHTS.values())
assert abs(_weight_sum - 1.0) < 0.001, f"Weights must sum to 1.0, got {_weight_sum}"

# =============================================================================
# DIRECTIONAL ALIGNMENT
# =============================================================================

# Indicators that need inversion (multiply by -1)
# Higher values should mean MORE stress for all indicators
#
# - GDP: Higher growth = LESS stress → Invert (multiply by -1)
# - CPI: Higher inflation = MORE stress → No inversion
# - Unemployment: Higher unemployment = MORE stress → No inversion

INVERT_INDICATORS = ['gdp']  # Only GDP needs inversion

# =============================================================================
# NORMALIZATION PARAMETERS
# =============================================================================

# Rolling window size for z-score calculation (in months)
# 36 months = 3 years of historical context
# This window adapts to changing economic regimes while maintaining stability

ROLLING_WINDOW_MONTHS = 36

# Sigmoid transformation parameter
# Controls the steepness of the 0-100 score transformation
# Higher values = sharper transitions between score ranges

SIGMOID_STEEPNESS = 1.0

# =============================================================================
# ALERT THRESHOLDS
# =============================================================================

# Stress score ranges for Green/Amber/Red classification
# Scores range from 0 (no stress) to 100 (maximum stress)

THRESHOLDS = {
    'green': (0, 39),      # Normal conditions - routine monitoring
    'amber': (40, 64),     # Elevated stress - heightened vigilance
    'red': (65, 100)       # High stress - activate risk response protocols
}

# Color codes for visualization
THRESHOLD_COLORS = {
    'green': '#2ecc71',    # Green
    'amber': '#f39c12',    # Orange/Amber
    'red': '#e74c3c'       # Red
}

# =============================================================================
# DATA PROCESSING PARAMETERS
# =============================================================================

# How to handle quarterly data when resampling to monthly
# 'ffill' = forward fill (repeat last known value until next quarter)
RESAMPLE_METHOD = 'ffill'

# Minimum number of data points required for z-score calculation
# Should be at least 24 months (2 years) for statistical stability
MIN_PERIODS_FOR_ZSCORE = 24

# =============================================================================
# VISUALIZATION PARAMETERS
# =============================================================================

# Chart dimensions (width, height) in inches
CHART_SIZE = (12, 6)

# DPI for saved charts (higher = better quality, larger file)
CHART_DPI = 100

# Chart output filenames
CHART_FILES = {
    'timeseries': os.path.join(OUTPUT_DIR, 'stress_timeseries.png'),
    'components': os.path.join(OUTPUT_DIR, 'component_breakdown.png'),
    'heatmap': os.path.join(OUTPUT_DIR, 'correlation_heatmap.png'),
    'alerts': os.path.join(OUTPUT_DIR, 'alert_timeline.png')
}

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================

# Number of decimal places for score display
SCORE_DECIMAL_PLACES = 1

# Date format for display
DATE_FORMAT = '%Y-%m'  # e.g., "2025-10"

# Console output verbosity (True = detailed output, False = minimal)
VERBOSE = True

# =============================================================================
# VALIDATION
# =============================================================================

def validate_config():
    """
    Validate configuration settings.
    Raises ValueError if configuration is invalid.
    """
    # Check weights sum to 1.0
    weight_sum = sum(INDICATOR_WEIGHTS.values())
    if abs(weight_sum - 1.0) > 0.001:
        raise ValueError(f"Indicator weights must sum to 1.0, got {weight_sum}")

    # Check all weights are positive
    for indicator, weight in INDICATOR_WEIGHTS.items():
        if weight <= 0:
            raise ValueError(f"Weight for {indicator} must be positive, got {weight}")

    # Check threshold ranges don't overlap
    ranges = list(THRESHOLDS.values())
    for i, (low1, high1) in enumerate(ranges):
        if low1 >= high1:
            raise ValueError(f"Invalid threshold range: {low1}-{high1}")
        for j, (low2, high2) in enumerate(ranges[i+1:], i+1):
            if not (high1 < low2 or high2 < low1):
                raise ValueError(f"Overlapping threshold ranges: {ranges[i]} and {ranges[j]}")

    # Check rolling window is reasonable
    if ROLLING_WINDOW_MONTHS < 12:
        raise ValueError(f"Rolling window too small: {ROLLING_WINDOW_MONTHS} months (minimum 12)")

    print("✓ Configuration validated successfully")

# Run validation when module is imported
if __name__ != "__main__":
    validate_config()
