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
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pipeline.exclusion_filters import apply_exclusion_filters
from pipeline.feature_engineering import engineer_features
from pipeline.ingestion import load_all
from pipeline.preprocessing import preprocess_ris
from pipeline.r1_bench_snapshot import compute_bench_snapshot
from pipeline.r2_forecast import compute_daily_forecast, compute_org_slice_forecast
from pipeline.r3_threshold import compute_threshold_alerts
from pipeline.action_advisor import compute_actions
from pipeline.digest_generator import generate_daily_digest, generate_meeting_agenda, generate_rm_nudges
from pipeline.r4_hiring_freeze import compute_hiring_freeze, compute_deployment_matches

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
    # raw data (set at startup)
    "ready": False,
    "error": None,
    "enriched_bench_df": None,
    "threshold_df": None,
    "so_ageing_df": None,
    "skill_df": None,
    # computed results (set at startup, served directly by endpoints)
    "snapshot": None,
    "daily_forecast": None,
    "org_breakdown": None,
    "alerts": None,
    "freeze_df_llm": None,
    "deployment_matches": None,
    "actions": None,
    "digest": None,
    "rm_nudges": None,
    "agenda": None,
}


def _run_startup_pipeline() -> None:
    """Run full pipeline once at startup — ingestion through all rule modules + LLM calls."""
    logger.info("=== Startup: running ingestion pipeline ===")
    try:
        raw = load_all()
        ris_df = preprocess_ris(raw["ris"])
        deployable_df, _ = apply_exclusion_filters(ris_df)
        enriched_df = engineer_features(deployable_df, raw["threshold"])

        logger.info("Startup complete — %d deployable bench rows cached", len(enriched_df))

        # Pre-compute all rule outputs (including LLM calls) so endpoints serve from cache
        logger.info("=== Startup: pre-computing rule outputs ===")
        snapshot    = compute_bench_snapshot(enriched_df)
        daily_fc    = compute_daily_forecast(enriched_df)
        org_bd      = compute_org_slice_forecast(enriched_df)
        alerts_df   = compute_threshold_alerts(enriched_df, raw["threshold"])
        freeze_df   = compute_hiring_freeze(enriched_df, raw["so_ageing"], raw["skill"])
        freeze_llm  = _add_llm_narrative(freeze_df)
        dep_matches = compute_deployment_matches(enriched_df, raw["so_ageing"])
        actions     = compute_actions(snapshot, daily_fc, alerts_df, freeze_llm)
        digest      = generate_daily_digest(snapshot, daily_fc, alerts_df, freeze_llm, actions)
        agenda      = generate_meeting_agenda(snapshot, daily_fc, alerts_df, freeze_llm, actions)
        rm_nudges   = generate_rm_nudges(enriched_df)

        # Set ready=True only after ALL outputs are cached — prevents 500s on early requests
        _cache.update({
            "ready": True,
            "error": None,
            "enriched_bench_df": enriched_df,
            "threshold_df":      raw["threshold"],
            "so_ageing_df":      raw["so_ageing"],
            "skill_df":          raw["skill"],
            "snapshot":           snapshot,
            "daily_forecast":     daily_fc,
            "org_breakdown":      org_bd,
            "alerts":             alerts_df,
            "freeze_df_llm":      freeze_llm,
            "deployment_matches": dep_matches,
            "actions":            actions,
            "digest":             digest,
            "agenda":             agenda,
            "rm_nudges":          rm_nudges,
        })
        logger.info("=== Startup: all rule outputs cached — endpoints will respond instantly ===")

    except Exception as exc:
        _cache["ready"] = False
        _cache["error"] = str(exc)
        logger.error("Startup pipeline FAILED: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    import threading
    threading.Thread(target=_run_startup_pipeline, daemon=True).start()
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

    snap = _cache["snapshot"]
    payload = {
        "total_headcount":        snap["total_headcount"],
        "at_risk_count":          snap["at_risk_count"],
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
    sliced = _cache["daily_forecast"][_cache["daily_forecast"]["days_from_today"] <= days]
    return JSONResponse(content=_clean_records(sliced))


# ---------------------------------------------------------------------------
# GET /api/bench/alerts — R3
# ---------------------------------------------------------------------------

@app.get("/api/bench/forecast/org-breakdown")
def get_forecast_org_breakdown():
    """Return release counts per org slice per bucket for the stacked breakdown chart."""
    if not _cache["ready"]:
        return _pipeline_error()
    return JSONResponse(content=_clean_records(_cache["org_breakdown"]))


@app.get("/api/bench/alerts")
def get_alerts():
    if not _cache["ready"]:
        return _pipeline_error()
    return JSONResponse(content=_clean_records(_cache["alerts"]))


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

@app.get("/api/bench/actions")
def get_actions():
    """Return agentic action recommendations from all rule outputs."""
    if not _cache["ready"]:
        return _pipeline_error()
    return JSONResponse(content=_cache["actions"])


def _get_grade_band(grade) -> str:
    if pd.isna(grade) or not str(grade).strip():
        return 'Others'
    g = str(grade).upper().strip()
    if g.startswith('IS'): return 'IS Band'
    if g.startswith('DT'): return 'DT Band'
    if g.startswith('DM'): return 'DM Band'
    if g.startswith('DP'): return 'DP Band'
    if g.startswith('BC'): return 'BC Band'
    if g.startswith('LN'): return 'LN Band'
    if g.startswith('I'):  return 'I Band'
    return 'Others'


@app.get("/api/bench/deployment-matches")
def get_deployment_matches(grade_band: str = "All"):
    """Return skill-level supply-demand match table. TC2: aggregated counts only.
    Optional ?grade_band=IS+Band filters bench to that grade before recomputing.
    """
    if not _cache["ready"]:
        return _pipeline_error()

    if grade_band == "All":
        return JSONResponse(content=_clean_records(_cache["deployment_matches"]))

    bench_df = _cache["enriched_bench_df"].copy()
    bench_df["_gb"] = bench_df["Grade"].apply(_get_grade_band)
    filtered = bench_df[bench_df["_gb"] == grade_band].drop(columns=["_gb"])

    if filtered.empty:
        return JSONResponse(content=[])

    result = compute_deployment_matches(filtered, _cache["so_ageing_df"])
    return JSONResponse(content=_clean_records(result))


@app.get("/api/bench/digest")
def get_digest():
    """Return daily bench intelligence digest. TC2: LLM receives only aggregate counts."""
    if not _cache["ready"]:
        return _pipeline_error()
    return JSONResponse(content=_cache["digest"])


@app.get("/api/bench/meeting-agenda")
def get_meeting_agenda():
    """Return the weekly bench review meeting agenda. Rule-based — no LLM call."""
    if not _cache["ready"]:
        return _pipeline_error()
    return JSONResponse(content=_cache["agenda"])


@app.get("/api/bench/rm-nudges")
def get_rm_nudges():
    """Return RM nudge emails for bench employees >60 days without pipeline status.
    Rule-based only. TC2: email bodies contain counts and skills only — no employee names.
    """
    if not _cache["ready"]:
        return _pipeline_error()
    return JSONResponse(content=_cache["rm_nudges"])


@app.get("/api/bench/download")
def download_excel():
    """Return the most recent BA_Dashboard Excel file as a download."""
    output_dir = Path(__file__).parent / "output"
    files = sorted(output_dir.glob("BA_Dashboard_*.xlsx"), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No Excel report found. Run the pipeline first.")
    latest = files[0]
    return FileResponse(
        path=str(latest),
        filename=latest.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/bench/hiring-freeze")
def get_hiring_freeze():
    if not _cache["ready"]:
        return _pipeline_error()
    return JSONResponse(content=_clean_records(_cache["freeze_df_llm"]))


# ---------------------------------------------------------------------------
# React UI — static assets + SPA catch-all (must be last)
# ---------------------------------------------------------------------------

_UI_DIST = Path(__file__).parent / "ui" / "dist"

if (_UI_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(_UI_DIST / "assets")), name="ui_assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    index = _UI_DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(
        status_code=404,
        detail="UI not built. Run: cd ui && npm run build",
    )
