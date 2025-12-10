"""
Data Loader Module

This module handles loading and aligning economic indicator data from clean CSV files.

Key functions:
- load_indicator_data(): Load a single indicator CSV
- parse_dates(): Convert date strings to datetime objects
- resample_to_monthly(): Convert quarterly data to monthly frequency
- align_indicators(): Align all indicators to common date range
- load_all_data(): Load and align all indicators in one call

Data format expected:
    date,value
    2025-Q3,8.6
    2025-10,101.33
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import config
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)


def parse_dates(date_str: str) -> pd.Timestamp:
    """
    Parse date strings from various formats to pandas Timestamp.

    Handles:
    - Quarterly: "2025-Q3" → 2025-07-01 (start of Q3)
    - Monthly: "2025-10" → 2025-10-01

    Args:
        date_str: Date string from CSV

    Returns:
        pandas Timestamp object

    Examples:
        >>> parse_dates("2025-Q3")
        Timestamp('2025-07-01 00:00:00')
        >>> parse_dates("2025-10")
        Timestamp('2025-10-01 00:00:00')
    """
    date_str = str(date_str).strip()

    # Handle quarterly format: "2025-Q3"
    if 'Q' in date_str or 'q' in date_str:
        # Extract year and quarter
        parts = date_str.upper().split('-Q')
        if len(parts) == 2:
            year = int(parts[0])
            quarter = int(parts[1])
            # Convert quarter to month (Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct)
            month = (quarter - 1) * 3 + 1
            return pd.Timestamp(year=year, month=month, day=1)

    # Handle monthly format: "2025-10" or standard datetime
    try:
        return pd.to_datetime(date_str)
    except Exception as e:
        raise ValueError(f"Could not parse date: {date_str}. Error: {e}")


def load_indicator_data(filepath: str, indicator_name: str) -> pd.DataFrame:
    """
    Load a single economic indicator from CSV file.

    Expected CSV format:
        date,value
        2025-Q3,8.6
        2025-10,101.33

    Args:
        filepath: Path to clean CSV file
        indicator_name: Name of indicator (for logging)

    Returns:
        DataFrame with DatetimeIndex and 'value' column

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid
    """
    try:
        # Load CSV
        df = pd.read_csv(filepath)

        if config.VERBOSE:
            print(f"  Loading {indicator_name}...")

        # Validate required columns
        if 'date' not in df.columns or 'value' not in df.columns:
            raise ValueError(f"CSV must have 'date' and 'value' columns. Got: {df.columns.tolist()}")

        # Parse dates
        df['date'] = df['date'].apply(parse_dates)

        # Set date as index
        df = df.set_index('date')

        # Sort by date
        df = df.sort_index()

        # Remove any duplicate dates (keep first)
        df = df[~df.index.duplicated(keep='first')]

        # Convert value to float
        df['value'] = pd.to_numeric(df['value'], errors='coerce')

        # Remove any NaN values
        df = df.dropna()

        if config.VERBOSE:
            print(f"    ✓ Loaded {len(df)} records from {df.index.min().strftime('%Y-%m')} to {df.index.max().strftime('%Y-%m')}")

        return df

    except FileNotFoundError:
        raise FileNotFoundError(f"Data file not found: {filepath}")
    except Exception as e:
        raise ValueError(f"Error loading {indicator_name} from {filepath}: {e}")


def resample_to_monthly(df: pd.DataFrame, method: str = 'ffill') -> pd.DataFrame:
    """
    Resample data to monthly frequency.

    For quarterly data, this forward-fills values:
    - Q1 (Jan) → Jan, Feb, Mar all get same value
    - Q2 (Apr) → Apr, May, Jun all get same value

    Args:
        df: DataFrame with DatetimeIndex
        method: Resampling method ('ffill' = forward fill)

    Returns:
        DataFrame resampled to monthly frequency
    """
    # Resample to month-start frequency
    df_monthly = df.resample('MS').first()

    # Forward fill to propagate quarterly values through the months
    if method == 'ffill':
        df_monthly = df_monthly.fillna(method='ffill')

    return df_monthly


def align_indicators(data_dict: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], pd.DatetimeIndex]:
    """
    Align all indicators to a common date range.

    Steps:
    1. Find the intersection of all date ranges
    2. Trim each indicator to this common range

    Args:
        data_dict: Dictionary of {indicator_name: DataFrame}

    Returns:
        Tuple of (aligned_data_dict, common_date_index)

    Example:
        >>> aligned, dates = align_indicators({'gdp': gdp_df, 'cpi': cpi_df})
        >>> print(f"Common range: {dates.min()} to {dates.max()}")
    """
    # Find earliest start date (latest of all start dates)
    start_dates = [df.index.min() for df in data_dict.values()]
    common_start = max(start_dates)

    # Find latest end date (earliest of all end dates)
    end_dates = [df.index.max() for df in data_dict.values()]
    common_end = min(end_dates)

    if config.VERBOSE:
        print(f"\nAligning indicators to common date range:")
        print(f"  Common range: {common_start.strftime('%Y-%m')} to {common_end.strftime('%Y-%m')}")
        print(f"  Total months: {(common_end.year - common_start.year) * 12 + (common_end.month - common_start.month) + 1}")

    # Create common date index
    common_dates = pd.date_range(start=common_start, end=common_end, freq='MS')

    # Align each indicator
    aligned_data = {}
    for name, df in data_dict.items():
        # Reindex to common dates
        aligned_df = df.reindex(common_dates)

        # Check for missing data
        missing_count = aligned_df['value'].isna().sum()
        if missing_count > 0:
            if config.VERBOSE:
                print(f"  Warning: {name} has {missing_count} missing months in common range")

        aligned_data[name] = aligned_df

    return aligned_data, common_dates


def load_all_data() -> Tuple[Dict[str, pd.DataFrame], pd.DatetimeIndex]:
    """
    Load and align all economic indicators.

    This is the main entry point for data loading. It:
    1. Loads each indicator from CSV
    2. Resamples quarterly data to monthly
    3. Aligns all indicators to common date range

    Returns:
        Tuple of (indicator_data_dict, common_dates)

    The returned dict has structure:
        {
            'gdp': DataFrame with 'value' column,
            'cpi': DataFrame with 'value' column,
            'unemployment': DataFrame with 'value' column
        }

    Example:
        >>> data, dates = load_all_data()
        >>> print(f"GDP latest value: {data['gdp']['value'].iloc[-1]}")
    """
    if config.VERBOSE:
        print("\n" + "="*60)
        print("LOADING ECONOMIC INDICATOR DATA")
        print("="*60)

    # Load each indicator
    raw_data = {}

    for indicator_name, filepath in config.DATA_FILES.items():
        df = load_indicator_data(filepath, indicator_name)
        raw_data[indicator_name] = df

    # Resample quarterly data to monthly
    if config.VERBOSE:
        print("\nResampling to monthly frequency...")

    monthly_data = {}
    for indicator_name, df in raw_data.items():
        # Check frequency (if data points are ~90 days apart, it's quarterly)
        date_diffs = df.index.to_series().diff().dt.days
        median_diff = date_diffs.median()

        if median_diff > 60:  # More than 60 days between points = quarterly
            if config.VERBOSE:
                print(f"  {indicator_name}: Quarterly → Monthly (forward-fill)")
            monthly_data[indicator_name] = resample_to_monthly(df, method=config.RESAMPLE_METHOD)
        else:
            if config.VERBOSE:
                print(f"  {indicator_name}: Already monthly")
            monthly_data[indicator_name] = df

    # Align to common date range
    aligned_data, common_dates = align_indicators(monthly_data)

    if config.VERBOSE:
        print("\n" + "="*60)
        print("DATA LOADING COMPLETE")
        print("="*60)
        print(f"✓ Loaded {len(config.DATA_FILES)} indicators")
        print(f"✓ Date range: {common_dates.min().strftime('%Y-%m')} to {common_dates.max().strftime('%Y-%m')}")
        print(f"✓ Total months: {len(common_dates)}\n")

    return aligned_data, common_dates


def get_summary_stats(data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Get summary statistics for all indicators.

    Args:
        data_dict: Dictionary of {indicator_name: DataFrame}

    Returns:
        DataFrame with summary statistics
    """
    stats = []
    for name, df in data_dict.items():
        stats.append({
            'Indicator': name.upper(),
            'Count': len(df),
            'Mean': df['value'].mean(),
            'Std': df['value'].std(),
            'Min': df['value'].min(),
            'Max': df['value'].max(),
            'Latest': df['value'].iloc[-1] if len(df) > 0 else None
        })

    return pd.DataFrame(stats)


# =============================================================================
# TESTING / DEMO
# =============================================================================

if __name__ == "__main__":
    """
    Test the data loader by loading all indicators and showing summary stats.

    Run this with:
        python -m src.data_loader
    """
    print("\n" + "="*60)
    print("DATA LOADER TEST")
    print("="*60)

    # Load all data
    data, dates = load_all_data()

    # Show summary statistics
    print("\nSUMMARY STATISTICS:")
    print("="*60)
    stats_df = get_summary_stats(data)
    print(stats_df.to_string(index=False))

    # Show sample data
    print("\nSAMPLE DATA (Last 5 months):")
    print("="*60)
    for name, df in data.items():
        print(f"\n{name.upper()}:")
        print(df.tail().to_string())

    print("\n✓ Data loader test complete!")
