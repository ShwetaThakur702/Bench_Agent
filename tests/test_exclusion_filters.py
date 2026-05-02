"""
Phase 10 — test_exclusion_filters.py

Tests: apply_exclusion_filters() returns the correct split and that
no excluded condition survives into the deployable population.
"""


def test_returns_two_element_tuple(bench_tuple):
    assert isinstance(bench_tuple, tuple)
    assert len(bench_tuple) == 2


def test_deployable_plus_excluded_equals_total(deployable_df, excluded_df):
    # TC3: every input row must land in exactly one bucket
    assert len(deployable_df) + len(excluded_df) == 1000


def test_deployable_count(deployable_df):
    assert len(deployable_df) == 80


def test_excluded_count(excluded_df):
    assert len(excluded_df) == 920


def test_no_leave_type_in_deployable(deployable_df):
    # Condition 1: on leave → excluded
    assert deployable_df["Leave type"].isna().all()


def test_no_bz_resources_in_deployable(deployable_df):
    # Condition 2: BZ resource → excluded
    assert deployable_df["BZ resources"].isna().all()


def test_no_d_rated_in_deployable(deployable_df):
    # Condition 3: D-rated → excluded
    assert deployable_df["D rated"].isna().all()


def test_no_exit_in_deployable(deployable_df):
    # Condition 4: exit confirmed → excluded
    assert deployable_df["Exit"].isna().all()


def test_no_resignation_in_deployable(deployable_df):
    # Condition 5: resignation submitted → excluded
    assert deployable_df["Resignation Submitted Date"].isna().all()


def test_no_campus_without_fbd_in_deployable(deployable_df):
    # Condition 6: Campus lateral without FBD → excluded
    bad = (
        (deployable_df["Campus/Lateral"] == "Campus") &
        (deployable_df["Campus status"] == "Without FBD")
    )
    assert not bad.any()


def test_exclusion_filter_does_not_exclude_clean_person():
    # A person with no exclusion criteria must land entirely in deployable — not excluded.
    import pandas as pd
    from pipeline.exclusion_filters import apply_exclusion_filters

    clean = pd.DataFrame([{
        "Leave type":               None,
        "BZ resources":             None,
        "D rated":                  None,
        "Exit":                     None,
        "Resignation Submitted Date": pd.NaT,
        "Campus/Lateral":           "Lateral",
        "Campus status":            None,
        "Current or Future Bench":  "Current bench",
        "Resource Start Date":      pd.Timestamp("2024-01-01"),
    }])
    deployable, excluded = apply_exclusion_filters(clean)
    assert len(deployable) == 1, "Clean person must not be excluded"
    assert len(excluded) == 0,   "No one should be in the excluded bucket"
