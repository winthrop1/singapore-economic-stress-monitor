"""
Transform SingStat Data from Wide to Long Format
Converts API data to standard date/value format for stress dashboard
"""

import pandas as pd
import re
from typing import Optional

def parse_quarter_date(col: str) -> Optional[str]:
    """
    Parse quarterly date column like '20253Q' to '2025-Q3'
    """
    match = re.match(r'(\d{4})(\d)Q', col)
    if match:
        year = match.group(1)
        quarter = match.group(2)
        return f"{year}-Q{quarter}"
    return None


def parse_month_date(col: str) -> Optional[str]:
    """
    Parse monthly date column like '2025Oct' to '2025-10'
    """
    month_map = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }

    match = re.match(r'(\d{4})([A-Za-z]+)', col)
    if match:
        year = match.group(1)
        month_str = match.group(2)
        month = month_map.get(month_str)
        if month:
            return f"{year}-{month}"
    return None


def transform_unemployment(filepath: str = "data/unemployment.csv") -> pd.DataFrame:
    """Transform unemployment data to long format"""
    print("\n" + "="*60)
    print("Transforming UNEMPLOYMENT data")
    print("="*60)

    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

    # Select "Total Unemployment Rate, (SA)" row
    target_row = df[df['DataSeries'].str.contains('Total Unemployment Rate', case=False, na=False)]

    if target_row.empty:
        print("Warning: Could not find 'Total Unemployment Rate' row")
        target_row = df.iloc[[0]]  # Use first row as fallback

    print(f"Selected: {target_row['DataSeries'].values[0]}")

    # Get date columns (exclude _id and DataSeries)
    date_cols = [c for c in df.columns if re.match(r'\d{4}\dQ', c)]
    print(f"Found {len(date_cols)} quarterly columns")

    # Transform to long format
    records = []
    for col in date_cols:
        date_str = parse_quarter_date(col)
        if date_str:
            value = target_row[col].values[0]
            records.append({'date': date_str, 'value': float(value)})

    result = pd.DataFrame(records)
    result = result.sort_values('date').reset_index(drop=True)

    print(f"Transformed: {len(result)} records")
    print(f"Date range: {result['date'].min()} to {result['date'].max()}")

    return result


def transform_gdp(filepath: str = "data/gdp.csv") -> pd.DataFrame:
    """Transform GDP data to long format"""
    print("\n" + "="*60)
    print("Transforming GDP data")
    print("="*60)

    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

    # Look for GDP growth rate row - try different patterns
    patterns = [
        'GDP At Current Market Prices',
        'Real GDP Growth',
        'GDP'
    ]

    target_row = None
    for pattern in patterns:
        match = df[df['DataSeries'].str.contains(pattern, case=False, na=False)]
        if not match.empty:
            target_row = match.iloc[[0]]
            break

    if target_row is None:
        print("Warning: Could not find GDP row, using first row")
        target_row = df.iloc[[0]]

    print(f"Selected: {target_row['DataSeries'].values[0]}")

    # Get date columns
    date_cols = [c for c in df.columns if re.match(r'\d{4}\dQ', c)]
    print(f"Found {len(date_cols)} quarterly columns")

    # Transform to long format
    records = []
    for col in date_cols:
        date_str = parse_quarter_date(col)
        if date_str:
            value = target_row[col].values[0]
            try:
                records.append({'date': date_str, 'value': float(value)})
            except:
                pass

    result = pd.DataFrame(records)
    result = result.sort_values('date').reset_index(drop=True)

    print(f"Transformed: {len(result)} records")
    print(f"Date range: {result['date'].min()} to {result['date'].max()}")

    return result


def transform_cpi(filepath: str = "data/cpi.csv") -> pd.DataFrame:
    """Transform CPI data to long format"""
    print("\n" + "="*60)
    print("Transforming CPI data")
    print("="*60)

    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

    # Select "All Items" row
    target_row = df[df['DataSeries'].str.contains('All Items', case=False, na=False)]

    if target_row.empty:
        print("Warning: Could not find 'All Items' row")
        target_row = df.iloc[[0]]

    print(f"Selected: {target_row['DataSeries'].values[0]}")

    # Get date columns (monthly format like 2025Oct)
    date_cols = [c for c in df.columns if re.match(r'\d{4}[A-Za-z]+', c)]
    print(f"Found {len(date_cols)} monthly columns")

    # Transform to long format
    records = []
    for col in date_cols:
        date_str = parse_month_date(col)
        if date_str:
            value = target_row[col].values[0]
            try:
                records.append({'date': date_str, 'value': float(value)})
            except:
                pass

    result = pd.DataFrame(records)
    result = result.sort_values('date').reset_index(drop=True)

    print(f"Transformed: {len(result)} records")
    print(f"Date range: {result['date'].min()} to {result['date'].max()}")

    return result


def transform_wage(filepath: str = "data/wage.csv") -> pd.DataFrame:
    """Transform wage data to long format"""
    print("\n" + "="*60)
    print("Transforming WAGE data")
    print("="*60)

    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)[:10]}...")

    # Check structure
    if 'DataSeries' not in df.columns:
        print("Note: Different structure, attempting direct parse")
        # May already be in a different format
        if 'date' in df.columns and 'value' in df.columns:
            return df[['date', 'value']]

    # Try to find wage-related row
    patterns = ['Total', 'Basic Wage', 'Overall', 'All']

    target_row = None
    for pattern in patterns:
        if 'DataSeries' in df.columns:
            match = df[df['DataSeries'].str.contains(pattern, case=False, na=False)]
            if not match.empty:
                target_row = match.iloc[[0]]
                break

    if target_row is None:
        target_row = df.iloc[[0]]

    if 'DataSeries' in df.columns:
        print(f"Selected: {target_row['DataSeries'].values[0]}")

    # Get date columns (quarterly)
    date_cols = [c for c in df.columns if re.match(r'\d{4}\dQ', c)]

    if not date_cols:
        # Try monthly format
        date_cols = [c for c in df.columns if re.match(r'\d{4}[A-Za-z]+', c)]

    print(f"Found {len(date_cols)} date columns")

    # Transform to long format
    records = []
    for col in date_cols:
        date_str = parse_quarter_date(col) or parse_month_date(col)
        if date_str:
            value = target_row[col].values[0]
            try:
                records.append({'date': date_str, 'value': float(value)})
            except:
                pass

    result = pd.DataFrame(records)
    if not result.empty:
        result = result.sort_values('date').reset_index(drop=True)
        print(f"Transformed: {len(result)} records")
        print(f"Date range: {result['date'].min()} to {result['date'].max()}")
    else:
        print("Warning: No data transformed for wage")

    return result


def main():
    """Transform all datasets"""
    print("\n" + "="*60)
    print("SINGSTAT DATA TRANSFORMATION")
    print("Wide format → Long format (date, value)")
    print("="*60)

    # Transform each dataset
    unemployment_df = transform_unemployment()
    gdp_df = transform_gdp()
    cpi_df = transform_cpi()
    wage_df = transform_wage()

    # Save transformed data
    print("\n" + "="*60)
    print("SAVING TRANSFORMED DATA")
    print("="*60)

    unemployment_df.to_csv("data/unemployment_clean.csv", index=False)
    print("✓ Saved data/unemployment_clean.csv")

    gdp_df.to_csv("data/gdp_clean.csv", index=False)
    print("✓ Saved data/gdp_clean.csv")

    cpi_df.to_csv("data/cpi_clean.csv", index=False)
    print("✓ Saved data/cpi_clean.csv")

    if not wage_df.empty:
        wage_df.to_csv("data/wage_clean.csv", index=False)
        print("✓ Saved data/wage_clean.csv")

    # Summary
    print("\n" + "="*60)
    print("TRANSFORMATION SUMMARY")
    print("="*60)

    print(f"\n{'Indicator':<20} {'Records':<10} {'Date Range'}")
    print("-" * 60)
    print(f"{'Unemployment':<20} {len(unemployment_df):<10} {unemployment_df['date'].min()} to {unemployment_df['date'].max()}")
    print(f"{'GDP':<20} {len(gdp_df):<10} {gdp_df['date'].min()} to {gdp_df['date'].max()}")
    print(f"{'CPI':<20} {len(cpi_df):<10} {cpi_df['date'].min()} to {cpi_df['date'].max()}")
    if not wage_df.empty:
        print(f"{'Wage':<20} {len(wage_df):<10} {wage_df['date'].min()} to {wage_df['date'].max()}")

    # Display sample data
    print("\n" + "="*60)
    print("SAMPLE DATA (Last 5 Records Each)")
    print("="*60)

    print("\nUnemployment:")
    print(unemployment_df.tail().to_string(index=False))

    print("\nGDP:")
    print(gdp_df.tail().to_string(index=False))

    print("\nCPI:")
    print(cpi_df.tail().to_string(index=False))

    if not wage_df.empty:
        print("\nWage:")
        print(wage_df.tail().to_string(index=False))

    return {
        'unemployment': unemployment_df,
        'gdp': gdp_df,
        'cpi': cpi_df,
        'wage': wage_df
    }


if __name__ == "__main__":
    data = main()
