import logging

import pandas as pd

from pipeline.ingestion import ThresholdConfigMissingError

logger = logging.getLogger(__name__)


def _alert_severity(breach_amount: float) -> str:
    if breach_amount > 20:
        return "CRITICAL"
    if breach_amount > 10:
        return "HIGH"
    if breach_amount > 0:
        return "MEDIUM"
    return "OK"


def _recommended_action(org_slice: str, current: int, threshold: float, breach: float) -> str:
    if breach <= 0:
        return f"No action required. {org_slice} bench ({current}) is within threshold ({int(threshold)})."
    return (
        f"Review bench pipeline for {org_slice}. "
        f"Current bench ({current}) exceeds threshold ({int(threshold)}) "
        f"by {int(breach)}. Consider hiring freeze advisory."
    )


def compute_threshold_alerts(
    deployable_bench_df: pd.DataFrame,
    threshold_config_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute R3 threshold breach alerts for each matched org slice.

    UNMAPPED rows are excluded from comparison.
    All matched org slices appear in output — breached with severity,
    non-breached with alert_severity = 'OK'.

    Parameters
    ----------
    deployable_bench_df  : enriched deployable bench from engineer_features()
    threshold_config_df  : threshold config from load_threshold_config()

    Returns
    -------
    pd.DataFrame — one row per matched org slice.

    Raises
    ------
    ThresholdConfigMissingError if threshold_config_df is None or empty.
    """
    if threshold_config_df is None or threshold_config_df.empty:
        msg = "Threshold config is missing or empty. R3 cannot run."
        logger.error(msg)
        print(f"ERROR: {msg}", flush=True)
        raise ThresholdConfigMissingError(msg)

    run_date = str(pd.Timestamp.today().date())

    # Current bench count per org slice — UNMAPPED excluded
    mapped = deployable_bench_df[deployable_bench_df["org_slice_key"] != "UNMAPPED"]
    unmapped_count = (deployable_bench_df["org_slice_key"] == "UNMAPPED").sum()
    logger.info("R3: %d UNMAPPED rows excluded from threshold comparison", unmapped_count)

    bench_by_org = (
        mapped.groupby("org_slice_key")
        .size()
        .reset_index(name="current_bench_count")
        .rename(columns={"org_slice_key": "org_slice"})
    )

    # Inner join — only compare slices present in both bench data and threshold config
    merged = bench_by_org.merge(threshold_config_df, on="org_slice", how="inner")
    logger.info(
        "R3: %d org slices in bench data, %d in threshold config, %d matched",
        len(bench_by_org), len(threshold_config_df), len(merged),
    )

    merged["breach_amount"]      = merged["current_bench_count"] - merged["bench_threshold"]
    merged["is_breached"]        = merged["breach_amount"] > 0
    merged["alert_severity"]     = merged["breach_amount"].apply(_alert_severity)
    merged["recommended_action"] = merged.apply(
        lambda r: _recommended_action(
            r["org_slice"], int(r["current_bench_count"]),
            r["bench_threshold"], r["breach_amount"]
        ),
        axis=1,
    )
    merged["run_date"] = run_date

    breached = merged[merged["is_breached"]]
    logger.info(
        "R3: %d org slices compared — %d breached, %d within threshold",
        len(merged), len(breached), len(merged) - len(breached),
    )
    if not breached.empty:
        for _, row in breached.iterrows():
            logger.warning(
                "ALERT [%s] %s: bench=%d threshold=%g breach=%+.0f",
                row["alert_severity"], row["org_slice"],
                row["current_bench_count"], row["bench_threshold"], row["breach_amount"],
            )

    SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "OK": 3}
    merged["_sev_rank"] = merged["alert_severity"].map(SEV_ORDER)
    merged = merged.sort_values(["_sev_rank", "org_slice"]).drop(columns=["_sev_rank"])

    cols = [
        "org_slice", "current_bench_count", "bench_threshold",
        "breach_amount", "is_breached", "alert_severity",
        "recommended_action", "run_date",
    ]
    return merged[cols].reset_index(drop=True)
