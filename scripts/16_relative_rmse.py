"""Relative RMSE of roads, fire stations, EMS and buildings, re-estimated from this repository's data only.

usage: python scripts/16_relative_rmse.py      (run from the repository root; about a minute)

Replaces the dependence on the companion project's caches. Same design as the companion pipeline:
  targets   building count, highway km, fire stations, EMS stations per tract (data/external/merged_inputs.csv)
  inputs    the five structural features of the frozen MapEquity model: land area, housing units, housing density,
            population, population density (logged)
  folds     the 10 spatial-block folds of the conformal model (modelling/tables/oof_bldg_primary.parquet), and
            leave-one-region-out
  models    constant (training mean), Poisson GLM, Tweedie GLM (power 1.5), LightGBM and XGBoost (Poisson loss)
  metric    relative RMSE = RMSE / SD of the target, pooled over tracts; 1.0 means no better than a constant
writes outputs/tables/review/relative_rmse_repo.csv and highway_loro_repo.csv
"""
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import PoissonRegressor, TweedieRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20261109
m = pd.read_csv("data/external/merged_inputs.csv", dtype={"GEOID": str})
r = pd.read_csv("deliverables/dataset/invisible_exposure_tract_results.csv", dtype={"GEOID": str}, usecols=["GEOID", "region"])
f = pd.read_parquet("modelling/tables/oof_bldg_primary.parquet", columns=["GEOID", "fold"])
d = m.merge(r, on="GEOID").merge(f, on="GEOID")
d["fold"] = d.fold.astype(str).astype(int)

land = d.if_land_km2.clip(lower=1e-3)
X = pd.DataFrame({"log_land": np.log(land), "log_hu": np.log1p(d.if_housing_units), "log_hu_density": np.log1p(d.if_housing_units / land),
                  "log_pop": np.log1p(d.if_pop_total), "log_pop_density": np.log1p(d.if_pop_total / land)}).values
TARGETS = {"buildings": "if_bldg_n", "highway": "if_road_km_hwy", "fire": "if_poi_n_fire", "ems": "if_poi_n_ems"}
MODELS = {
    "constant": lambda: None,
    "poisson": lambda: make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-4, max_iter=1000)),
    "tweedie": lambda: make_pipeline(StandardScaler(), TweedieRegressor(power=1.5, link="log", alpha=1e-4, max_iter=1000)),
    "lightgbm": lambda: lgb.LGBMRegressor(objective="poisson", n_estimators=400, learning_rate=0.03, num_leaves=31,
                                          min_child_samples=40, subsample=0.8, subsample_freq=1, random_state=SEED, verbose=-1),
    "xgboost": lambda: xgb.XGBRegressor(objective="count:poisson", n_estimators=400, learning_rate=0.03, max_depth=5,
                                        subsample=0.8, random_state=SEED, n_jobs=4),
}


def oof(y, groups):
    preds = {k: np.zeros(len(y)) for k in MODELS}
    for g in np.unique(groups):
        te, tr = groups == g, groups != g
        for k, make in MODELS.items():
            if k == "constant":
                preds[k][te] = y[tr].mean(); continue
            mod = make(); mod.fit(X[tr], y[tr]); preds[k][te] = np.clip(mod.predict(X[te]), 0, None)
    return preds


rows, hw = [], None
for design, groups in [("spatial", d.fold.values), ("loro", d.region.values)]:
    for comp, col in TARGETS.items():
        y = d[col].values.astype(float)
        p = oof(y, groups)
        for k, mu in p.items():
            rows.append({"design": design, "component": comp, "model": k,
                         "relative_rmse": np.sqrt(np.mean((y - mu) ** 2)) / y.std()})
        if design == "loro" and comp == "highway":
            hw = d[["region"]].assign(observed_km=y, predicted_km=p["tweedie"]).groupby("region").sum()
            hw["predicted_over_observed"] = hw.predicted_km / hw.observed_km

out = Path("outputs/tables/review"); out.mkdir(parents=True, exist_ok=True)
t = pd.DataFrame(rows); t.to_csv(out / "relative_rmse_repo.csv", index=False)
hw.reset_index().to_csv(out / "highway_loro_repo.csv", index=False)
print(t.pivot_table(index=["design", "component"], columns="model", values="relative_rmse").round(3).to_string())
print(hw.round(3).to_string())
