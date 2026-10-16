"""Expectation model with conformal prediction intervals.

We predict log1p(count) from structural features with LightGBM, then use
split-conformal calibration so each tract gets an interval. A tract is
flagged as a coverage-risk tract only when the observed count falls below
the lower bound, which separates "map is missing things" from "model is
unsure".
"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from .features import AUDIT_ONLY_COLUMNS


def _check_no_audit_leakage(cols):
    leaked = [c for c in cols if any(a in c.lower() for a in AUDIT_ONLY_COLUMNS)]
    if leaked:
        raise ValueError(f"Audit-only variables in expectation model: {leaked}")


def fit_predict_conformal(
    train: pd.DataFrame,
    calib: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    target: str,
    alpha: float = 0.10,
    seed: int = 42,
) -> pd.DataFrame:
    """Train on `train`, calibrate on `calib`, predict intervals for `test`.

    Returns test rows with columns: expected, lower, upper, observed,
    shortfall (log scale), flagged.
    """
    _check_no_audit_leakage(features)
    model = lgb.LGBMRegressor(
        n_estimators=600, learning_rate=0.03, num_leaves=31,
        min_child_samples=20, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.8, random_state=seed, verbose=-1,
    )
    y_tr = np.log1p(train[target])
    model.fit(train[features], y_tr)

    # Split-conformal: absolute residual quantile on calibration set
    resid = np.abs(np.log1p(calib[target]) - model.predict(calib[features]))
    n = len(resid)
    q = np.quantile(resid, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n))

    pred = model.predict(test[features])
    out = test[["GEOID"]].copy()
    out["observed"] = test[target].values
    out["expected"] = np.expm1(pred)
    out["lower"] = np.expm1(pred - q).clip(min=0)
    out["upper"] = np.expm1(pred + q)
    out["shortfall_log"] = pred - np.log1p(out["observed"])
    out["flagged"] = out["observed"] < out["lower"]
    out["missing_estimate"] = (out["expected"] - out["observed"]).clip(lower=0)
    return out
