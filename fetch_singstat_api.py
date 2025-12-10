"""
Data.gov.sg API Fetcher for SingStat Economic Indicators
Fetches unemployment, CPI, GDP, and wage data via API
"""

import requests
import pandas as pd
import json
from typing import Optional, Dict, Any
import time

# Dataset IDs from data.gov.sg
DATASETS = {
    "unemployment": {
        "id": "d_b816a930bca0eb19fdf20fcbfcdd4c39",
        "name": "Unemployment Rate (Quarterly, Seasonally Adjusted)",
        "file": "unemployment.csv"
    },
    "cpi": {
        "id": "d_bdaff844e3ef89d39fceb962ff8f0791",
        "name": "Consumer Price Index (2024 Base Year, Monthly)",
        "file": "cpi.csv"
    },
    "gdp": {
        "id": "d_a5ff719648a0e6d4b4c623ee383ab686",
        "name": "GDP Year-on-Year Growth Rate (Quarterly)",
        "file": "gdp.csv"
    },
    "wage": {
        "id": "d_7f59ea6dc7b3dbecb828f64935537df6",  # Basic wage change dataset
        "name": "Basic Wage Change (Quarterly)",
        "file": "wage.csv"
    }
}

# API endpoint patterns to try
API_ENDPOINTS = [
    # Pattern 1: New v2 API
    "https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/poll-download",
    # Pattern 2: Direct download
    "https://data.gov.sg/api/action/datastore_search?resource_id={dataset_id}&limit=10000",
    # Pattern 3: CKAN-style
    "https://data.gov.sg/dataset/{dataset_id}/download",
    # Pattern 4: Beta API
    "https://beta.data.gov.sg/api/3/action/datastore_search?resource_id={dataset_id}&limit=10000",
    # Pattern 5: v1 initiate download
    "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/initiate-download",
    # Pattern 6: v2 initiate download
    "https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/initiate-download",
]


def fetch_with_endpoint(dataset_id: str, endpoint_pattern: str) -> Optional[Dict]:
    """Try fetching data with a specific endpoint pattern"""
    url = endpoint_pattern.format(dataset_id=dataset_id)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            # Check if JSON response
            try:
                data = response.json()
                return {"success": True, "data": data, "url": url}
            except:
                # Might be CSV data
                if response.text.strip():
                    return {"success": True, "data": response.text, "url": url, "type": "csv"}

        return {"success": False, "status": response.status_code, "url": url}

    except Exception as e:
        return {"success": False, "error": str(e), "url": url}


def initiate_download(dataset_id: str) -> Optional[str]:
    """
    Use the initiate-download endpoint which returns a download URL
    This is the recommended approach for data.gov.sg
    """
    # Try v2 API first
    url = f"https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/initiate-download"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    print(f"  Initiating download from: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)[:500]}")

            # The response should contain a download URL
            if "data" in data and "url" in data["data"]:
                return data["data"]["url"]
            elif "url" in data:
                return data["url"]
            elif "download_url" in data:
                return data["download_url"]
            else:
                print(f"  Unexpected response structure: {list(data.keys())}")
                return None
        else:
            print(f"  Failed: {response.text[:300]}")
            return None

    except Exception as e:
        print(f"  Error: {str(e)}")
        return None


def download_csv(url: str) -> Optional[pd.DataFrame]:
    """Download CSV from the provided URL"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    try:
        response = requests.get(url, headers=headers, timeout=60)

        if response.status_code == 200:
            # Parse CSV from response
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return df
        else:
            print(f"  Download failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"  Download error: {str(e)}")
        return None


def fetch_dataset(indicator: str, config: Dict) -> Optional[pd.DataFrame]:
    """Fetch a single dataset using the data.gov.sg API"""

    print(f"\n{'='*70}")
    print(f"Fetching: {config['name']}")
    print(f"Dataset ID: {config['id']}")
    print(f"{'='*70}")

    # Method 1: Try initiate-download endpoint
    print("\nMethod 1: Initiate Download API")
    download_url = initiate_download(config['id'])

    if download_url:
        print(f"  Got download URL: {download_url[:80]}...")
        df = download_csv(download_url)
        if df is not None:
            print(f"  ✓ Success! Downloaded {len(df)} rows")
            return df

    # Method 2: Try other endpoint patterns
    print("\nMethod 2: Trying alternative endpoints...")
    for i, pattern in enumerate(API_ENDPOINTS, 1):
        print(f"  Attempt {i}: {pattern[:50]}...")
        result = fetch_with_endpoint(config['id'], pattern)

        if result.get("success"):
            print(f"  ✓ Got response from: {result['url']}")

            if result.get("type") == "csv":
                from io import StringIO
                df = pd.read_csv(StringIO(result["data"]))
                return df
            elif isinstance(result.get("data"), dict):
                # Parse JSON response
                if "result" in result["data"] and "records" in result["data"]["result"]:
                    df = pd.DataFrame(result["data"]["result"]["records"])
                    return df

        time.sleep(0.5)  # Rate limiting

    print(f"\n✗ Failed to fetch {indicator}")
    return None


def main():
    """Main function to fetch all datasets"""

    print("\n" + "="*70)
    print("DATA.GOV.SG API FETCHER")
    print("Fetching 4 SingStat Economic Indicators")
    print("="*70)

    results = {}

    for indicator, config in DATASETS.items():
        df = fetch_dataset(indicator, config)

        if df is not None:
            results[indicator] = df

            # Save to CSV
            filepath = f"data/{config['file']}"
            df.to_csv(filepath, index=False)
            print(f"\n✓ Saved to {filepath}")

            # Show preview
            print(f"\nPreview of {indicator}:")
            print(f"Columns: {list(df.columns)}")
            print(df.head(3).to_string())
        else:
            results[indicator] = None

        time.sleep(1)  # Rate limiting between datasets

    # Summary
    print("\n" + "="*70)
    print("FETCH SUMMARY")
    print("="*70)

    success_count = sum(1 for v in results.values() if v is not None)
    print(f"\nSuccessfully fetched: {success_count}/4 datasets")

    for indicator, df in results.items():
        if df is not None:
            print(f"  ✓ {indicator}: {len(df)} rows")
        else:
            print(f"  ✗ {indicator}: FAILED")

    if success_count < 4:
        print("\n" + "="*70)
        print("MANUAL DOWNLOAD REQUIRED")
        print("="*70)
        print("\nSome datasets couldn't be fetched via API.")
        print("Please download manually from:")
        for indicator, df in results.items():
            if df is None:
                config = DATASETS[indicator]
                print(f"\n{indicator}:")
                print(f"  https://data.gov.sg/datasets/{config['id']}/view")

    return results


if __name__ == "__main__":
    results = main()
