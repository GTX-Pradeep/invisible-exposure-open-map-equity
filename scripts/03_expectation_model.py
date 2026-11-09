"""Phase 3: expected count, 90% conformal range, flag and shortfall per tract (buildings + POIs).
Primary specification: spatial-block cross-fitting (50 km), global CQR calibration."""
import json
import pandas as pd
import yaml
from coverage_risk.model import STRUCTURAL, crossfit_cqr, make_folds, feature_importance

cfg = yaml.safe_load(open("config/config.yaml"))
mc = cfg["model"]
df = pd.read_parquet("data/processed/tracts_all.parquet")
folds = make_folds(df, "spatial", k=10, seed=mc["seed"], km=mc["spatial_block_km"])
res, summ = {}, {}
for layer, target in [("bldg", "r2026a_bldg450"), ("poi", "r2026a_poi")]:
    out = crossfit_cqr(df, target, STRUCTURAL, folds, alpha=mc["alpha"], params=mc["lgbm"], seed=mc["seed"])
    out.columns = ["GEOID"] + [f"{layer}_{c}" for c in out.columns[1:]]
    res[layer] = out
    summ[layer] = {"coverage": float(out[f"{layer}_covered"].mean()), "flag_rate": float(out[f"{layer}_flag"].mean()),
                   "n_flag": int(out[f"{layer}_flag"].sum()),
                   "shortfall_total": float(out.loc[out[f"{layer}_flag"], f"{layer}_shortfall"].sum()),
                   "shortfall_lower_total": float(out[f"{layer}_shortfall_lower"].sum())}
    fi = feature_importance(df, target, STRUCTURAL, mc["lgbm"], mc["seed"])
    fi.to_csv(f"outputs/tables/feature_importance_{layer}.csv")
pred = res["bldg"].merge(res["poi"], on="GEOID")
pred.to_parquet("data/processed/expectation.parquet", index=False)
json.dump(summ, open("outputs/tables/phase3_summary.json", "w"), indent=2)
print(json.dumps(summ, indent=2))
ok = all(0.87 <= s["coverage"] <= 0.93 for s in summ.values())
print("EXIT CHECK (coverage within 87-93%):", "PASS" if ok else "FAIL")
