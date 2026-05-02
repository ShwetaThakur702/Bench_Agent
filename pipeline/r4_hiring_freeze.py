import logging

import pandas as pd

logger = logging.getLogger(__name__)


def compute_hiring_freeze(
    deployable_bench_df: pd.DataFrame,
    so_ageing_df: pd.DataFrame,
    skill_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute R4 rule-based hiring freeze advisory.

    TC2 COMPLIANCE: Returns only aggregated skill-level statistics.
    No Emplid, employee names, or individual rows are included in the output.
    The LangGraph layer (Phase 5e) receives only this aggregated DataFrame.

    Parameters
    ----------
    deployable_bench_df : enriched deployable bench from engineer_features()
    so_ageing_df        : SO Ageing filtered to Active + Open/Recruit (from Phase 1)
    skill_df            : Skill_Data_Synthetic, unfiltered

    Returns
    -------
    pd.DataFrame — one row per skill with supply/demand/freeze fields.
    """
    run_date = pd.Timestamp.today().date().isoformat()

    # ------------------------------------------------------------------
    # Step 1 — Supply side
    # ------------------------------------------------------------------
    bench_supply = (
        deployable_bench_df.groupby("Skiil")
        .size()
        .reset_index(name="bench_count")
        .rename(columns={"Skiil": "skill"})
    )

    near_term_mask = (
        deployable_bench_df["Releases in Next 30 days and beyond"] == "Release in 30 days"
    )
    near_term = (
        deployable_bench_df[near_term_mask]
        .groupby("Skiil")
        .size()
        .reset_index(name="near_term_releases")
        .rename(columns={"Skiil": "skill"})
    )

    supply = bench_supply.merge(near_term, on="skill", how="left")
    supply["near_term_releases"] = supply["near_term_releases"].fillna(0).astype(int)
    supply["total_supply"]       = supply["bench_count"] + supply["near_term_releases"]

    logger.info("R4 supply: %d skills across %d bench employees", len(supply), len(deployable_bench_df))

    # ------------------------------------------------------------------
    # Step 2 — Demand side (SO Ageing already filtered in Phase 1)
    # ------------------------------------------------------------------
    demand = (
        so_ageing_df.groupby("Primary Skill Description")
        .size()
        .reset_index(name="open_demand_count")
        .rename(columns={"Primary Skill Description": "skill"})
    )

    logger.info("R4 demand: %d skills across %d open SO lines", len(demand), len(so_ageing_df))

    # ------------------------------------------------------------------
    # Step 3 — Supply vs demand gap
    # ------------------------------------------------------------------
    gap = supply.merge(demand, on="skill", how="outer").fillna(0)
    gap["bench_count"]       = gap["bench_count"].astype(int)
    gap["near_term_releases"] = gap["near_term_releases"].astype(int)
    gap["total_supply"]       = gap["total_supply"].astype(int)
    gap["open_demand_count"]  = gap["open_demand_count"].astype(int)

    gap["supply_surplus"]      = gap["total_supply"] - gap["open_demand_count"]
    gap["freeze_recommended"]  = gap["supply_surplus"] > 0

    gap["advisory_note"] = gap.apply(
        lambda r: (
            f"Supply ({int(r['total_supply'])}) exceeds demand ({int(r['open_demand_count'])}) "
            f"by {int(r['supply_surplus'])} for skill '{r['skill']}'. Recommend hiring pause."
            if r["freeze_recommended"] else
            f"Demand ({int(r['open_demand_count'])}) exceeds supply ({int(r['total_supply'])}) "
            f"by {int(abs(r['supply_surplus']))} for skill '{r['skill']}'. No freeze needed."
        ),
        axis=1,
    )

    # ------------------------------------------------------------------
    # Step 4 — Skill enrichment: avg bench rating per skill
    # TC2: only aggregated avg_skill_rating is attached — no individual rows
    # ------------------------------------------------------------------
    skill_bench = skill_df[skill_df["Bench/Non Bench"] == "Bench"].copy()

    # Join to deployable bench to get the Skiil label for each skill record
    enriched_skills = skill_bench.merge(
        deployable_bench_df[["Emplid", "Skiil"]],
        left_on="Employee ID",
        right_on="Emplid",
        how="inner",
    )

    avg_rating = (
        enriched_skills.groupby("Skiil")["Overall Rating"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"Skiil": "skill", "Overall Rating": "avg_skill_rating"})
    )

    gap = gap.merge(avg_rating, on="skill", how="left")
    # avg_skill_rating NaN for skills with no matching skill_df records
    gap["avg_skill_rating"] = gap["avg_skill_rating"].round(2)

    gap["run_date"] = run_date

    freeze_count = gap["freeze_recommended"].sum()
    deficit_count = (~gap["freeze_recommended"]).sum()
    logger.info(
        "R4: %d skills analysed — %d freeze recommended, %d demand exceeds supply",
        len(gap), freeze_count, deficit_count,
    )

    # Final column order — TC2: no Emplid or employee-level fields
    cols = [
        "skill", "bench_count", "near_term_releases", "total_supply",
        "open_demand_count", "supply_surplus", "freeze_recommended",
        "avg_skill_rating", "advisory_note", "run_date",
    ]
    return gap[cols].sort_values("supply_surplus", ascending=False).reset_index(drop=True)


def compute_deployment_matches(
    deployable_bench_df: pd.DataFrame,
    so_ageing_df: pd.DataFrame,
) -> pd.DataFrame:
    """Match open SO demand lines against bench employee skills.

    TC2 COMPLIANT — data flow:
      1. Emplid + talentx_skills_list are exploded into a local intermediate (bench_exploded).
      2. Emplid is consumed by nunique() to count distinct matched employees per skill.
      3. bench_exploded is deleted immediately after the count.
      4. The merge and all downstream steps use only (skill_norm, matched_bench_count).
      5. The returned DataFrame is restricted to an explicit column allowlist —
         no Emplid, no employee names, no individual rows reach the caller.

    Parameters
    ----------
    deployable_bench_df : enriched bench (must have talentx_skills_list from engineer_features)
    so_ageing_df        : SO Ageing filtered to Active + Open/Recruit

    Returns
    -------
    pd.DataFrame — one row per demanded skill, sorted NONE → PARTIAL → FULL.
    Columns: skill, open_demand_count, matched_bench_count, match_rate_pct, coverage, gap, run_date
    """
    run_date = pd.Timestamp.today().date().isoformat()

    demand = (
        so_ageing_df.groupby("Primary Skill Description")
        .size()
        .reset_index(name="open_demand_count")
        .rename(columns={"Primary Skill Description": "skill"})
    )

    if demand.empty:
        logger.warning("compute_deployment_matches: no open demand found in SO Ageing")
        return pd.DataFrame(columns=[
            "skill", "open_demand_count", "matched_bench_count",
            "match_rate_pct", "coverage", "gap", "run_date",
        ])

    # TC2 boundary — Emplid is used only to deduplicate employees per skill.
    # It never leaves this block: matched_counts contains only (skill_norm, matched_bench_count).
    bench_exploded = (
        deployable_bench_df[["Emplid", "talentx_skills_list"]]
        .explode("talentx_skills_list")
        .dropna(subset=["talentx_skills_list"])
    )
    bench_exploded["skill_norm"] = bench_exploded["talentx_skills_list"].str.strip().str.lower()

    matched_counts = (
        bench_exploded.groupby("skill_norm")["Emplid"]
        .nunique()                          # count distinct employees — Emplid consumed here
        .reset_index(name="matched_bench_count")
    )
    del bench_exploded                      # employee-level data no longer needed

    demand["skill_norm"] = demand["skill"].str.strip().str.lower()
    result = demand.merge(matched_counts, on="skill_norm", how="left")
    result["matched_bench_count"] = result["matched_bench_count"].fillna(0).astype(int)

    result["match_rate_pct"] = (
        result["matched_bench_count"] / result["open_demand_count"] * 100
    ).round(1)
    result["gap"] = result["open_demand_count"] - result["matched_bench_count"]

    def _coverage(row) -> str:
        if row["matched_bench_count"] >= row["open_demand_count"]:
            return "FULL"
        if row["matched_bench_count"] > 0:
            return "PARTIAL"
        return "NONE"

    result["coverage"] = result.apply(_coverage, axis=1)
    result["run_date"] = run_date

    COVERAGE_RANK = {"NONE": 0, "PARTIAL": 1, "FULL": 2}
    result["_rank"] = result["coverage"].map(COVERAGE_RANK)
    result = result.sort_values(["_rank", "skill"]).drop(columns=["_rank", "skill_norm"])

    cols = ["skill", "open_demand_count", "matched_bench_count", "match_rate_pct", "coverage", "gap", "run_date"]
    logger.info(
        "compute_deployment_matches: %d skills — FULL=%d PARTIAL=%d NONE=%d",
        len(result),
        (result["coverage"] == "FULL").sum(),
        (result["coverage"] == "PARTIAL").sum(),
        (result["coverage"] == "NONE").sum(),
    )
    return result[cols].reset_index(drop=True)
