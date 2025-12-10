"""
Normalizer Module

This module normalizes economic indicators to a common 0-100 stress scale.

Process:
1. Calculate rolling z-scores (36-month window)
2. Apply directional inversion (ensure higher = more stress)
3. Transform z-scores to 0-100 scale using sigmoid function

Why normalize?
- Different indicators have different scales (GDP: %, CPI: index, Unemployment: %)
- Need to combine them into single stress score
- Normalization ensures equal contribution regardless of original scale

Mathematical Details:
    Z-score: z = (x - μ) / σ
    where μ = rolling mean, σ = rolling standard deviation

    Sigmoid: score = 100 / (1 + e^(-z))
    This maps z-scores to 0-100 range:
    - z = -3 → score ≈ 5 (very low stress)
    - z = 0 → score = 50 (neutral)
    - z = +3 → score ≈ 95 (very high stress)
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import config


def calculate_rolling_zscore(series: pd.Series, window: int = None) -> pd.Series:
    """
    Calculate rolling z-score for a time series.

    Z-score = (value - rolling_mean) / rolling_std

    This tells us how many standard deviations away from the mean each value is,
    relative to recent history.

    Args:
        series: Time series data (pandas Series)
        window: Rolling window size in periods (default from config)

    Returns:
        Series of z-scores

    Example:
        If GDP growth is 8% and the 36-month average is 5% with std of 2%:
        z-score = (8 - 5) / 2 = 1.5
        (1.5 standard deviations above recent average)
    """
    if window is None:
        window = config.ROLLING_WINDOW_MONTHS

    # Calculate rolling mean and standard deviation
    rolling_mean = series.rolling(window=window, min_periods=config.MIN_PERIODS_FOR_ZSCORE).mean()
    rolling_std = series.rolling(window=window, min_periods=config.MIN_PERIODS_FOR_ZSCORE).std()

    # Calculate z-score: (value - mean) / std
    z_score = (series - rolling_mean) / rolling_std

    # Replace infinite values with NaN (can occur if std = 0)
    z_score = z_score.replace([np.inf, -np.inf], np.nan)

    return z_score


def apply_directional_inversion(data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Invert indicators where higher values mean LESS stress.

    Goal: Make all indicators directionally consistent
    - Higher value = MORE stress (for all indicators)

    Indicators to invert:
    - GDP: Higher growth = less stress → Multiply by -1

    Indicators NOT inverted:
    - CPI: Higher inflation = more stress (already correct direction)
    - Unemployment: Higher unemployment = more stress (already correct direction)

    Args:
        data_dict: Dictionary of {indicator_name: DataFrame with 'value' column}

    Returns:
        Dictionary with inverted values where needed

    Example:
        GDP growth of +8% → -8 (after inversion)
        GDP growth of -2% → +2 (after inversion)
        Now negative GDP (recession) gives positive value (high stress)
    """
    inverted_data = {}

    for indicator_name, df in data_dict.items():
        df_copy = df.copy()

        # Check if this indicator needs inversion
        if indicator_name in config.INVERT_INDICATORS:
            if config.VERBOSE:
                original_mean = df_copy['value'].mean()
                df_copy['value'] = -df_copy['value']
                new_mean = df_copy['value'].mean()
                print(f"  {indicator_name}: Inverted (mean {original_mean:.2f} → {new_mean:.2f})")
        else:
            if config.VERBOSE:
                print(f"  {indicator_name}: No inversion needed")

        inverted_data[indicator_name] = df_copy

    return inverted_data


def sigmoid_transform(z_score: float, steepness: float = None) -> float:
    """
    Transform z-score to 0-100 scale using sigmoid function.

    Sigmoid formula: score = 100 / (1 + e^(-z))

    This creates a smooth S-curve:
    - Very negative z-scores → scores near 0
    - z = 0 → score = 50
    - Very positive z-scores → scores near 100

    Args:
        z_score: Standard score (how many std deviations from mean)
        steepness: Controls curve steepness (default from config)

    Returns:
        Score between 0 and 100

    Examples:
        >>> sigmoid_transform(-3.0)
        4.74  # Very low stress
        >>> sigmoid_transform(0.0)
        50.0  # Neutral
        >>> sigmoid_transform(3.0)
        95.26  # Very high stress
    """
    if steepness is None:
        steepness = config.SIGMOID_STEEPNESS

    if pd.isna(z_score):
        return np.nan

    # Apply sigmoid: 100 / (1 + e^(-steepness * z))
    score = 100.0 / (1.0 + np.exp(-steepness * z_score))

    return score


def normalize_indicator(df: pd.DataFrame, indicator_name: str) -> pd.DataFrame:
    """
    Normalize a single indicator to 0-100 stress scale.

    Steps:
    1. Calculate rolling z-score
    2. Transform to 0-100 using sigmoid

    Args:
        df: DataFrame with 'value' column
        indicator_name: Name for logging

    Returns:
        DataFrame with additional columns:
        - 'z_score': Standardized value
        - 'normalized': Score on 0-100 scale
    """
    df_normalized = df.copy()

    # Calculate z-score
    df_normalized['z_score'] = calculate_rolling_zscore(df_normalized['value'])

    # Transform to 0-100 scale
    df_normalized['normalized'] = df_normalized['z_score'].apply(sigmoid_transform)

    # Count how many values we successfully normalized
    valid_count = df_normalized['normalized'].notna().sum()

    if config.VERBOSE:
        print(f"  {indicator_name}: {valid_count}/{len(df)} values normalized")
        if valid_count > 0:
            print(f"    Mean score: {df_normalized['normalized'].mean():.1f}")
            print(f"    Range: {df_normalized['normalized'].min():.1f} - {df_normalized['normalized'].max():.1f}")

    return df_normalized


def normalize_all_indicators(data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Normalize all economic indicators to 0-100 stress scale.

    This is the main normalization function. It:
    1. Applies directional inversion (GDP)
    2. Calculates rolling z-scores (36-month window)
    3. Transforms to 0-100 scale (sigmoid)

    Args:
        data_dict: Dictionary of {indicator_name: DataFrame}

    Returns:
        Dictionary of normalized DataFrames with columns:
        - 'value': Original value
        - 'z_score': Rolling z-score
        - 'normalized': Score on 0-100 scale

    Example:
        >>> data, _ = load_all_data()
        >>> normalized = normalize_all_indicators(data)
        >>> print(normalized['gdp']['normalized'].tail())
    """
    if config.VERBOSE:
        print("\n" + "="*60)
        print("NORMALIZING INDICATORS")
        print("="*60)

    # Step 1: Apply directional inversion
    if config.VERBOSE:
        print("\nApplying directional inversion...")

    inverted_data = apply_directional_inversion(data_dict)

    # Step 2: Normalize each indicator
    if config.VERBOSE:
        print(f"\nCalculating z-scores ({config.ROLLING_WINDOW_MONTHS}-month rolling window)...")

    normalized_data = {}
    for indicator_name, df in inverted_data.items():
        normalized_data[indicator_name] = normalize_indicator(df, indicator_name)

    if config.VERBOSE:
        print("\n" + "="*60)
        print("NORMALIZATION COMPLETE")
        print("="*60)

    return normalized_data


def get_normalization_summary(normalized_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Get summary statistics for normalized indicators.

    Args:
        normalized_data: Dictionary of normalized DataFrames

    Returns:
        DataFrame with normalization summary statistics
    """
    summary = []

    for name, df in normalized_data.items():
        # Filter to only rows with valid normalized scores
        valid_df = df.dropna(subset=['normalized'])

        if len(valid_df) > 0:
            summary.append({
                'Indicator': name.upper(),
                'Valid_Records': len(valid_df),
                'Avg_Z_Score': valid_df['z_score'].mean(),
                'Avg_Normalized': valid_df['normalized'].mean(),
                'Min_Score': valid_df['normalized'].min(),
                'Max_Score': valid_df['normalized'].max(),
                'Latest_Score': valid_df['normalized'].iloc[-1]
            })

    return pd.DataFrame(summary)


# =============================================================================
# TESTING / DEMO
# =============================================================================

if __name__ == "__main__":
    """
    Test the normalizer by loading data and normalizing all indicators.

    Run this with:
        python -m src.normalizer
    """
    from src.data_loader import load_all_data

    print("\n" + "="*60)
    print("NORMALIZER TEST")
    print("="*60)

    # Load data
    data, dates = load_all_data()

    # Normalize indicators
    normalized = normalize_all_indicators(data)

    # Show summary
    print("\nNORMALIZATION SUMMARY:")
    print("="*60)
    summary_df = get_normalization_summary(normalized)
    pd.set_option('display.float_format', '{:.2f}'.format)
    print(summary_df.to_string(index=False))

    # Show sample normalized data
    print("\nSAMPLE NORMALIZED DATA (Last 10 months):")
    print("="*60)
    for name, df in normalized.items():
        print(f"\n{name.upper()}:")
        print(df[['value', 'z_score', 'normalized']].tail(10).to_string())

    # Show stress level distribution
    print("\nSTRESS LEVEL DISTRIBUTION:")
    print("="*60)
    for name, df in normalized.items():
        valid_scores = df['normalized'].dropna()
        if len(valid_scores) > 0:
            green = (valid_scores < 40).sum()
            amber = ((valid_scores >= 40) & (valid_scores < 65)).sum()
            red = (valid_scores >= 65).sum()
            total = len(valid_scores)

            print(f"\n{name.upper()}:")
            print(f"  🟢 Green (0-39):   {green:3d} months ({100*green/total:5.1f}%)")
            print(f"  🟡 Amber (40-64):  {amber:3d} months ({100*amber/total:5.1f}%)")
            print(f"  🔴 Red (65-100):   {red:3d} months ({100*red/total:5.1f}%)")

    print("\n✓ Normalizer test complete!")
