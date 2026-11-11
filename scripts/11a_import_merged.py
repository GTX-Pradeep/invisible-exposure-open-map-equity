"""Merged project, step 2: import per-tract fields from MapEquityChallenge.

Writes data/external/merged_inputs.csv (one row per GEOID) and outputs/tables/merged/merged_sources.json (SHA-256 of
every source file). Nothing here is ever an input to the expectation model (tests/test_core.py checks this).

Imported:
  MEC eda_outputs/base_table.parquet     mec_bldg_n, mec_bldg_n_class, mec_bldg_n_msft, mec_bldg_n_lt30m2, mec_bldg_n_height
  MEC eda_outputs/audit_strata.parquet   alternative hazard indicators for N2
  MEC eda_outputs/model_inputs.parquet   the 9 Isolation Forest inputs of experiments/08 (for N3)
  MEC ablation OOF cache                 NB and XGB expected building counts (spatial folds; eastern-wa = transfer)
  project notebook 09 models E and G     XGB expected building counts, recomputed here exactly as in the notebook
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

cfg = yaml.safe_load(open("config/config.yaml"))["merge"]
MEC = Path(cfg["mapequity_root"]).resolve()
AR = MEC / "academic_research"
sources = {}


def src(p: Path) -> Path:
    sources[str(p.relative_to(MEC.parent))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


# 1. MEC building attributes and Microsoft counts (all building sizes)
b = pd.read_parquet(src(MEC / "eda_outputs/base_table.parquet"))
out = b[["GEOID", "bldg_n", "bldg_n_class", "bldg_n_msft", "bldg_n_lt30m2", "bldg_n_height"]].rename(
    columns=lambda c: c if c == "GEOID" else "mec_" + c)

# 2. alternative hazard indicators (challenge strata, via the MEC EDA)
HZ = ["epht_heat_days_summer", "gehe_wbgt28_days_mean", "hwd_maxtemp_mean", "usfs_WHP_mean",
      "mtbs_wildfire_burned_pct_land", "pmdi_mean", "spi12_mean", "usdm_summer_dsci"]
a = pd.read_parquet(src(MEC / "eda_outputs/audit_strata.parquet"))[["GEOID"] + HZ]
out = out.merge(a.rename(columns={c: "alt_" + c for c in HZ}), on="GEOID", how="left", validate="one_to_one")

# 3. Isolation Forest inputs (experiments/08_isolation_forest.ipynb)
IF = ["land_km2", "housing_units", "pop_total", "bldg_n", "road_km_hwy", "poi_n", "poi_n_fire", "poi_n_ems", "poi_n_school"]
mi = pd.read_parquet(src(MEC / "eda_outputs/model_inputs.parquet"))[["GEOID"] + IF]
out = out.merge(mi.rename(columns={c: "if_" + c for c in IF}), on="GEOID", how="left", validate="one_to_one")

# 4. NB and XGB expected building counts from the frozen OOF cache (feature set B0)
c = pd.read_parquet(src(AR / "ablation_benchmarks/cache/oof_predictions.parquet"),
                    columns=["design", "component", "model", "feature_set", "GEOID", "y", "mu"])
c = c[(c.component == "buildings") & (c.feature_set == "B0") & c.model.isin(["nb", "xgb"]) & c.design.isin(["spatial", "transfer"])]
w = c.pivot_table(index="GEOID", columns="model", values="mu", aggfunc="first").add_prefix("exp_mu_")
w["exp_y"] = c.groupby("GEOID").y.first()
out = out.merge(w.reset_index(), on="GEOID", how="left", validate="one_to_one")

# 5. project notebook 09: models E (structure + rural + region) and G (+ neighbours' structure and building density)
sys.path.insert(0, str(MEC))
from scipy.spatial import cKDTree
from sklearn.model_selection import GroupKFold
from mapequity.modeling import _fit_predict, STRUCTURAL_COLUMNS

t = pd.read_parquet(src(AR / "shared_inputs/features/tract_features.parquet"))
au = pd.read_parquet(src(AR / "shared_inputs/features/audit_attributes.parquet"))[["GEOID", "ur_class"]]
d = t.merge(au, on="GEOID", validate="one_to_one")
d["rural"] = d.ur_class.eq("Rural")
y = d.building_count.to_numpy(float)
S = np.log1p(d[list(STRUCTURAL_COLUMNS)].astype(float)).to_numpy()
dens = np.log1p(d.building_count / d.land_area_km2).to_numpy()[:, None]
K = 8
nbr = np.zeros((len(d), K), int)
for _, g in d.groupby("region"):
    i = g.index.to_numpy()
    xy = g[["centroid_x_m", "centroid_y_m"]].to_numpy()
    nbr[i] = i[cKDTree(xy).query(xy, k=K + 1)[1][:, 1:]]
med = lambda M: np.median(M[nbr], axis=1)
base = np.hstack([S, d.rural.to_numpy(float)[:, None], pd.get_dummies(d.region, dtype=float).to_numpy()])
FE = {"E": base, "G": np.hstack([base, med(S), med(dens)])}
folds = list(GroupKFold(5).split(np.arange(len(d)), groups=d.spatial_block_50km.astype(str)))
p = pd.DataFrame({"GEOID": d.GEOID.astype(str), "prj_y": y})
for name, X in FE.items():
    mu = np.full(len(d), np.nan)
    for k, (tr, te) in enumerate(folds):
        mu[te] = _fit_predict("xgboost", X[tr], y[tr], X[te], 42 + k)[0]
    p[f"prj_mu_{name}"] = mu
out = out.merge(p, on="GEOID", how="left", validate="one_to_one")

out["GEOID"] = out.GEOID.astype(str).str.zfill(11)
Path(cfg["out"]).parent.mkdir(parents=True, exist_ok=True)
Path("outputs/tables/merged").mkdir(parents=True, exist_ok=True)
out.to_csv(cfg["out"], index=False)
json.dump({"rows": len(out), "missing_by_column": out.isna().sum()[lambda s: s > 0].to_dict(), "sha256": sources},
          open(Path("outputs/tables/merged").joinpath("merged_sources.json"), "w"), indent=2)
print(out.shape, "| missing:", out.isna().sum()[lambda s: s > 0].to_dict())
