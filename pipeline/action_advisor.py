"""
pipeline/action_advisor.py — Agentic Action Layer

Takes R1/R2/R3/R4 outputs and generates structured action recommendations.
R4 freeze actions include an LLM-generated draft HR email.

TC2 COMPLIANCE (same constraint as Phase 5e):
  - All action/rationale text uses only aggregate counts and org-slice labels.
    No Emplid or employee name appears anywhere in this module.
  - The LLM for R4 emails receives exactly five fields via _Tc2EmailPayload:
      skill name, total_supply, open_demand_count, supply_surplus, avg_skill_rating.
    Nothing else reaches the LLM call.

Each action dict has keys:
    rule       — R1 / R2 / R3 / R4
    priority   — IMMEDIATE / 7-DAY / 30-DAY
    owner      — RM / HR / Leadership
    action     — plain-English next step (counts + org slices only)
    rationale  — why this action is needed (counts + org slices only)
    hr_email   — {subject, body} dict (R4 only)
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MOCK_LLM: bool   = os.getenv("MOCK_LLM", "false").lower() == "true"
LLM_MODEL: str   = os.getenv("LLM_MODEL", "gpt-4o-mini")
_API_KEY: str    = os.getenv("OPENAI_API_KEY", "")
_API_BASE: str   = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

_HR_EMAIL_PROMPT = """\
You are a resource management advisor drafting a professional HR communication.
Based on the following aggregated skill supply and demand data, write a hiring freeze recommendation email.

Data (aggregated statistics only — no employee names or IDs):
{skill_summary}

Write a professional email with:
- Subject line
- Opening paragraph explaining the situation
- Body paragraph with the specific recommendation and rationale
- Closing paragraph with next steps and a review timeline

Output as JSON only: {{"subject": "...", "body": "..."}}
No preamble. JSON only.\
"""


# ---------------------------------------------------------------------------
# TC2 payload — exactly the five fields permitted to reach the LLM.
# The dataclass makes the boundary explicit and prevents accidental additions.
# ---------------------------------------------------------------------------

@dataclass
class _Tc2EmailPayload:
    """Aggregated skill-level statistics — the only data sent to the LLM.

    TC2: no Emplid, no employee name, no project name, no individual row data.
    Fields: skill name, total_supply, open_demand_count, supply_surplus, avg_skill_rating.
    """
    skill: str
    total_supply: int
    open_demand_count: int
    supply_surplus: int
    avg_skill_rating: float | None


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _mock_hr_email(p: _Tc2EmailPayload) -> dict:
    rating_str = f"{p.avg_skill_rating:.1f}" if p.avg_skill_rating is not None and pd.notna(p.avg_skill_rating) else "N/A"
    timeline = "immediately" if p.supply_surplus > 5 else "within the next 30 days"
    return {
        "subject": f"Hiring Freeze Recommendation — {p.skill} Skill Cluster",
        "body": (
            f"Dear HR Team,\n\n"
            f"Following a review of our current bench supply and open demand pipeline, we recommend "
            f"implementing a hiring freeze for the {p.skill} skill cluster {timeline}.\n\n"
            f"Current bench supply stands at {p.total_supply} resources against {p.open_demand_count} "
            f"open demand positions, resulting in a surplus of {p.supply_surplus}. "
            f"The average skill rating across the bench pool is {rating_str}. "
            f"Continuing to recruit for this cluster would further widen the surplus "
            f"and increase bench carrying costs with no clear deployment path.\n\n"
            f"We recommend pausing all active {p.skill} requisitions for a 30-day review period. "
            f"During this window, the RM team will work to map existing bench resources to open demands "
            f"before any new recruitment is approved. Please confirm receipt and update all active "
            f"requisition statuses to 'On Hold' accordingly.\n\n"
            f"Regards,\nBench Agent (Advisory System — for review before sending)"
        ),
    }


def _call_hr_email_llm(p: _Tc2EmailPayload) -> dict:
    """Generate a draft HR email. Only the five TC2-approved fields in `p` are sent.

    TC2: p contains skill name + aggregate counts only. No employee-level data.
    """
    if MOCK_LLM:
        logger.warning("MOCK_LLM=true — returning mock HR email for skill '%s'", p.skill)
        return _mock_hr_email(p)

    try:
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI

        # Build the five-field summary — this is the complete LLM input
        rating_str = f"{p.avg_skill_rating:.2f}" if p.avg_skill_rating is not None and pd.notna(p.avg_skill_rating) else "N/A"
        tc2_summary = (
            f"Skill: {p.skill} | "
            f"Total Supply: {p.total_supply} | "
            f"Open Demand: {p.open_demand_count} | "
            f"Supply Surplus: {p.supply_surplus} | "
            f"Avg Skill Rating: {rating_str}"
        )
        logger.info(
            "action_advisor LLM input (TC2 verified — aggregates only): %s", tc2_summary
        )

        prompt = _HR_EMAIL_PROMPT.format(skill_summary=tc2_summary)

        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=_API_KEY,
            openai_api_base=_API_BASE,
            temperature=0.3,
            max_tokens=800,
            default_headers={"HTTP-Referer": "http://localhost", "X-Title": "BenchAgent"},
            request_timeout=30,
        )
        raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        return json.loads(raw)

    except Exception as exc:
        logger.warning("HR email LLM call failed (%s) — using mock", exc)
        return _mock_hr_email(p)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_actions(
    snapshot: dict,
    forecast_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    freeze_df: pd.DataFrame,
) -> list[dict]:
    """Generate structured action recommendations from all rule outputs.

    TC2 COMPLIANCE:
      - snapshot  : aggregated KPIs only (counts, distributions) — no individual rows
      - forecast_df: date-level aggregates — no individual rows
      - alerts_df : org-slice-level aggregates — no individual rows
      - freeze_df : skill-level aggregates — no individual rows
      All action/rationale strings reference only counts and org-slice labels.
      LLM calls receive only a _Tc2EmailPayload (5 fields, no PII).
    """
    actions: list[dict] = []

    total_hc      = snapshot.get("total_headcount", 0)
    status_counts = snapshot.get("status_counts", {})
    available_cnt = status_counts.get("available", 0)
    nafd_cnt      = status_counts.get("nafd", 0)
    aging_dist    = snapshot.get("aging_distribution", {})
    # aging_dist is a pd.Series or dict coming from r1_bench_snapshot
    if hasattr(aging_dist, "to_dict"):
        aging_dist = aging_dist.to_dict()
    critical_aging = aging_dist.get(">91 days", 0)

    # ── R1 ────────────────────────────────────────────────────────────────────
    if available_cnt > 0:
        if critical_aging > 0:
            actions.append({
                "rule": "R1",
                "priority": "IMMEDIATE",
                "owner": "RM",
                "action": (
                    f"Schedule placement review for {available_cnt} 'Available for mapping' employees. "
                    f"{critical_aging} have exceeded 91 days on bench — escalate to leadership if no "
                    "proposed status within 7 days."
                ),
                "rationale": (
                    f"{available_cnt} deployable employees have no proposed opportunity. "
                    f"{critical_aging} have crossed the 91-day aging threshold, indicating stalled placement. "
                    "Every additional bench day increases carrying cost and attrition risk."
                ),
            })
        else:
            actions.append({
                "rule": "R1",
                "priority": "IMMEDIATE",
                "owner": "RM",
                "action": (
                    f"Initiate placement discussions for {available_cnt} employees "
                    "with 'Available for mapping' status."
                ),
                "rationale": (
                    f"{available_cnt} deployable employees currently have no proposed opportunities. "
                    "Early engagement shortens bench duration."
                ),
            })

    if total_hc > 0 and nafd_cnt / total_hc > 0.20:
        actions.append({
            "rule": "R1",
            "priority": "7-DAY",
            "owner": "Leadership",
            "action": (
                f"Convene bench review meeting — {nafd_cnt} of {total_hc} bench employees "
                f"({round(nafd_cnt / total_hc * 100)}%) carry NAFD status."
            ),
            "rationale": (
                "NAFD count exceeds 20% of total deployable bench. Leadership review needed to "
                "assess conversion feasibility, skill transition, or exit decisions to right-size the bench."
            ),
        })

    # ── R2 ────────────────────────────────────────────────────────────────────
    if not forecast_df.empty:
        d30_row = forecast_df[forecast_df["days_from_today"] == 30]
        d30_bench = int(d30_row["total_forecast_bench"].iloc[0]) if not d30_row.empty else 0

        if d30_bench > 0 and total_hc > 0 and (d30_bench / total_hc) > 0.10:
            actions.append({
                "rule": "R2",
                "priority": "IMMEDIATE",
                "owner": "RM",
                "action": (
                    f"Begin pre-mapping for {d30_bench} resources forecasted to join bench within 30 days. "
                    "Start demand matching now to minimise time-on-bench at landing."
                ),
                "rationale": (
                    f"30-day forecast shows {d30_bench} additional resources entering bench — "
                    f"a {round(d30_bench / total_hc * 100)}% increase over current headcount. "
                    "Proactive mapping prevents a spike in undeployed bench."
                ),
            })

        mixed_days   = int((forecast_df["forecast_confidence_band"] == "MIXED").sum())
        high_days    = int((forecast_df["forecast_confidence_band"] == "HIGH").sum())
        if mixed_days > high_days:
            actions.append({
                "rule": "R2",
                "priority": "7-DAY",
                "owner": "RM",
                "action": (
                    "Confirm release dates with project managers for all projected bench additions. "
                    "Most forecast releases are low-confidence estimates."
                ),
                "rationale": (
                    f"{mixed_days} of {len(forecast_df)} forecast days show MIXED confidence "
                    "(projected releases exceed confirmed). Inaccurate forecasts lead to under-preparation "
                    "and last-minute bench spikes."
                ),
            })

    # ── R3 ────────────────────────────────────────────────────────────────────
    if not alerts_df.empty:
        breached = alerts_df[alerts_df["is_breached"] == True]
        for _, row in breached.iterrows():
            org      = str(row["org_slice"])
            breach   = int(row["breach_amount"])
            current  = int(row["current_bench_count"])
            threshold = int(row["bench_threshold"])

            actions.append({
                "rule": "R3",
                "priority": "IMMEDIATE",
                "owner": "HR",
                "org_slice": org,
                "action": f"Pause all active hiring requisitions for {org} immediately.",
                "rationale": (
                    f"{org} bench ({current}) exceeds configured threshold ({threshold}) by {breach}. "
                    "Continuing to hire into a surplus org slice deepens bench cost with no deployment path."
                ),
            })
            actions.append({
                "rule": "R3",
                "priority": "7-DAY",
                "owner": "RM",
                "org_slice": org,
                "action": (
                    f"Review all {current} {org} bench employees for redeployment — "
                    "identify skill adjacencies and active projects with capacity gaps."
                ),
                "rationale": (
                    f"Threshold breach of {breach} in {org} means more bench than planned capacity. "
                    "Redeployment within 7 days prevents escalation to a higher severity alert."
                ),
            })
            actions.append({
                "rule": "R3",
                "priority": "30-DAY",
                "owner": "Leadership",
                "org_slice": org,
                "action": (
                    f"If {org} bench remains undeployed at 30-day mark, initiate skill transition / "
                    "reskilling plan to address structural demand-supply mismatch."
                ),
                "rationale": (
                    f"Persistent threshold breach in {org} beyond 30 days signals a structural mismatch. "
                    "Reskilling or reallocation planning is required to prevent long-term bench cost escalation."
                ),
            })

    # ── R4 ────────────────────────────────────────────────────────────────────
    # TC2: extract only the five permitted fields into _Tc2EmailPayload before
    # any LLM call. The dataclass prevents accidental inclusion of other columns.
    if not freeze_df.empty:
        freeze_rows = freeze_df[freeze_df["freeze_recommended"] == True]
        for _, row in freeze_rows.iterrows():
            payload = _Tc2EmailPayload(
                skill             = str(row["skill"]),
                total_supply      = int(row["total_supply"]),
                open_demand_count = int(row["open_demand_count"]),
                supply_surplus    = int(row["supply_surplus"]),
                avg_skill_rating  = row.get("avg_skill_rating"),
            )

            hr_email = _call_hr_email_llm(payload)

            actions.append({
                "rule": "R4",
                "priority": "IMMEDIATE" if payload.supply_surplus > 5 else "7-DAY",
                "owner": "HR",
                "skill": payload.skill,
                "action": (
                    f"Implement hiring freeze for '{payload.skill}' skill cluster. "
                    "Notify all active recruiters and pause open requisitions."
                ),
                "rationale": (
                    f"Bench supply ({payload.total_supply}) exceeds open demand "
                    f"({payload.open_demand_count}) by {payload.supply_surplus} "
                    f"for '{payload.skill}'. Continued recruitment widens the surplus "
                    "and increases bench carrying cost."
                ),
                "hr_email": hr_email,
            })

    logger.info(
        "action_advisor: generated %d action items (R1:%d R2:%d R3:%d R4:%d)",
        len(actions),
        sum(1 for a in actions if a["rule"] == "R1"),
        sum(1 for a in actions if a["rule"] == "R2"),
        sum(1 for a in actions if a["rule"] == "R3"),
        sum(1 for a in actions if a["rule"] == "R4"),
    )
    return actions
