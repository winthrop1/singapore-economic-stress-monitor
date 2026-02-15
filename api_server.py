#!/usr/bin/env python3
"""
Read-only API server for Singapore Economic Stress Monitor frontend payloads.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config
from main import run_dashboard
from src.frontend_data import build_frontend_payload, write_frontend_payload


def _parse_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if raw_origins.strip() == "*":
        return ["*"]

    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if origins:
        return origins

    return [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]


app = FastAPI(
    title="Singapore Economic Stress Monitor API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = _parse_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

DATA_DIR = Path(os.getenv("STRESS_API_DATA_DIR", os.path.join(config.BASE_DIR, "output", "dashboard_data")))
CACHE_TTL_SECONDS = int(os.getenv("STRESS_API_CACHE_TTL_SECONDS", "600"))

_cache_lock = threading.Lock()
_cache: Dict[str, Any] = {
    "payload": None,
    "loaded_at": 0.0,
}


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


def _read_payload_from_disk() -> Optional[Dict[str, Any]]:
    latest_path = DATA_DIR / "latest.json"
    history_path = DATA_DIR / "history.json"
    indicators_path = DATA_DIR / "indicators.json"

    if not latest_path.exists() or not history_path.exists() or not indicators_path.exists():
        return None

    return {
        "latest": json.loads(latest_path.read_text(encoding="utf-8")),
        "history": json.loads(history_path.read_text(encoding="utf-8")),
        "indicators": json.loads(indicators_path.read_text(encoding="utf-8")),
    }


def _generate_payload() -> Dict[str, Any]:
    results = run_dashboard(create_charts=False, verbose=False)
    payload = build_frontend_payload(results["stress_df"])
    write_frontend_payload(payload, str(DATA_DIR))
    return payload


def _load_payload() -> Dict[str, Any]:
    with _cache_lock:
        now = time.time()
        if _cache["payload"] and (now - _cache["loaded_at"]) < CACHE_TTL_SECONDS:
            return _cache["payload"]

        payload = _read_payload_from_disk()
        if payload is None:
            payload = _generate_payload()

        _cache["payload"] = payload
        _cache["loaded_at"] = now
        return payload


@app.get("/healthz")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "data_dir": str(DATA_DIR),
    }


@app.get("/api/stress-monitor/latest")
def get_latest() -> Dict[str, Any]:
    try:
        return _load_payload()["latest"]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Latest data unavailable") from exc


@app.get("/api/stress-monitor/history")
def get_history() -> Any:
    try:
        return _load_payload()["history"]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="History data unavailable") from exc


@app.get("/api/stress-monitor/indicators")
def get_indicators() -> Dict[str, Any]:
    try:
        return _load_payload()["indicators"]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Indicators data unavailable") from exc
