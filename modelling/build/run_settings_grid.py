"""Step 7 (build order): how sensitive is the building model to its settings?

Refits the primary specification (scripts/03_expectation_model.py: LightGBM quantile + CQR, 10 folds of 50 km spatial
blocks, alpha 0.10) and one-at-a-time variants of each setting. Writes
  modelling/tables/01_settings_grid.csv      one row per variant: coverage, fit, width, skill vs USA Structures, stability
  modelling/tables/oof_bldg_primary.parquet  out-of-fold predictions of the primary model (input to notebook 02)
  modelling/tables/oof_poi_primary.parquet
Post-hoc sensitivity only: the primary specification is not changed by these results. No audit variable is used.
Run from the repo root:  PYTHONPATH=src python modelling/build/run_settings_grid.py   (about 30 minutes on 2 cores)
"""
import json, time
import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score

from coverage_risk.features import HOUSING_TYPE_COLS, JOB_COLS
from coverage_risk.model import STRUCTURAL, crossfit_cqr, make_folds

cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
df = pd.read_parquet("data/processed/tracts_all.parquet")
T = "modelling/tables"
ref = df.ref_bldg.notna()
truth = (df.r2026a_bldg450 / df.ref_bldg < 0.8).values
BASE = dict(params=mc["lgbm"], km=mc["spatial_block_km"], k=10, seed=mc["seed"], features=STRUCTURAL, alpha=mc["alpha"])
P = lambda **kw: {**mc["lgbm"], **kw}
VARIANTS = [
    ("primary (published)", "-", {}),
    ("n_estimators 300", "LightGBM", {"params": P(n_estimators=300)}),
    ("n_estimators 1200", "LightGBM", {"params": P(n_estimators=1200)}),
    ("learning_rate 0.015", "LightGBM", {"params": P(learning_rate=0.015)}),
    ("learning_rate 0.06", "LightGBM", {"params": P(learning_rate=0.06)}),
    ("num_leaves 15", "LightGBM", {"params": P(num_leaves=15)}),
    ("num_leaves 63", "LightGBM", {"params": P(num_leaves=63)}),
    ("min_child_samples 50", "LightGBM", {"params": P(min_child_samples=50)}),
    ("no row/column subsampling", "LightGBM", {"params": P(subsample=1.0, colsample_bytree=1.0, subsample_freq=0)}),
    ("seed 2", "randomness", {"seed": 2}),
    ("seed 3", "randomness", {"seed": 3}),
    ("spatial blocks 25 km", "validation", {"km": 25}),
    ("spatial blocks 100 km", "validation", {"km": 100}),
    ("5 folds", "validation", {"k": 5}),
    ("no housing-type inputs", "inputs", {"features": [c for c in STRUCTURAL if c not in HOUSING_TYPE_COLS]}),
    ("no LODES job inputs", "inputs", {"features": [c for c in STRUCTURAL if c not in JOB_COLS]}),
    ("only housing units, population, land", "inputs", {"features": ["hu", "pop", "land_km2", "log_hu", "log_pop", "log_land_km2", "hu_density", "pop_density", "log_hu_density"]}),
]


def metrics(out):
    resid = out.y_log - out.q_med
    cov = out.groupby(df.region.values).covered.mean()
    f, s = out.flag.values[ref.values], out.deficit_z.values[ref.values]
    t = truth[ref.values]
    tp = (f & t).sum()
    return {"coverage": out.covered.mean(), "cov_region_min": cov.min(), "cov_region_max": cov.max(),
            "n_flag": int(out.flag.sum()), "mae_log": np.abs(resid).mean(),
            "r2_log": 1 - (resid ** 2).sum() / ((out.y_log - out.y_log.mean()) ** 2).sum(),
            "width_log": (out.upper_log - out.lower_log).mean(),
            "precision": tp / max(f.sum(), 1), "recall": tp / t.sum(), "lift": tp / max(f.sum(), 1) / t.mean(),
            "roc_auc": roc_auc_score(t, s), "pr_auc": average_precision_score(t, s)}


rows, prim = [], None
for name, group, kw in VARIANTS:
    s = {**BASE, **kw}
    t0 = time.time()
    folds = make_folds(df, "spatial", k=s["k"], seed=mc["seed"], km=s["km"])
    out = crossfit_cqr(df, "r2026a_bldg450", s["features"], folds, alpha=s["alpha"], params=s["params"], seed=s["seed"])
    r = {"variant": name, "setting": group, "n_features": len(s["features"]), **metrics(out)}
    if prim is None:
        prim = out
        out.to_parquet(f"{T}/oof_bldg_primary.parquet", index=False)
    a, b = set(prim.GEOID[prim.flag]), set(out.GEOID[out.flag])
    r["flag_overlap_jaccard"] = len(a & b) / len(a | b)
    r["deficit_spearman_vs_primary"] = spearmanr(prim.deficit_z, out.deficit_z).statistic
    r["seconds"] = round(time.time() - t0)
    rows.append(r)
    pd.DataFrame(rows).to_csv(f"{T}/01_settings_grid.csv", index=False)
    print(f"{name:40s} cov {r['coverage']:.3f} flags {r['n_flag']:4d} r2 {r['r2_log']:.3f} prec {r['precision']:.3f} jacc {r['flag_overlap_jaccard']:.2f} {r['seconds']}s", flush=True)

folds = make_folds(df, "spatial", k=10, seed=mc["seed"], km=mc["spatial_block_km"])
crossfit_cqr(df, "r2026a_poi", STRUCTURAL, folds, alpha=mc["alpha"], params=mc["lgbm"], seed=mc["seed"]).to_parquet(f"{T}/oof_poi_primary.parquet", index=False)
print("done")
