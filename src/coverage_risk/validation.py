"""Validation utilities: CV-scheme comparison, flag skill against independent references, deletion test."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from scipy.stats import spearmanr

from .model import crossfit_cqr, make_folds


def cv_scheme_table(df, target, features, alpha, params, seed, km) -> pd.DataFrame:
    rows = []
    for scheme in ["random", "spatial", "region"]:
        folds = make_folds(df, scheme, k=10, seed=seed, km=km)
        for mond in [False, True]:
            out = crossfit_cqr(df, target, features, folds, alpha, params, seed, mondrian=df.region if mond else None)
            resid = out.y_log - out.q_med
            r = {"scheme": scheme, "calibration": "mondrian-region" if mond else "global",
                 "coverage": out.covered.mean(), "flag_rate": out.flag.mean(),
                 "mae_log": np.abs(resid).mean(), "r2_log": 1 - (resid**2).sum() / ((out.y_log - out.y_log.mean())**2).sum(),
                 "width_log": (out.upper_log - out.lower_log).mean()}
            cov = out.groupby(df.region.values).covered.mean()
            r.update({f"cov_{k}": v for k, v in cov.items()})
            r["cov_region_min"] = cov.min(); r["cov_region_max"] = cov.max()
            rows.append(r)
    return pd.DataFrame(rows)


def flag_skill(flag: np.ndarray, score: np.ndarray, truth: np.ndarray) -> dict:
    flag, truth = np.asarray(flag, bool), np.asarray(truth, bool)
    ok = ~np.isnan(score)
    tp = (flag & truth).sum()
    prec = tp / max(flag.sum(), 1)
    rec = tp / max(truth.sum(), 1)
    return {"n": int(len(flag)), "prevalence": float(truth.mean()), "n_flag": int(flag.sum()), "n_true": int(truth.sum()),
            "precision": float(prec), "recall": float(rec), "f1": float(2 * prec * rec / max(prec + rec, 1e-9)),
            "lift": float(prec / max(truth.mean(), 1e-9)),
            "auc": float(roc_auc_score(truth[ok], score[ok])) if truth[ok].any() and (~truth[ok]).any() else np.nan,
            "pr_auc": float(average_precision_score(truth[ok], score[ok])) if truth[ok].any() else np.nan}


def deletion_test(out: pd.DataFrame, fractions=(0.1, 0.2, 0.3, 0.5, 0.7, 0.9), n_tracts: int = 2000, seed: int = 0,
                  eligible: np.ndarray | None = None) -> pd.DataFrame:
    """Remove a share of a tract's mapped features and check whether the (already out-of-fold) lower
    bound flags it.  Valid because the tract's own observation never entered its model or calibration
    fold; only the observed count changes."""
    rng = np.random.default_rng(seed)
    pool = np.where(~out.flag.values if eligible is None else eligible)[0]
    idx = rng.choice(pool, size=min(n_tracts, len(pool)), replace=False)
    rows = []
    for f in fractions:
        y_new = np.log1p(np.floor(out.observed.values[idx] * (1 - f)))
        power = (y_new < out.lower_log.values[idx]).mean()
        rows.append({"removed_share": f, "detection_rate": power})
    return pd.DataFrame(rows)


def spearman(a, b) -> float:
    ok = ~(np.isnan(a) | np.isnan(b))
    return float(spearmanr(a[ok], b[ok]).statistic)
