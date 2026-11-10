"""Schema and consistency checks for the tract table (scripts/02_build_tract_table.py runs them before saving).

Each check is cheap and has a reason: a silent join failure, a mis-parsed ACS table or a broken aggregation
would otherwise flow straight into the model. check_tract_table raises AssertionError listing every failure.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STRUCTURAL_REQUIRED = ["hu", "pop", "households", "land_km2", "jobs"]
SHARE_PREFIXES = ("sh_", "jsh_", "bsh_", "psh_")
SHARE_EXACT = ["vacant_share", "b_src_max_share", "b_ml_share", "p_src_max_share", "p_conf50_share"]
SRC_COLS = ["r2026a_src_osm", "r2026a_src_msft", "r2026a_src_google", "r2026a_src_esri", "r2026a_src_other"]


def check_tract_table(df: pd.DataFrame, expected_geoids=None, max_missing_ref: float = 0.01) -> dict:
    """Return a dict of check -> result; raise AssertionError if any check fails."""
    fail, res = [], {}

    def chk(name, ok, detail=""):
        res[name] = "ok" if ok else f"FAIL {detail}".strip()
        if not ok:
            fail.append(f"{name}: {detail}")

    g = df["GEOID"].astype(str)
    chk("GEOID unique", g.is_unique, f"{g.duplicated().sum()} duplicates")
    ok11 = g.str.fullmatch(r"\d{11}")
    chk("GEOID is 11 digits", ok11.all(), f"{(~ok11).sum()} bad")
    if expected_geoids is not None:
        exp = set(map(str, expected_geoids))
        chk("tract list matches the study list", set(g) == exp, f"missing {len(exp - set(g))}, extra {len(set(g) - exp)}")
    miss = df[[c for c in STRUCTURAL_REQUIRED if c in df]].isna().sum()
    chk("no missing structural inputs", miss.sum() == 0, miss[miss > 0].to_dict())
    counts = [c for c in df.columns if c in STRUCTURAL_REQUIRED or c.startswith(("r2026a_bldg", "r2026a_poi", "r2026a_src_", "ref_bldg", "jobs"))]
    neg = (df[counts].select_dtypes("number") < 0).sum()
    chk("counts are non-negative", neg.sum() == 0, neg[neg > 0].to_dict())
    shares = [c for c in df.columns if c.startswith(SHARE_PREFIXES) or c in SHARE_EXACT]
    s = df[shares].select_dtypes("number")
    bad = ((s < -1e-9) | (s > 1 + 1e-9)).sum()
    chk("shares lie in [0, 1]", bad.sum() == 0, bad[bad > 0].to_dict())
    if {"r2026a_bldg", "r2026a_bldg450"} <= set(df.columns):
        chk("buildings >= 450 sq ft <= all buildings", (df.r2026a_bldg450 <= df.r2026a_bldg).all())
    if set(SRC_COLS + ["r2026a_bldg"]) <= set(df.columns):
        chk("source counts add up to buildings", (df[SRC_COLS].sum(axis=1) == df.r2026a_bldg).all(),
            f"{(df[SRC_COLS].sum(axis=1) != df.r2026a_bldg).sum()} tracts differ")
    if {"r2026a_poi", "r2026a_poi_conf50", "r2026a_poi_multisrc"} <= set(df.columns):
        chk("confident / multi-source places <= places", ((df.r2026a_poi_conf50 <= df.r2026a_poi) & (df.r2026a_poi_multisrc <= df.r2026a_poi)).all())
    if "ref_bldg" in df:
        m = df.ref_bldg.isna().mean()
        chk(f"USA Structures missing for <= {max_missing_ref:.0%} of tracts", m <= max_missing_ref, f"{m:.2%}")
    if "land_km2" in df:
        chk("land area is non-negative", (df.land_km2 >= 0).all())
    res["n_tracts"] = len(df)
    if fail:
        raise AssertionError("tract table checks failed:\n  " + "\n  ".join(fail))
    return res
