"""
api.py — FastAPI REST server for Bench Agent (Phase 8).

Startup: ingestion + preprocessing pipeline runs once; enriched DataFrames
are cached in memory.  Each endpoint calls only its rule module on the
cache — no re-ingestion on request.

CORS is open for all origins so the static dashboard (file://) can connect.
"""
from __future__ import annotations

import json
import logging
import math
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pipeline.exclusion_filters import apply_exclusion_filters
from pipeline.feature_engineering import engineer_features
from pipeline.ingestion import load_all
from pipeline.preprocessing import preprocess_ris
from pipeline.r1_bench_snapshot import compute_bench_snapshot
from pipeline.r2_forecast import compute_daily_forecast
from pipeline.r3_threshold import compute_threshold_alerts
from pipeline.r4_hiring_freeze import compute_hiring_freeze

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM config (mirrors agent.py — all values driven by .env)
# ---------------------------------------------------------------------------
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
MOCK_LLM = os.getenv("MOCK_LLM", "false").lower() == "true"
_API_KEY = os.getenv("OPENAI_API_KEY", "")
_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

# ---------------------------------------------------------------------------
# In-memory pipeline cache
# ---------------------------------------------------------------------------
_cache: dict[str, Any] = {
    "ready": False,
    "error": None,
    "enriched_bench_df": None,
    "threshold_df": None,
    "so_ageing_df": None,
    "skill_df": None,
}


def _run_startup_pipeline() -> None:
    """Run ingestion → preprocessing → exclusions → feature engineering once."""
    logger.info("=== Startup: running ingestion pipeline ===")
    try:
        raw = load_all()
        ris_df = preprocess_ris(raw["ris"])
        deployable_df, _ = apply_exclusion_filters(ris_df)
        enriched_df = engineer_features(deployable_df, raw["threshold"])

        _cache.update({
            "ready": True,
            "error": None,
            "enriched_bench_df": enriched_df,
            "threshold_df": raw["threshold"],
            "so_ageing_df": raw["so_ageing"],
            "skill_df": raw["skill"],
        })
        logger.info(
            "Startup complete — %d deployable bench rows cached", len(enriched_df)
        )
    except Exception as exc:
        _cache["ready"] = False
        _cache["error"] = str(exc)
        logger.error("Startup pipeline FAILED: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    _run_startup_pipeline()
    yield


app = FastAPI(
    title="Bench Agent API",
    version="1.0.0",
    description="Advisory-only bench management API — never enforces decisions.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------

def _clean(val: Any) -> Any:
    """Convert numpy/pandas scalars to JSON-safe Python types. NaN/NaT → None."""
    if isinstance(val, pd.Timestamp):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        v = float(val)
        return None if math.isnan(v) else v
    if isinstance(val, np.bool_):
        return bool(val)
    if isinstance(val, float) and math.isnan(val):
        return None
    try:
        if pd.isnull(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _clean_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame → list of JSON-safe dicts."""
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def _clean_series(s: pd.Series) -> dict:
    """pd.Series (groupby counts) → JSON-safe dict with string keys."""
    return {str(k): _clean(v) for k, v in s.items()}


def _pipeline_error() -> JSONResponse:
    detail = _cache["error"] or "pipeline not ready"
    logger.warning("Endpoint called before pipeline ready: %s", detail)
    return JSONResponse(
        status_code=503,
        content={"error": "pipeline failed", "detail": detail},
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    bench_count = (
        len(_cache["enriched_bench_df"])
        if _cache["ready"] and _cache["enriched_bench_df"] is not None
        else 0
    )
    return {
        "status": "ok",
        "run_date": str(date.today()),
        "bench_count": bench_count,
        "pipeline_ready": _cache["ready"],
    }


# ---------------------------------------------------------------------------
# GET /api/bench/snapshot — R1
# ---------------------------------------------------------------------------

@app.get("/api/bench/snapshot")
def get_snapshot():
    if not _cache["ready"]:
        return _pipeline_error()

    snap = compute_bench_snapshot(_cache["enriched_bench_df"])

    payload = {
        "total_headcount":        snap["total_headcount"],
        "run_date":               snap["run_date"],
        "status_counts":          snap["status_counts"],
        "current_vs_future":      _clean_series(snap["current_vs_future"]),
        "aging_distribution":     _clean_series(snap["aging_distribution"]),
        "by_location":            _clean_series(snap["by_location"]),
        "by_bu":                  _clean_series(snap["by_bu"]),
        "by_grade":               _clean_series(snap["by_grade"]),
        "by_pool":                _clean_series(snap["by_pool"]),
        "by_country":             _clean_series(snap["by_country"]),
        "by_allocation_category": _clean_series(snap["by_allocation_category"]),
        "by_skill":               _clean_series(snap["by_skill"]),
    }
    return JSONResponse(content=payload)


# ---------------------------------------------------------------------------
# GET /api/bench/forecast — R2
# ---------------------------------------------------------------------------

@app.get("/api/bench/forecast")
def get_forecast(days: int = 90):
    """Return daily forecast rows.  Query param: ?days=30|60|90 (default 90)."""
    if not _cache["ready"]:
        return _pipeline_error()

    days = max(1, min(days, 90))
    daily_df = compute_daily_forecast(_cache["enriched_bench_df"])
    sliced = daily_df[daily_df["days_from_today"] <= days]
    return JSONResponse(content=_clean_records(sliced))


# ---------------------------------------------------------------------------
# GET /api/bench/alerts — R3
# ---------------------------------------------------------------------------

@app.get("/api/bench/alerts")
def get_alerts():
    if not _cache["ready"]:
        return _pipeline_error()

    alerts_df = compute_threshold_alerts(
        _cache["enriched_bench_df"],
        _cache["threshold_df"],
    )
    return JSONResponse(content=_clean_records(alerts_df))


# ---------------------------------------------------------------------------
# LLM narrative enrichment — mirrors run_r4_llm node in agent.py
# TC2: only aggregated skill-level stats are sent to the LLM (no PII)
# ---------------------------------------------------------------------------

def _add_llm_narrative(freeze_df: pd.DataFrame) -> pd.DataFrame:
    """Attach LLM narrative to each row. Falls back to advisory_note on error."""
    freeze_df = freeze_df.copy()
    freeze_rows = freeze_df[freeze_df["freeze_recommended"] == True]

    if freeze_rows.empty:
        freeze_df["llm_narrative"] = freeze_df["advisory_note"]
        return freeze_df

    if MOCK_LLM:
        logger.warning("MOCK_LLM=true — skipping LLM, using rule-based advisory_note")
        freeze_df["llm_narrative"] = freeze_df["advisory_note"]
        return freeze_df

    # Build TC2-compliant aggregated summary (no individual rows, no Emplid)
    lines = []
    for _, row in freeze_rows.iterrows():
        avg = row["avg_skill_rating"]
        avg_str = f"{avg:.2f}" if pd.notna(avg) else "N/A"
        lines.append(
            f"Skill: {row['skill']} | Supply: {int(row['total_supply'])} | "
            f"Demand: {int(row['open_demand_count'])} | Surplus: {int(row['supply_surplus'])} | "
            f"Avg Rating: {avg_str}"
        )
    summary = "\n".join(lines)

    narrative_map: dict[str, str] = {}
    try:
        from agents.bench_agent.prompts import HIRING_FREEZE_PROMPT
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI

        prompt = HIRING_FREEZE_PROMPT.format(supply_demand_summary=summary)
        logger.info("Calling LLM model=%s via %s", LLM_MODEL, _API_BASE)

        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=_API_KEY,
            openai_api_base=_API_BASE,
            temperature=0,
            max_tokens=2048,
            default_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "BenchAgent",
            },
            request_timeout=30,
        )
        raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()

        # Strip markdown fences if the model wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        for item in json.loads(raw):
            skill = item.get("skill", "")
            narrative = " ".join(filter(None, [
                item.get("recommendation", ""),
                item.get("rationale", ""),
                f"Review: {item.get('review_timeline', '')}",
            ])).strip()
            narrative_map[skill] = narrative

        logger.info("LLM narratives received for %d skills", len(narrative_map))

    except Exception as exc:
        logger.warning("LLM call failed (%s) — falling back to rule-based advisory_note", exc)

    freeze_df["llm_narrative"] = freeze_df.apply(
        lambda row: narrative_map.get(row["skill"], row["advisory_note"]),
        axis=1,
    )
    return freeze_df


# ---------------------------------------------------------------------------
# GET /api/bench/hiring-freeze — R4 rules + LLM narrative
# ---------------------------------------------------------------------------

@app.get("/api/bench/hiring-freeze")
def get_hiring_freeze():
    if not _cache["ready"]:
        return _pipeline_error()

    freeze_df = compute_hiring_freeze(
        _cache["enriched_bench_df"],
        _cache["so_ageing_df"],
        _cache["skill_df"],
    )
    freeze_df = _add_llm_narrative(freeze_df)
    return JSONResponse(content=_clean_records(freeze_df))
