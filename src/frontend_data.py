"""
Frontend data payload builder.

This module transforms backend pipeline outputs into frontend-ready JSON payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

import config
from src.data_loader import parse_dates


INDICATOR_LABELS = {
    "gdp": "GDP Growth",
    "cpi": "Consumer Price Inflation",
    "unemployment": "Unemployment Rate",
}

METHODOLOGY_SUMMARY = (
    "The Singapore Economic Stress Monitor combines normalized GDP, CPI, and unemployment indicators into "
    "a composite 0-100 stress score. Higher values indicate higher macroeconomic stress."
)

METHODOLOGY_DETAILS = (
    "1) Load indicator data and align to monthly frequency.\n"
    "2) Normalize each indicator to a 0-100 stress scale with rolling z-scores and sigmoid mapping.\n"
    "3) Combine normalized indicators using configured weights:\n"
    f"   - GDP: {config.INDICATOR_WEIGHTS['gdp']:.0%}\n"
    f"   - CPI: {config.INDICATOR_WEIGHTS['cpi']:.0%}\n"
    f"   - Unemployment: {config.INDICATOR_WEIGHTS['unemployment']:.0%}\n"
    "4) Classify stress bands from composite score:\n"
    "   - Low: 0-25\n"
    "   - Moderate: 26-50\n"
    "   - Elevated: 51-75\n"
    "   - High: 76-100"
)


def _score_to_band(score: float) -> str:
    if score <= 25:
        return "Low"
    if score <= 50:
        return "Moderate"
    if score <= 75:
        return "Elevated"
    return "High"


def _format_month(period: pd.Timestamp) -> str:
    return period.strftime("%Y-%m")


def _safe_date_from_series(filepath: str) -> str:
    dataset = pd.read_csv(filepath)
    if "date" not in dataset.columns or dataset.empty:
        return ""

    parsed_dates: List[pd.Timestamp] = []
    for raw_value in dataset["date"].dropna().tolist():
        try:
            parsed_dates.append(parse_dates(str(raw_value)))
        except Exception:
            continue

    if not parsed_dates:
        return ""

    return max(parsed_dates).strftime("%Y-%m-%d")


def _build_drivers(stress_df: pd.DataFrame) -> List[Dict]:
    valid_scores = stress_df.dropna(subset=["composite_score"])
    if len(valid_scores) < 2:
        return []

    latest_row = valid_scores.iloc[-1]
    previous_row = valid_scores.iloc[-2]

    drivers: List[Dict] = []
    for indicator_name in config.INDICATOR_WEIGHTS:
        column = f"{indicator_name}_score"
        delta = float(latest_row[column] - previous_row[column])

        if abs(delta) < 1e-9:
            continue

        drivers.append(
            {
                "name": INDICATOR_LABELS.get(indicator_name, indicator_name.upper()),
                "contribution": round(delta, 1),
                "direction": "negative" if delta > 0 else "positive",
            }
        )

    return drivers


def build_frontend_payload(stress_df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Build frontend payload dictionaries from stress results.
    """
    valid_scores = stress_df.dropna(subset=["composite_score"])
    if valid_scores.empty:
        raise ValueError("No valid stress scores available for frontend payload.")

    latest_row = valid_scores.iloc[-1]
    latest_score = float(latest_row["composite_score"])

    one_month_change = 0.0
    if len(valid_scores) >= 2:
        one_month_change = latest_score - float(valid_scores["composite_score"].iloc[-2])

    three_month_change = 0.0
    if len(valid_scores) >= 4:
        three_month_change = latest_score - float(valid_scores["composite_score"].iloc[-4])
    elif len(valid_scores) >= 2:
        three_month_change = one_month_change

    history: List[Dict] = []
    for date_index, row in valid_scores.iterrows():
        entry = {
            "date": _format_month(date_index),
            "score": round(float(row["composite_score"]), 1),
        }
        if row.get("alert_level") == "Red":
            entry["regime"] = "high-volatility"
        history.append(entry)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    latest_payload = {
        "projectId": config.PROJECT_ID,
        "stressScore": round(latest_score, 1),
        "stressBand": _score_to_band(latest_score),
        "oneMonthChange": round(one_month_change, 1),
        "threeMonthChange": round(three_month_change, 1),
        "lastUpdated": generated_at,
        "githubUrl": config.PROJECT_REPOSITORY_URL,
        "summary": (
            "A composite indicator tracking financial stress in Singapore's economy using publicly "
            "available macroeconomic data."
        ),
    }

    source_records: List[Dict] = []
    for indicator_name, filepath in config.DATA_FILES.items():
        metadata = config.SOURCE_METADATA.get(indicator_name)
        if metadata is None:
            continue

        source_records.append(
            {
                "name": metadata["name"],
                "url": metadata["url"],
                "lastUpdated": _safe_date_from_series(filepath),
            }
        )

    indicators_payload = {
        "projectId": config.PROJECT_ID,
        "drivers": _build_drivers(valid_scores),
        "methodology": {
            "summary": METHODOLOGY_SUMMARY,
            "details": METHODOLOGY_DETAILS,
        },
        "sources": source_records,
    }

    return {
        "latest": latest_payload,
        "history": history,
        "indicators": indicators_payload,
    }


def write_frontend_payload(payload: Dict[str, Dict], output_dir: str) -> Tuple[str, str, str]:
    """
    Write latest/history/indicators payloads into an output directory.
    """
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    latest_path = target_dir / "latest.json"
    history_path = target_dir / "history.json"
    indicators_path = target_dir / "indicators.json"

    latest_path.write_text(json.dumps(payload["latest"], indent=2) + "\n", encoding="utf-8")
    history_path.write_text(json.dumps(payload["history"], indent=2) + "\n", encoding="utf-8")
    indicators_path.write_text(json.dumps(payload["indicators"], indent=2) + "\n", encoding="utf-8")

    return (str(latest_path), str(history_path), str(indicators_path))
