"""Expectation model: how many buildings / POIs *should* a tract contain, with conformal ranges.

* LightGBM quantile regression (q = alpha/2, 0.5, 1 - alpha/2) on log1p(count), structural columns only.
* Cross-fitting: every tract's prediction comes from a model that never saw its fold (fold = random,
  spatial block, or whole region), so a tract's own deficit cannot shrink its expectation.
* Conformalized quantile regression (CQR; Romano et al. 2019) in a cross-conformal arrangement: the
  correction for fold k is the finite-sample (1-alpha) quantile of out-of-fold conformity scores of
  the other folds; optionally Mondrian (calibrated within each region).
* A tract is flagged when its observed count falls below the conformal lower bound.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from .features import AUDIT_ONLY_PREFIXES

LEAKY_EXACT = {"GEOID", "county", "lat", "lon", "ALAND"}


def assert_no_leakage(cols) -> None:
    bad = [c for c in cols if c in LEAKY_EXACT or c.lower().startswith(AUDIT_ONLY_PREFIXES)
           or c.startswith(("r2023_", "r2026a_", "r2026b_", "bsh_", "psh_", "b_", "p_"))
           # merged-project imports (scripts/11a_import_merged.py): comparison data only, never model inputs
           or c.startswith(("mec_", "alt_", "if_", "exp_", "prj_"))]
    if bad:
        raise ValueError(f"audit/outcome columns refused as model inputs: {bad}")


STRUCTURAL = [
    "hu", "pop", "households", "gq_pop", "vacant_share", "u1_det", "u1_att", "u2", "u3_4", "u5_9", "u10_19",
    "u20_49", "u50p", "u_mobile", "u_boat_rv", "struct_equiv", "sh_u1_det", "sh_u1_att", "sh_u2", "sh_u3_4",
    "sh_u5_9", "sh_u10_19", "sh_u20_49", "sh_u50p", "sh_u_mobile", "sh_u_boat_rv", "sh_yb2020p", "sh_yb2010",
    "sh_yb2000", "sh_yb1990", "sh_yb1980", "sh_yb1970", "sh_yb1960", "sh_yb1950", "sh_yb1940", "sh_yb1939m",
    "land_km2", "log_land_km2", "hu_density", "pop_density", "log_hu", "log_pop", "log_struct_equiv",
    "log_hu_density",
]
from .features import JOB_COLS  # noqa: E402
STRUCTURAL = STRUCTURAL + JOB_COLS


def spatial_blocks(lat, lon, km: float = 50.0) -> np.ndarray:
    """Square blocks of ~km size in an equal-distance approximation."""
    y = np.asarray(lat) * 110.574
    x = np.asarray(lon) * 111.320 * np.cos(np.radians(np.asarray(lat)))
    return (np.floor(x / km).astype(int) * 100_003 + np.floor(y / km).astype(int)).astype(np.int64)


def make_folds(df: pd.DataFrame, scheme: str, k: int = 10, seed: int = 0, km: float = 50.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(df)
    if scheme == "random":
        return rng.permutation(np.arange(n) % k)
    if scheme == "spatial":
        blocks = spatial_blocks(df.lat, df.lon, km)
        ub = np.unique(blocks)
        assign = dict(zip(ub, rng.permutation(np.arange(len(ub)) % k)))
        return np.array([assign[b] for b in blocks])
    if scheme == "region":
        cats = pd.Categorical(df.region)
        return cats.codes.astype(int)
    raise ValueError(scheme)


def _fit_q(X, y, q, params, seed):
    m = lgb.LGBMRegressor(objective="quantile", alpha=q, random_state=seed, verbose=-1, **params)
    m.fit(X, y)
    return m


def crossfit_cqr(df: pd.DataFrame, target: str, features: list[str], folds: np.ndarray, alpha: float = 0.10,
                 params: dict | None = None, seed: int = 0, mondrian: pd.Series | None = None) -> pd.DataFrame:
    """Return out-of-fold q_lo, q_med, q_hi (log scale) and conformal lower/upper bounds."""
    assert_no_leakage(features)
    params = params or {}
    X = df[features].astype(float).values
    y = np.log1p(df[target].astype(float).values)
    n = len(df)
    q_lo, q_med, q_hi = np.empty(n), np.empty(n), np.empty(n)
    for f in np.unique(folds):
        tr, te = folds != f, folds == f
        for q, arr in ((alpha / 2, q_lo), (0.5, q_med), (1 - alpha / 2, q_hi)):
            arr[te] = _fit_q(X[tr], y[tr], q, params, seed).predict(X[te])
    lo, hi = np.minimum(q_lo, q_med), np.maximum(q_hi, q_med)
    score = np.maximum(lo - y, y - hi)  # CQR conformity score (out-of-fold)
    corr = np.empty(n)
    groups = np.zeros(n, dtype=int) if mondrian is None else pd.Categorical(mondrian).codes
    for g in np.unique(groups):
        in_g = groups == g
        for f in np.unique(folds):
            cal = in_g & (folds != f)
            tgt = in_g & (folds == f)
            if not tgt.any():
                continue
            if cal.sum() < 20:  # fall back to all other folds if the group is too small
                cal = folds != f
            s = np.sort(score[cal])
            m = len(s)
            idx = min(m - 1, int(np.ceil((1 - alpha) * (m + 1))) - 1)
            corr[tgt] = s[idx]
    out = pd.DataFrame({
        "GEOID": df.GEOID.values, "y_log": y, "q_lo": lo, "q_med": q_med, "q_hi": hi, "cqr_corr": corr,
        "lower_log": lo - corr, "upper_log": hi + corr, "fold": folds,
    })
    out["observed"] = df[target].values
    out["expected"] = np.expm1(q_med)
    out["lower"] = np.maximum(np.expm1(out.lower_log), 0)
    out["upper"] = np.expm1(out.upper_log)
    out["covered"] = (y >= out.lower_log) & (y <= out.upper_log)
    out["flag"] = y < out.lower_log
    out["shortfall"] = np.maximum(out.expected - out.observed, 0)
    out["shortfall_lower"] = np.maximum(out.lower - out.observed, 0)  # conservative: below the lower bound
    # standardized deficit: how far below the median, in units of the lower half-width
    half = np.maximum(q_med - out.lower_log, 1e-6)
    out["deficit_z"] = (q_med - y) / half
    return out


def feature_importance(df, target, features, params=None, seed=0) -> pd.Series:
    assert_no_leakage(features)
    m = _fit_q(df[features].astype(float).values, np.log1p(df[target].astype(float).values), 0.5, params or {}, seed)
    return pd.Series(m.booster_.feature_importance("gain"), index=features).sort_values(ascending=False)
