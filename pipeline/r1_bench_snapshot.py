import logging

import pandas as pd

logger = logging.getLogger(__name__)


def compute_bench_snapshot(df: pd.DataFrame) -> dict:
    """Compute R1 KPIs from the enriched deployable bench dataframe.

    Parameters
    ----------
    df : enriched deployable_bench_df from engineer_features()

    Returns
    -------
    dict with plain int / str / pd.Series values — safe for JSON serialisation
    after calling .to_dict() on Series values.
    """

    def _groupby_count(col: str) -> pd.Series:
        return df.groupby(col, dropna=False).size().rename("count")

    # ------------------------------------------------------------------
    # At-risk flag — aging > 60 days AND not Proposed/Shortlisted
    # ------------------------------------------------------------------
    at_risk_mask = (
        (df["bench_aging_derived"].fillna(0) > 60)
        & (~df["Final Status"].fillna("").str.contains("Proposed|Shortlisted", case=False, regex=True))
    )
    at_risk_count = int(at_risk_mask.sum())

    # ------------------------------------------------------------------
    # Status counts — buckets must cover all 80 rows
    # ------------------------------------------------------------------
    fs = df["Final Status"].fillna("")

    available = int((fs == "Available for mapping").sum())
    proposed  = int(fs.isin(["Proposed - Feedback Awaiting", "Proposed - Pending Interview"]).sum())
    allocated = int((fs == "Allocated to Billable Project").sum())
    nafd      = int(fs.str.startswith("NAFD").sum())
    other     = int(len(df) - available - proposed - allocated - nafd)

    status_counts = {
        "available": available,
        "proposed":  proposed,
        "allocated": allocated,
        "nafd":      nafd,
        "other":     other,           # catch-all so all rows are accounted for
    }

    snapshot = {
        "total_headcount":      int(len(df)),
        "at_risk_count":        at_risk_count,
        "by_location":          _groupby_count("Location Category"),
        "by_bu":                _groupby_count("Business Unit"),
        "by_grade":             _groupby_count("Grade").sort_values(ascending=False),
        "by_pool":              _groupby_count("Pool Description"),
        "by_country":           _groupby_count("Country"),
        "aging_distribution":   _groupby_count("bench_aging_bucket_derived"),
        "status_counts":        status_counts,
        "current_vs_future":    _groupby_count("Current or Future Bench"),
        "by_allocation_category": _groupby_count("Bench allocation category"),
        "by_skill":             _groupby_count("Skiil").sort_values(ascending=False),
        "run_date":             str(pd.Timestamp.today().date()),
    }

    logger.info(
        "R1 snapshot: headcount=%d  available=%d  proposed=%d  allocated=%d  nafd=%d  other=%d  at_risk=%d",
        snapshot["total_headcount"], available, proposed, allocated, nafd, other, at_risk_count,
    )
    return snapshot
