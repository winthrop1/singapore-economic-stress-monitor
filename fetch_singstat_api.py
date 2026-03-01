"""
Data.gov.sg API Fetcher for SingStat Economic Indicators
Fetches unemployment, CPI, and GDP data via the v1 API.
"""

import sys
import requests
import pandas as pd
from io import StringIO
from typing import Optional, Dict
import time

# Correct v1 API base (api-open, not api-production)
_API_BASE = "https://api-open.data.gov.sg/v1/public/api/datasets"

# Required datasets — pipeline fails if any of these can't be fetched
REQUIRED_DATASETS = {
    "unemployment": {
        "id": "d_b816a930bca0eb19fdf20fcbfcdd4c39",
        "name": "Unemployment Rate (Quarterly, Seasonally Adjusted)",
        "file": "unemployment.csv",
    },
    "cpi": {
        "id": "d_bdaff844e3ef89d39fceb962ff8f0791",
        "name": "Consumer Price Index (2024 Base Year, Monthly)",
        "file": "cpi.csv",
    },
    "gdp": {
        "id": "d_a5ff719648a0e6d4b4c623ee383ab686",
        "name": "GDP Year-on-Year Growth Rate (Quarterly)",
        "file": "gdp.csv",
    },
}

# Optional datasets — pipeline continues even if these fail
OPTIONAL_DATASETS: Dict = {}


def _download_dataset(dataset_id: str) -> Optional[pd.DataFrame]:
    """
    Download a dataset using the data.gov.sg v1 two-step API:
    1. GET initiate-download  → starts the export job
    2. GET poll-download       → repeat until the CSV URL is ready
    """
    headers = {"Accept": "application/json"}

    # Step 1: initiate
    initiate_url = f"{_API_BASE}/{dataset_id}/initiate-download"
    print(f"  Initiating: {initiate_url}")
    resp = requests.get(initiate_url, headers=headers, timeout=30)
    print(f"  Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"  Failed: {resp.text[:300]}")
        return None

    # Step 2: poll until URL is available (up to ~60 s)
    poll_url = f"{_API_BASE}/{dataset_id}/poll-download"
    for attempt in range(12):
        time.sleep(5)
        resp = requests.get(poll_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"  Poll {attempt + 1} failed: {resp.status_code} — retrying")
            continue
        body = resp.json()
        inner = body.get("data", body)
        csv_url = inner.get("url", "")
        status = inner.get("status", "")
        print(f"  Poll {attempt + 1}: status={status or '?'}")
        if csv_url:
            csv_resp = requests.get(csv_url, timeout=60)
            if csv_resp.status_code == 200:
                return pd.read_csv(StringIO(csv_resp.text))
            print(f"  CSV download failed: {csv_resp.status_code}")
            return None

    print("  No download URL obtained after polling")
    return None


def _fetch_and_save(indicator: str, cfg: Dict) -> Optional[pd.DataFrame]:
    print(f"\n{'='*70}")
    print(f"Fetching: {cfg['name']}")
    print(f"Dataset ID: {cfg['id']}")
    print(f"{'='*70}")

    df = _download_dataset(cfg["id"])
    if df is not None:
        filepath = f"data/{cfg['file']}"
        df.to_csv(filepath, index=False)
        print(f"\n✓ Saved {len(df)} rows → {filepath}")
        print(f"  Columns: {list(df.columns[:6])}{'...' if len(df.columns) > 6 else ''}")
    else:
        print(f"\n✗ Failed to fetch {indicator}")
    return df


def main():
    print("\n" + "=" * 70)
    print("DATA.GOV.SG API FETCHER")
    print("=" * 70)

    results = {}
    failed_required = []

    for indicator, cfg in REQUIRED_DATASETS.items():
        df = _fetch_and_save(indicator, cfg)
        results[indicator] = df
        if df is None:
            failed_required.append(indicator)
        time.sleep(1)

    for indicator, cfg in OPTIONAL_DATASETS.items():
        df = _fetch_and_save(indicator, cfg)
        results[indicator] = df
        if df is None:
            print(f"  (optional — pipeline will continue without {indicator})")
        time.sleep(1)

    # Summary
    print("\n" + "=" * 70)
    print("FETCH SUMMARY")
    print("=" * 70)
    for indicator, df in results.items():
        tag = "(optional)" if indicator in OPTIONAL_DATASETS else "(required)"
        if df is not None:
            print(f"  ✓ {indicator} {tag}: {len(df)} rows")
        else:
            print(f"  ✗ {indicator} {tag}: FAILED")

    if failed_required:
        print(f"\nERROR: {len(failed_required)} required dataset(s) could not be fetched: {failed_required}")
        print("Check dataset IDs at https://data.gov.sg and update REQUIRED_DATASETS.")
        sys.exit(1)

    return results


if __name__ == "__main__":
    main()
