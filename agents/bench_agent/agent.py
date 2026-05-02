"""
Bench Agent — LangGraph StateGraph (Phase 5e)

Node order:
  load_data → preprocess → apply_exclusions → engineer_features
  → run_r1 → run_r2 → run_r3 → run_r4_rules → run_r4_llm → persist_outputs

TC2 COMPLIANCE: run_r4_llm sends only aggregated skill-level stats to the LLM.
No Emplid, no employee names, no individual rows leave this process.

Environment variables (all loaded from .env):
  LLM_MODEL       — OpenAI model name (default: gpt-4o-mini)
  OPENAI_API_KEY  — API key (required for live LLM calls)
  OPENAI_API_BASE — API base URL (default: https://api.openai.com/v1)
  MOCK_LLM        — Set to "true" to skip the real LLM call (default: false)
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

# ---------------------------------------------------------------------------
# Path resolution — ensure project root is importable regardless of CWD
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.bench_agent.prompts import HIRING_FREEZE_PROMPT
from output.excel_writer import write_output
from pipeline.action_advisor import compute_actions
from pipeline.digest_generator import generate_daily_digest, generate_meeting_agenda
from pipeline.persistence import save_alerts, save_forecast, save_snapshot
from pipeline.exclusion_filters import apply_exclusion_filters
from pipeline.feature_engineering import engineer_features
from pipeline.ingestion import load_all
from pipeline.preprocessing import preprocess_ris
from pipeline.r1_bench_snapshot import compute_bench_snapshot
from pipeline.r2_forecast import compute_bucket_summary, compute_daily_forecast
from pipeline.r3_threshold import compute_threshold_alerts
from pipeline.r4_hiring_freeze import compute_hiring_freeze

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config — all overridable via .env; model is the only thing that changes
# between evaluator runs
# ---------------------------------------------------------------------------
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
MOCK_LLM: bool = os.getenv("MOCK_LLM", "false").lower() == "true"
_OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
_OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------
class AgentState(TypedDict, total=False):
    raw_data: dict
    ris_df: Any
    deployable_bench_df: Any
    excluded_df: Any
    enriched_bench_df: Any
    r1_snapshot: dict
    r2_daily_forecast_df: Any
    r2_bucket_summary_df: Any
    r3_alerts_df: Any
    r4_freeze_df: Any
    action_recommendations: list
    digest: dict
    agenda: dict


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _format_supply_demand_summary(freeze_rows: pd.DataFrame) -> str:
    """Format freeze-recommended rows as a TC2-compliant summary string.

    Only skill-level aggregates are included — no Emplid, no names.
    """
    lines = []
    for _, row in freeze_rows.iterrows():
        avg = row["avg_skill_rating"]
        avg_str = f"{avg:.2f}" if pd.notna(avg) else "N/A"
        lines.append(
            f"Skill: {row['skill']} | Supply: {int(row['total_supply'])} | "
            f"Demand: {int(row['open_demand_count'])} | Surplus: {int(row['supply_surplus'])} | "
            f"Avg Rating: {avg_str}"
        )
    return "\n".join(lines)


def _mock_llm_response(freeze_rows: pd.DataFrame) -> list[dict]:
    """Return a structurally valid JSON response without calling the real LLM."""
    results = []
    for _, row in freeze_rows.iterrows():
        surplus = int(row["supply_surplus"])
        if surplus > 5:
            timeline = "immediate"
        elif surplus >= 3:
            timeline = "30-day"
        else:
            timeline = "60-day"
        results.append({
            "skill": row["skill"],
            "recommendation": f"Pause all new hiring for '{row['skill']}' skill cluster.",
            "rationale": (
                f"Bench supply ({int(row['total_supply'])}) exceeds open demand "
                f"({int(row['open_demand_count'])}) by {surplus}. "
                f"Avg skill rating: {row['avg_skill_rating'] if pd.notna(row['avg_skill_rating']) else 'N/A'}."
            ),
            "review_timeline": timeline,
        })
    return results


def _call_llm(summary: str, freeze_rows: pd.DataFrame) -> list[dict]:
    """Call the configured LLM via ChatOpenAI or return a mock response.

    TC2: only the aggregated `summary` string is sent — no PII.
    Falls back silently; callers must handle exceptions.

    OpenRouter requires HTTP-Referer and X-Title headers.
    Model string must match OpenRouter format exactly (e.g. "openai/gpt-5-mini").
    """
    if MOCK_LLM:
        logger.warning("MOCK_LLM=true — returning mock LLM response (no API call made)")
        return _mock_llm_response(freeze_rows)

    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI

    prompt = HIRING_FREEZE_PROMPT.format(supply_demand_summary=summary)
    logger.info("run_r4_llm: calling model=%s via %s", LLM_MODEL, _OPENAI_API_BASE)

    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=_OPENAI_API_KEY,
        openai_api_base=_OPENAI_API_BASE,
        temperature=0,
        max_tokens=2048,
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "BenchAgent",
        },
        request_timeout=30,
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content

    # Strip markdown fences if the model wraps the JSON
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("```", 2)[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.rsplit("```", 1)[0].strip()

    return json.loads(stripped)


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def load_data(state: AgentState) -> dict:
    logger.info("=== Node: load_data ===")
    raw = load_all()
    logger.info("load_data: loaded %d source datasets", len(raw))
    return {"raw_data": raw}


def preprocess(state: AgentState) -> dict:
    logger.info("=== Node: preprocess ===")
    ris_df = preprocess_ris(state["raw_data"]["ris"])
    return {"ris_df": ris_df}


def apply_exclusions(state: AgentState) -> dict:
    logger.info("=== Node: apply_exclusions ===")
    deployable, excluded = apply_exclusion_filters(state["ris_df"])
    logger.info(
        "apply_exclusions: deployable=%d  excluded=%d",
        len(deployable), len(excluded),
    )
    return {"deployable_bench_df": deployable, "excluded_df": excluded}


def engineer_features_node(state: AgentState) -> dict:
    logger.info("=== Node: engineer_features ===")
    enriched = engineer_features(
        state["deployable_bench_df"],
        state["raw_data"]["threshold"],
    )
    return {"enriched_bench_df": enriched}


def run_r1(state: AgentState) -> dict:
    logger.info("=== Node: run_r1 ===")
    snapshot = compute_bench_snapshot(state["enriched_bench_df"])
    logger.info("run_r1: headcount=%d", snapshot["total_headcount"])
    return {"r1_snapshot": snapshot}


def run_r2(state: AgentState) -> dict:
    logger.info("=== Node: run_r2 ===")
    daily = compute_daily_forecast(state["enriched_bench_df"])
    bucket = compute_bucket_summary(daily)
    return {"r2_daily_forecast_df": daily, "r2_bucket_summary_df": bucket}


def run_r3(state: AgentState) -> dict:
    logger.info("=== Node: run_r3 ===")
    alerts = compute_threshold_alerts(
        state["enriched_bench_df"],
        state["raw_data"]["threshold"],
    )
    logger.info("run_r3: %d org slices evaluated", len(alerts))
    return {"r3_alerts_df": alerts}


def run_r4_rules(state: AgentState) -> dict:
    logger.info("=== Node: run_r4_rules ===")
    freeze_df = compute_hiring_freeze(
        state["enriched_bench_df"],
        state["raw_data"]["so_ageing"],
        state["raw_data"]["skill"],
    )
    freeze_count = int(freeze_df["freeze_recommended"].sum())
    logger.info("run_r4_rules: %d skills analysed, %d freeze recommended", len(freeze_df), freeze_count)
    return {"r4_freeze_df": freeze_df}


def run_r4_llm(state: AgentState) -> dict:
    """Add LLM-generated narrative to the hiring freeze DataFrame.

    TC2: only aggregated skill-level stats are sent to the LLM.
    Falls back to rule-based advisory_note on any error.
    """
    logger.info("=== Node: run_r4_llm (model=%s, mock=%s) ===", LLM_MODEL, MOCK_LLM)
    freeze_df = state["r4_freeze_df"].copy()

    # Only freeze-recommended rows are sent to the LLM
    freeze_rows = freeze_df[freeze_df["freeze_recommended"] == True].copy()

    if freeze_rows.empty:
        logger.info("run_r4_llm: no freeze-recommended skills — skipping LLM, using advisory_note")
        freeze_df["llm_narrative"] = freeze_df["advisory_note"]
        return {"r4_freeze_df": freeze_df}

    # Build TC2-compliant summary — no PII
    summary = _format_supply_demand_summary(freeze_rows)

    try:
        llm_results = _call_llm(summary, freeze_rows)

        # Map skill → formatted narrative string
        narrative_map: dict[str, str] = {}
        for item in llm_results:
            skill = item.get("skill", "")
            narrative = " ".join(filter(None, [
                item.get("recommendation", ""),
                item.get("rationale", ""),
                f"Review: {item.get('review_timeline', '')}",
            ])).strip()
            narrative_map[skill] = narrative

        logger.info("run_r4_llm: received narratives for %d skills", len(narrative_map))

    except json.JSONDecodeError as exc:
        logger.warning("run_r4_llm: JSON parse failed (%s) — falling back to rule-based advisory", exc)
        narrative_map = {}
    except Exception as exc:
        logger.warning("run_r4_llm: LLM call failed (%s) — falling back to rule-based advisory", exc)
        narrative_map = {}

    # Add llm_narrative — use LLM output where available, advisory_note as fallback
    freeze_df["llm_narrative"] = freeze_df.apply(
        lambda row: narrative_map.get(row["skill"], row["advisory_note"]),
        axis=1,
    )

    return {"r4_freeze_df": freeze_df}


def run_action_advisor(state: AgentState) -> dict:
    """Generate agentic action recommendations from all rule outputs."""
    logger.info("=== Node: run_action_advisor ===")
    actions = compute_actions(
        snapshot=state["r1_snapshot"],
        forecast_df=state["r2_daily_forecast_df"],
        alerts_df=state["r3_alerts_df"],
        freeze_df=state["r4_freeze_df"],
    )
    logger.info("run_action_advisor: %d action items generated", len(actions))
    return {"action_recommendations": actions}


def generate_digest_node(state: AgentState) -> dict:
    """Generate the daily intelligence digest after all rule outputs are ready."""
    logger.info("=== Node: generate_digest ===")
    digest = generate_daily_digest(
        snapshot=state["r1_snapshot"],
        forecast=state["r2_daily_forecast_df"],
        alerts=state["r3_alerts_df"],
        freeze=state["r4_freeze_df"],
        actions=state["action_recommendations"],
    )
    logger.info(
        "generate_digest: health=%s, breaches=%d, freezes=%d",
        digest["bench_health"]["status"],
        len(digest["threshold_breaches"]),
        len(digest["freeze_recommendations"]),
    )
    return {"digest": digest}


def generate_agenda_node(state: AgentState) -> dict:
    """Generate the weekly meeting agenda after all rule outputs are ready."""
    logger.info("=== Node: generate_agenda ===")
    agenda = generate_meeting_agenda(
        snapshot=state["r1_snapshot"],
        forecast=state["r2_daily_forecast_df"],
        alerts=state["r3_alerts_df"],
        freeze=state["r4_freeze_df"],
        actions=state["action_recommendations"],
    )
    logger.info("generate_agenda: next_monday=%s", agenda["meeting_date"])
    return {"agenda": agenda}


def persist_outputs(state: AgentState) -> dict:
    """Write Excel output and persist to PostgreSQL (Phase 6)."""
    logger.info("=== Node: persist_outputs ===")
    out_path = write_output(
        dashboard_df=state["enriched_bench_df"],
        forecast_df=state["r2_daily_forecast_df"],
        alerts_df=state["r3_alerts_df"],
        freeze_df=state["r4_freeze_df"],
    )
    logger.info("persist_outputs: Excel written → %s", out_path)

    save_snapshot(state["r1_snapshot"])
    save_forecast(state["r2_daily_forecast_df"])
    save_alerts(state["r3_alerts_df"], state["r4_freeze_df"])
    return {}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct and compile the LangGraph StateGraph."""
    graph = StateGraph(AgentState)

    graph.add_node("load_data",          load_data)
    graph.add_node("preprocess",         preprocess)
    graph.add_node("apply_exclusions",   apply_exclusions)
    graph.add_node("engineer_features",  engineer_features_node)
    graph.add_node("run_r1",             run_r1)
    graph.add_node("run_r2",             run_r2)
    graph.add_node("run_r3",             run_r3)
    graph.add_node("run_r4_rules",       run_r4_rules)
    graph.add_node("run_r4_llm",         run_r4_llm)
    graph.add_node("run_action_advisor", run_action_advisor)
    graph.add_node("generate_digest",    generate_digest_node)
    graph.add_node("generate_agenda",    generate_agenda_node)
    graph.add_node("persist_outputs",    persist_outputs)

    graph.set_entry_point("load_data")

    graph.add_edge("load_data",          "preprocess")
    graph.add_edge("preprocess",         "apply_exclusions")
    graph.add_edge("apply_exclusions",   "engineer_features")
    graph.add_edge("engineer_features",  "run_r1")
    graph.add_edge("run_r1",             "run_r2")
    graph.add_edge("run_r2",             "run_r3")
    graph.add_edge("run_r3",             "run_r4_rules")
    graph.add_edge("run_r4_rules",       "run_r4_llm")
    graph.add_edge("run_r4_llm",         "run_action_advisor")
    graph.add_edge("run_action_advisor", "generate_digest")
    graph.add_edge("generate_digest",    "generate_agenda")
    graph.add_edge("generate_agenda",    "persist_outputs")
    graph.add_edge("persist_outputs",    END)

    compiled = graph.compile()
    logger.info("LangGraph StateGraph compiled successfully — 13 nodes connected")
    return compiled


# Module-level compiled graph (importable by FastAPI layer in Phase 8)
compiled_graph = build_graph()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_pipeline() -> AgentState:
    """Execute the full pipeline and return the final state."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting Bench Agent pipeline (LLM_MODEL=%s, MOCK_LLM=%s)", LLM_MODEL, MOCK_LLM)
    final_state: AgentState = compiled_graph.invoke({})
    logger.info("Pipeline complete.")
    return final_state


if __name__ == "__main__":
    run_pipeline()
