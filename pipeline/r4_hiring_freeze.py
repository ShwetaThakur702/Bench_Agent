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
