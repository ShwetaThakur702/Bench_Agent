"""
pipeline/persistence.py — Phase 6 database persistence layer.

Exposes three functions:
    save_snapshot(snapshot_dict)    → 1 row in bench_snapshots
    save_forecast(forecast_df)      → 91 rows in bench_forecasts
    save_alerts(alerts_df, freeze_df) → R3 + R4 rows in bench_alerts

Design rules:
  - psycopg2 only, no ORM.
  - One connection per call: open → insert → commit → close.
  - DB unavailable: log warning and return — never crash the pipeline.
  - TC2: no Emplid or individual employee data is persisted here.
"""
from __future__ import annotations

import json
import logging
import math
import os
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _connect():
    import psycopg2
    url = os.getenv("POSTGRES_URL", "postgresql://localhost/bench_agent")
    return psycopg2.connect(url)


# ---------------------------------------------------------------------------
# JSON serialisation — converts pandas/numpy types to JSON-safe Python
# ---------------------------------------------------------------------------

def _to_safe(obj: Any) -> Any:
    if isinstance(obj, pd.Series):
        return {str(k): _to_safe(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: _to_safe(v) for k, v in obj.items()}
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, float) and math.isnan(obj):
        return None
    try:
        if pd.isnull(obj):
            return None
    except (TypeError, ValueError):
        pass
    return obj


def _dumps(obj: Any) -> str:
    return json.dumps(_to_safe(obj))


# ---------------------------------------------------------------------------
# save_snapshot — 1 row per run
# ---------------------------------------------------------------------------

def save_snapshot(snapshot_dict: dict) -> None:
    """Insert one R1 snapshot row into bench_snapshots."""
    try:
        conn = _connect()
    except Exception as exc:
        logger.warning("persistence.save_snapshot: DB unavailable (%s) — skipping", exc)
        return

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bench_snapshots (run_date, total_headcount, snapshot_json)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        snapshot_dict.get("run_date"),
                        int(snapshot_dict["total_headcount"]),
                        _dumps(snapshot_dict),
                    ),
                )
        logger.info("persistence.save_snapshot: 1 row inserted into bench_snapshots")
    except Exception as exc:
        logger.warning("persistence.save_snapshot: insert failed (%s) — skipping", exc)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# save_forecast — 91 rows per run
# ---------------------------------------------------------------------------

def save_forecast(forecast_df: pd.DataFrame) -> None:
    """Bulk-insert R2 daily forecast rows into bench_forecasts."""
    try:
        conn = _connect()
    except Exception as exc:
        logger.warning("persistence.save_forecast: DB unavailable (%s) — skipping", exc)
        return

    rows = []
    for _, r in forecast_df.iterrows():
        fd = r["forecast_date"]
        rows.append((
            str(r["run_date"]) if "run_date" in r.index else str(pd.Timestamp.today().date()),
            fd.strftime("%Y-%m-%d") if isinstance(fd, pd.Timestamp) else str(fd),
            int(r["days_from_today"]),
            int(r["total_forecast_bench"]),
            int(r["confirmed_count"]),
            int(r["projected_count"]),
            str(r["forecast_confidence_band"]),
            str(r["bucket"]),
        ))

    try:
        with conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO bench_forecasts
                        (run_date, forecast_date, days_from_today, total_forecast_bench,
                         confirmed_count, projected_count, forecast_confidence_band, bucket)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )
        logger.info("persistence.save_forecast: %d rows inserted into bench_forecasts", len(rows))
    except Exception as exc:
        logger.warning("persistence.save_forecast: insert failed (%s) — skipping", exc)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# save_alerts — R3 threshold alerts + R4 hiring freeze, unified table
# ---------------------------------------------------------------------------

def save_alerts(alerts_df: pd.DataFrame, freeze_df: pd.DataFrame) -> None:
    """Insert R3 threshold alerts and R4 hiring-freeze rows into bench_alerts.

    R3 rows → alert_type='threshold', llm_narrative=NULL
    R4 rows → alert_type='freeze',    llm_narrative from freeze_df if present
    """
    try:
        conn = _connect()
    except Exception as exc:
        logger.warning("persistence.save_alerts: DB unavailable (%s) — skipping", exc)
        return

    today = str(pd.Timestamp.today().date())
    rows: list[tuple] = []

    # R3 threshold alerts
    for _, r in alerts_df.iterrows():
        rows.append((
            str(r.get("run_date", today)),
            "threshold",
            str(r["org_slice"]),
            int(r["current_bench_count"]),
            int(r["bench_threshold"]),
            float(r["breach_amount"]),
            str(r["alert_severity"]),
            str(r.get("recommended_action", "")),
            None,                           # no LLM narrative for threshold alerts
        ))

    # R4 hiring-freeze advisory
    has_narrative = "llm_narrative" in freeze_df.columns
    for _, r in freeze_df.iterrows():
        severity = "FREEZE" if bool(r["freeze_recommended"]) else "OK"
        narrative = str(r["llm_narrative"]) if has_narrative and pd.notna(r.get("llm_narrative")) else None
        rows.append((
            str(r.get("run_date", today)),
            "freeze",
            str(r["skill"]),
            int(r["total_supply"]),
            int(r["open_demand_count"]),
            float(r["supply_surplus"]),
            severity,
            str(r.get("advisory_note", "")),
            narrative,
        ))

    try:
        with conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO bench_alerts
                        (run_date, alert_type, org_slice_or_skill, current_count,
                         threshold_or_demand, breach_or_surplus, alert_severity,
                         recommended_action, llm_narrative)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )
        r3 = len(alerts_df)
        r4 = len(freeze_df)
        logger.info(
            "persistence.save_alerts: %d rows inserted into bench_alerts (%d threshold + %d freeze)",
            len(rows), r3, r4,
        )
    except Exception as exc:
        logger.warning("persistence.save_alerts: insert failed (%s) — skipping", exc)
    finally:
        conn.close()
