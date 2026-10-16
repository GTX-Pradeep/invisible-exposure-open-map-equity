"""Hidden exposure and pre-registered equity audit.

Vulnerability and hazard variables enter ONLY here, after coverage-risk
scores have been computed from structural variables alone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def hidden_exposure(scores: pd.DataFrame, hazard: pd.Series, housing_units: pd.Series) -> pd.DataFrame:
    """Missing exposed structures, and per 1,000 housing units.

    hazard: tract-level exposure in [0, 1] (e.g., share of tract in high
    wildfire-hazard class). Must not be derived from POIs (avoid circularity).
    """
    out = scores.copy()
    out["hidden_exposed"] = out["missing_estimate"] * hazard.values
    out["hidden_exposed_per_1k_hu"] = 1000 * out["hidden_exposed"] / housing_units.replace(0, np.nan).values
    return out


def compare_groups(df: pd.DataFrame, outcome: str, group_col: str, a, b) -> dict:
    """Mann-Whitney test and median difference between two groups."""
    x = df.loc[df[group_col] == a, outcome].dropna()
    y = df.loc[df[group_col] == b, outcome].dropna()
    u, p = stats.mannwhitneyu(x, y, alternative="two-sided")
    return {"outcome": outcome, "group": group_col, "a": a, "b": b,
            "n_a": len(x), "n_b": len(y),
            "median_a": x.median(), "median_b": y.median(), "p": p}


def run_preregistered(df: pd.DataFrame, contrasts: list[dict], fdr_alpha: float = 0.05) -> pd.DataFrame:
    """Run a fixed list of contrasts with Benjamini-Hochberg correction.

    Each contrast: {"outcome", "group_col", "a", "b"}.
    """
    res = pd.DataFrame([compare_groups(df, **c) for c in contrasts])
    res["reject_fdr"], res["p_fdr"], *_ = multipletests(res["p"], alpha=fdr_alpha, method="fdr_bh")
    return res
