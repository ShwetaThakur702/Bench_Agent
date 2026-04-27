import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Map Confirm release values to confidence tiers
_CONFIDENCE_MAP = {
    "Confirmed Release":                       "HIGH",
    "Extension to be performed/Initiated":     "MEDIUM",
    "Unclear":                                 "LOW",
}


def _derive_aging_bucket(days) -> str:
    if pd.isna(days):
        return "Unknown"
    if days < 30:
        return "<30 days"
    if days <= 60:
        return "31-60 days"
    if days <= 90:
        return "61-90 days"
    return ">91 days"


def _build_skill_list(primary: str | None, core: str | None, skiil: str | None) -> list[str]:
    skills: list[str] = []
    if pd.notna(primary) and str(primary).strip():
        skills = [s.strip() for s in str(primary).split(",") if s.strip()]
    if pd.notna(core) and str(core).strip():
        core_val = str(core).strip()
        if core_val not in skills:
            skills.insert(0, core_val)
    if not skills and pd.notna(skiil) and str(skiil).strip():
        skills = [str(skiil).strip()]
    return skills


def engineer_features(df: pd.DataFrame, threshold_config_df: pd.DataFrame) -> pd.DataFrame:
    """Add 6 derived columns to the deployable bench dataframe.

    Parameters
    ----------
    df                  : deployable_bench_df from apply_exclusion_filters()
    threshold_config_df : threshold config with columns ['org_slice', 'bench_threshold']

    Returns
    -------
    Enriched dataframe with new columns added in-place (copy returned).
    """
    df = df.copy()
    today = pd.Timestamp.today().normalize()
    threshold_keys: set[str] = set(threshold_config_df["org_slice"].tolist())

    # ------------------------------------------------------------------
    # 1. effective_release_date
    #    Priority: Resource End Date → revised end date → Forecast Date
    # ------------------------------------------------------------------
    df["effective_release_date"] = (
        df["Resource End Date"]
        .fillna(df["revised end date"])
        .fillna(df["Forecast Date"])
    )
    nat_count = df["effective_release_date"].isna().sum()
    logger.info("effective_release_date: %d NaT values", nat_count)

    # ------------------------------------------------------------------
    # 2. forecast_confidence
    # ------------------------------------------------------------------
    df["forecast_confidence"] = (
        df["Confirm release"].map(_CONFIDENCE_MAP).fillna("LOW")
    )

    # ------------------------------------------------------------------
    # 3. is_future_release
    #    True when effective_release_date > today AND Future Allocation is null
    # ------------------------------------------------------------------
    df["is_future_release"] = (
        df["effective_release_date"].notna()
        & (df["effective_release_date"] > today)
        & df["Future Allocation"].isna()
    )

    # ------------------------------------------------------------------
    # 4. org_slice_key
    #    4-column fallback: Department ID → SL/IND_CLUSTER → Resource Based SSL → SSL/POD
    # ------------------------------------------------------------------
    LOOKUP_PRIORITY = ["Department ID", "SL/IND_CLUSTER", "Resource Based SSL", "SSL/POD"]

    def _resolve_org_slice(row) -> str:
        for col in LOOKUP_PRIORITY:
            val = row.get(col)
            if pd.notna(val) and str(val).strip().upper() in threshold_keys:
                return str(val).strip().upper()
        return "UNMAPPED"

    df["org_slice_key"] = df.apply(_resolve_org_slice, axis=1)

    unmapped = (df["org_slice_key"] == "UNMAPPED").sum()
    if unmapped:
        unmapped_depts = df.loc[df["org_slice_key"] == "UNMAPPED", "Department ID"].unique().tolist()
        logger.warning(
            "org_slice_key: %d rows UNMAPPED (no threshold match in Department ID or "
            "SL/IND_CLUSTER). Unmapped Department IDs: %s",
            unmapped, unmapped_depts,
        )

    # ------------------------------------------------------------------
    # 5. talentx_skills_list
    #    Core skill + Primary & Secondary skills, fallback to Skiil
    # ------------------------------------------------------------------
    df["talentx_skills_list"] = df.apply(
        lambda row: _build_skill_list(
            row.get("TalentX  Primary & Seconday Skills"),
            row.get("TalentX  - Core Skill"),
            row.get("Skiil"),
        ),
        axis=1,
    )

    # ------------------------------------------------------------------
    # 6. bench_aging_bucket_derived
    #    Derived from bench_aging_derived (days since Resource Start Date)
    # ------------------------------------------------------------------
    df["bench_aging_bucket_derived"] = df["bench_aging_derived"].apply(_derive_aging_bucket)

    logger.info(
        "feature_engineering complete: %d rows, %d columns", len(df), len(df.columns)
    )
    return df
