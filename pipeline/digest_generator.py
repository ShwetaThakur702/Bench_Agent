"""
pipeline/digest_generator.py — Daily Digest & RM Nudge Generator (Advisory only)

Two automations:
1. generate_daily_digest()  — aggregated daily intelligence report with LLM executive summary
2. generate_rm_nudges()     — rule-based RM nudge emails, counts + skills only

TC2 COMPLIANCE:
  - LLM receives only 5 aggregate counts (no PII, no Emplid)
  - RM nudge emails contain NO employee names — counts and skill groups only
"""
from __future__ import annotations

import math
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MOCK_LLM: bool = os.getenv("MOCK_LLM", "false").lower() == "true"
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

_EXCLUDED_STATUSES = frozenset({
    "Proposed - Pending Interview",
    "Proposed - Feedback Awaiting",
    "Shortlisted - To Be allocated",
})

_EXECUTIVE_SUMMARY_PROMPT = """\
You are a resource management intelligence system generating a daily bench management report.
Write a 3-4 sentence executive summary paragraph for senior leadership.

Aggregated bench data (no employee names or IDs):
- Total bench headcount: {total_bench}
- At-risk employees (bench >60 days, no proposed/shortlisted status): {at_risk_count}
- Active threshold breaches: {breach_count}
- Hiring freeze recommendations: {freeze_count}
- Projected bench additions in next 30 days: {releases_30d}

Write a professional 3-4 sentence paragraph covering bench health, key risks, and priorities.
No bullet points. Plain paragraph only. No preamble.\
"""


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------

def _to_json_safe(obj: Any) -> Any:
    """Recursively convert numpy/pandas types to JSON-safe Python types."""
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if math.isnan(v) else v
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, float) and math.isnan(obj):
        return None
    try:
        if pd.isnull(obj):
            return None
    except (TypeError, ValueError):
        pass
    return obj


def _safe_records(df: pd.DataFrame) -> list[dict]:
    return [_to_json_safe(row) for row in df.to_dict(orient="records")]


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _mock_executive_summary(total_bench: int, at_risk_count: int, breach_count: int,
                              freeze_count: int, releases_30d: int) -> str:
    risk_pct = round(at_risk_count / total_bench * 100) if total_bench > 0 else 0
    health_label = "requires immediate attention" if (breach_count > 0 or risk_pct > 10) else "is within acceptable parameters"
    return (
        f"The bench currently stands at {total_bench} deployable resources, with {at_risk_count} "
        f"({risk_pct}%) flagged as at-risk due to extended bench tenure without active deployment proposals. "
        f"There {'are' if breach_count > 0 else 'are no'} {breach_count} active threshold breach(es) requiring "
        f"immediate review, and {freeze_count} skill cluster(s) have been flagged for hiring freeze consideration. "
        f"With {releases_30d} additional resource(s) projected to join the bench within 30 days, "
        f"overall bench health {health_label} and warrants proactive deployment action from the RM team."
    )


def _call_summary_llm(total_bench: int, at_risk_count: int, breach_count: int,
                       freeze_count: int, releases_30d: int) -> str:
    """Generate executive summary via LLM. Falls back to rule-based text on error.
    TC2: only aggregate counts sent — no PII.
    """
    if MOCK_LLM:
        logger.warning("MOCK_LLM=true — returning mock executive summary")
        return _mock_executive_summary(total_bench, at_risk_count, breach_count, freeze_count, releases_30d)

    try:
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI

        prompt = _EXECUTIVE_SUMMARY_PROMPT.format(
            total_bench=total_bench,
            at_risk_count=at_risk_count,
            breach_count=breach_count,
            freeze_count=freeze_count,
            releases_30d=releases_30d,
        )
        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=_API_KEY,
            openai_api_base=_API_BASE,
            temperature=0.3,
            max_tokens=300,
            default_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "BenchAgent",
            },
            request_timeout=30,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content.strip()
        # Strip markdown fences if the model wraps the output
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()
        return text
    except Exception as exc:
        logger.warning("Executive summary LLM call failed (%s) — using rule-based fallback", exc)
        return _mock_executive_summary(total_bench, at_risk_count, breach_count, freeze_count, releases_30d)


# ---------------------------------------------------------------------------
# Automation 1: Daily Digest Generator
# ---------------------------------------------------------------------------

def generate_daily_digest(
    snapshot: dict,
    forecast: pd.DataFrame,
    alerts: pd.DataFrame,
    freeze: pd.DataFrame,
    actions: list[dict],
) -> dict:
    """Generate the daily bench intelligence digest.

    TC2: LLM receives only 5 aggregate counts — no PII, no Emplid.

    Parameters
    ----------
    snapshot : dict from compute_bench_snapshot()
    forecast : DataFrame from compute_daily_forecast()
    alerts   : DataFrame from compute_threshold_alerts()
    freeze   : DataFrame from compute_hiring_freeze()
    actions  : list of dicts from compute_actions()

    Returns
    -------
    JSON-safe dict with: report_date, report_title, executive_summary,
    bench_health, top_actions, threshold_breaches, freeze_recommendations,
    releases_in_30_days, generated_at
    """
    today = str(date.today())
    total_bench = int(snapshot.get("total_headcount", 0))
    at_risk_count = int(snapshot.get("at_risk_count", 0))

    # ---- current / future bench split ----
    cvf = snapshot.get("current_vs_future", {})
    current_bench = 0
    future_bench = 0
    try:
        current_bench = int(cvf.get("Current bench", 0) or 0)
        future_bench = int(cvf.get("Future bench", 0) or 0)
    except (AttributeError, TypeError, ValueError):
        pass

    # ---- threshold breaches ----
    breach_count = 0
    has_critical_high = False
    threshold_breaches: list[dict] = []
    if alerts is not None and not alerts.empty:
        breached = alerts[alerts["is_breached"] == True]
        breach_count = len(breached)
        has_critical_high = bool(breached["alert_severity"].isin(["CRITICAL", "HIGH"]).any())
        threshold_breaches = _safe_records(breached)

    # ---- freeze recommendations ----
    freeze_count = 0
    freeze_recommendations: list[dict] = []
    if freeze is not None and not freeze.empty:
        freeze_recs = freeze[freeze["freeze_recommended"] == True]
        freeze_count = len(freeze_recs)
        freeze_recommendations = _safe_records(freeze_recs)

    # ---- releases in 30 days (max cumulative future bench at day 30) ----
    releases_in_30_days = 0
    if forecast is not None and not forecast.empty:
        thirty_day = forecast[forecast["days_from_today"] <= 30]
        if not thirty_day.empty:
            max_val = thirty_day["total_forecast_bench"].max()
            releases_in_30_days = 0 if pd.isna(max_val) else int(max_val)

    # ---- bench health status ----
    # CRITICAL = any CRITICAL/HIGH breach; WATCH = any breach or at_risk > 10%; else HEALTHY
    risk_pct = at_risk_count / total_bench if total_bench > 0 else 0.0
    if has_critical_high:
        health_status = "CRITICAL"
    elif breach_count > 0 or risk_pct > 0.10:
        health_status = "WATCH"
    else:
        health_status = "HEALTHY"

    bench_health = {
        "total_bench": total_bench,
        "current_bench": current_bench,
        "future_bench": future_bench,
        "at_risk_count": at_risk_count,
        "status": health_status,
    }

    # ---- top 3 IMMEDIATE actions ----
    immediate = [a for a in actions if a.get("priority") == "IMMEDIATE"]
    top_actions = [_to_json_safe(a) for a in immediate[:3]]

    # ---- executive summary — only aggregate stats sent to LLM (TC2) ----
    executive_summary = _call_summary_llm(
        total_bench=total_bench,
        at_risk_count=at_risk_count,
        breach_count=breach_count,
        freeze_count=freeze_count,
        releases_30d=releases_in_30_days,
    )

    logger.info(
        "generate_daily_digest: status=%s, breaches=%d, freezes=%d, at_risk=%d, releases_30d=%d",
        health_status, breach_count, freeze_count, at_risk_count, releases_in_30_days,
    )

    return {
        "report_date": today,
        "report_title": "Bench Agent Daily Intelligence Report",
        "executive_summary": executive_summary,
        "bench_health": bench_health,
        "top_actions": top_actions,
        "threshold_breaches": threshold_breaches,
        "freeze_recommendations": freeze_recommendations,
        "releases_in_30_days": releases_in_30_days,
        "generated_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Automation 2: RM Nudge Email Generator
# ---------------------------------------------------------------------------

def generate_rm_nudges(deployable_bench_df: pd.DataFrame) -> list[dict]:
    """Generate RM nudge emails for employees with extended bench aging.

    Rule-based only — no LLM call.
    TC2: email body contains NO employee names — counts and skill groups only.

    Eligibility:
      - bench_aging_derived > 60 days
      - Final Status NOT IN {Proposed - Pending Interview, Proposed - Feedback Awaiting,
                              Shortlisted - To Be allocated}

    Returns
    -------
    list of dicts (one per RM), sorted HIGH urgency first:
      rm_name, employee_count, email_subject, email_body, urgency
    """
    df = deployable_bench_df.copy()

    aging_mask = df["bench_aging_derived"].fillna(0) > 60
    status_mask = ~df["Final Status"].fillna("").isin(_EXCLUDED_STATUSES)
    eligible = df[aging_mask & status_mask].copy()

    if eligible.empty:
        logger.info("generate_rm_nudges: no employees meet bench_aging > 60 + status criteria")
        return []

    logger.info("generate_rm_nudges: %d eligible employees across RMs", len(eligible))

    results = []
    for rm_name, rm_group in eligible.groupby("RM", dropna=True):
        if not rm_name or (isinstance(rm_name, float) and math.isnan(rm_name)):
            continue

        employee_count = len(rm_group)
        has_over_90 = bool((rm_group["bench_aging_derived"] > 90).any())
        urgency = "HIGH" if has_over_90 else "MEDIUM"

        # Group by skill — no individual names (TC2 compliant)
        skill_lines = []
        for skill, s_group in rm_group.groupby("Skiil", dropna=False):
            skill_label = str(skill) if (skill and not (isinstance(skill, float) and math.isnan(skill))) else "Unknown Skill"
            count = len(s_group)
            avg_aging = int(round(s_group["bench_aging_derived"].mean()))
            plural = "employees" if count > 1 else "employee"
            skill_lines.append(
                f"- {count} {plural} in {skill_label} with avg bench aging {avg_aging} days"
            )

        skill_section = "\n".join(skill_lines) if skill_lines else "- (skill data unavailable)"
        emp_label = "employees" if employee_count > 1 else "employee"

        email_subject = "Action Required — Bench Status Update Needed"
        email_body = (
            f"Hi {rm_name},\n\n"
            f"The following {employee_count} {emp_label} under your account have been on bench\n"
            f"for over 60 days without a proposed or shortlisted status.\n"
            f"Please update their deployment status in RIS by end of day.\n\n"
            f"Employees requiring status update:\n"
            f"{skill_section}\n\n"
            f"Current bench aging thresholds:\n"
            f"- >60 days without proposed status = escalation required\n"
            f"- >90 days = leadership review triggered\n\n"
            f"Please log into RIS and update the Final Status field for these resources.\n\n"
            f"This is an automated advisory from Bench Agent.\n"
            f"[Advisory only — Bench Agent cannot modify RIS]"
        )

        results.append({
            "rm_name": str(rm_name),
            "employee_count": employee_count,
            "email_subject": email_subject,
            "email_body": email_body,
            "urgency": urgency,
        })

    # HIGH first, then by employee_count descending within each urgency tier
    results.sort(key=lambda x: (0 if x["urgency"] == "HIGH" else 1, -x["employee_count"]))

    high_count = sum(1 for r in results if r["urgency"] == "HIGH")
    logger.info(
        "generate_rm_nudges: %d RM nudge emails generated (%d HIGH urgency)",
        len(results), high_count,
    )
    return results


# ---------------------------------------------------------------------------
# Automation 3: Meeting Agenda Generator
# ---------------------------------------------------------------------------

def generate_meeting_agenda(
    snapshot: dict,
    forecast: pd.DataFrame,
    alerts: pd.DataFrame,
    freeze: pd.DataFrame,
    actions: list[dict],
) -> dict:
    """Generate a structured weekly bench review meeting agenda.

    No LLM call — fully rule-based.
    No employee names or Emplids in output (TC2 compliant).

    Returns
    -------
    JSON-safe dict: meeting_date, meeting_date_human, meeting_title, prepared_by,
    sections (list of {section, duration_mins, points}), total_duration_mins, disclaimer
    """
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_monday = today + timedelta(days=days_ahead)
    meeting_date = next_monday.strftime("%Y-%m-%d")
    meeting_date_human = (
        next_monday.strftime("%A, ")
        + str(next_monday.day)
        + next_monday.strftime(" %B %Y")
    )

    # ---- bench health (same logic as digest) ----
    total_bench = int(snapshot.get("total_headcount", 0))
    at_risk = int(snapshot.get("at_risk_count", 0))
    cvf = snapshot.get("current_vs_future", {})
    current_bench = 0
    future_bench = 0
    try:
        current_bench = int(cvf.get("Current bench", 0) or 0)
        future_bench = int(cvf.get("Future bench", 0) or 0)
    except (AttributeError, TypeError, ValueError):
        pass

    breach_count = 0
    has_critical_high = False
    if alerts is not None and not alerts.empty:
        breached = alerts[alerts["is_breached"] == True]
        breach_count = len(breached)
        has_critical_high = bool(breached["alert_severity"].isin(["CRITICAL", "HIGH"]).any())
    risk_pct = at_risk / total_bench if total_bench > 0 else 0.0
    if has_critical_high:
        health_status = "CRITICAL"
    elif breach_count > 0 or risk_pct > 0.10:
        health_status = "WATCH"
    else:
        health_status = "HEALTHY"

    section1 = {
        "section": "1. Bench Health Overview",
        "duration_mins": 10,
        "points": [
            f"Total bench: {total_bench} ({current_bench} current, {future_bench} future)",
            f"At-risk employees: {at_risk} (bench >60 days, no proposed status)",
            f"Health status: {health_status}",
        ],
    }

    # ---- threshold breaches ----
    breach_points: list[str] = []
    if alerts is not None and not alerts.empty:
        for _, row in alerts[alerts["is_breached"] == True].iterrows():
            sign = "+" if int(row["breach_amount"]) > 0 else ""
            breach_points.append(
                f"{row['org_slice']}: bench={int(row['current_bench_count'])} vs "
                f"threshold={int(row['bench_threshold'])} "
                f"({sign}{int(row['breach_amount'])}, {row['alert_severity']}) — RM review needed"
            )
    if not breach_points:
        breach_points = ["No active threshold breaches"]

    section2 = {
        "section": "2. Threshold Breaches — Action Required",
        "duration_mins": 15,
        "points": breach_points,
    }

    # ---- hiring freeze ----
    freeze_points: list[str] = []
    if freeze is not None and not freeze.empty:
        for _, row in freeze[freeze["freeze_recommended"] == True].iterrows():
            surplus = int(row["supply_surplus"])
            sign = "+" if surplus > 0 else ""
            timeline = "IMMEDIATE" if surplus > 5 else "30-day"
            freeze_points.append(
                f"{row['skill']}: supply={int(row['total_supply'])}, "
                f"demand={int(row['open_demand_count'])}, surplus={sign}{surplus} — {timeline} freeze"
            )
    if not freeze_points:
        freeze_points = ["No hiring freeze recommendations"]

    section3 = {
        "section": "3. Hiring Freeze Recommendations",
        "duration_mins": 10,
        "points": freeze_points,
    }

    # ---- release pipeline ----
    confirmed_30d = 0
    projected_90d = 0
    if forecast is not None and not forecast.empty:
        fc_30 = forecast[forecast["days_from_today"] <= 30]
        confirmed_30d = int(fc_30["confirmed_count"].sum()) if not fc_30.empty else 0
        fc_90 = forecast[forecast["days_from_today"] <= 90]
        projected_90d = int(fc_90["projected_count"].sum()) if not fc_90.empty else 0

    section4 = {
        "section": "4. Release Pipeline — Next 30 Days",
        "duration_mins": 5,
        "points": [
            f"{confirmed_30d} confirmed release{'s' if confirmed_30d != 1 else ''} in next 30 days",
            f"{projected_90d} release{'s' if projected_90d != 1 else ''} projected in next 90 days",
        ],
    }

    # ---- top 5 immediate actions ----
    immediate = [a for a in actions if a.get("priority") == "IMMEDIATE"]
    action_points = [a["action"] for a in immediate[:5]]
    if not action_points:
        action_points = ["No immediate actions pending"]

    section5 = {
        "section": "5. Immediate Actions Pending",
        "duration_mins": 15,
        "points": action_points,
    }

    section6 = {
        "section": "6. AOB (Any Other Business)",
        "duration_mins": 5,
        "points": ["Open floor"],
    }

    sections = [section1, section2, section3, section4, section5, section6]
    total_duration = sum(s["duration_mins"] for s in sections)

    logger.info(
        "generate_meeting_agenda: next_monday=%s, health=%s, breaches=%d, freezes=%d",
        meeting_date, health_status, breach_count, len(freeze_points),
    )

    return _to_json_safe({
        "meeting_date": meeting_date,
        "meeting_date_human": meeting_date_human,
        "meeting_title": f"Weekly Bench Review — {meeting_date}",
        "prepared_by": "Bench Agent (Advisory)",
        "sections": sections,
        "total_duration_mins": total_duration,
        "disclaimer": "Generated by Bench Agent — advisory only",
    })
