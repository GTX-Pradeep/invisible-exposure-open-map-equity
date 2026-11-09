"""Phase 4: does the reference-free model find real gaps?  Results reported whatever they show."""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from coverage_risk.model import STRUCTURAL
from coverage_risk.validation import cv_scheme_table, deletion_test, flag_skill, spearman

cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
df = pd.read_parquet("data/processed/tracts_all.parquet")
ex = pd.read_parquet("data/processed/expectation.parquet")
d = df.merge(ex, on="GEOID")
T = "outputs/tables"

# 1. CV schemes x calibration
cv = pd.concat([cv_scheme_table(df, t, STRUCTURAL, mc["alpha"], mc["lgbm"], mc["seed"], mc["spatial_block_km"]).assign(layer=l)
                for l, t in [("bldg", "r2026a_bldg450"), ("poi", "r2026a_poi")]])
cv.to_csv(f"{T}/cv_schemes.csv", index=False)
print(cv[["layer", "scheme", "calibration", "coverage", "flag_rate", "r2_log", "cov_region_min", "cov_region_max"]].round(3).to_string())

# 2. flags vs independent references
d["ref_ratio_b"] = d.r2026a_bldg450 / d.ref_bldg
d["ref_gap_b"] = d.ref_ratio_b < 0.8
# POI: Overture/ZBP establishment ratio; gap = below 1/2 of the region's median ratio
d["ref_ratio_p"] = d.r2026a_poi / d.ref_est_zbp.where(d.ref_est_zbp >= 5)
d["ref_gap_p"] = d.ref_ratio_p < 0.5 * d.groupby("region").ref_ratio_p.transform("median")

# baselines: (a) map/housing ratio, (b) OLS log-log on housing units (in-sample, generous)
d["base_ratio_b"] = -(np.log1p(d.r2026a_bldg450) - np.log1p(d.struct_equiv))
X = sm.add_constant(np.column_stack([np.log1p(d.hu), np.log1p(d.land_km2)]))
for l, t in [("b", "r2026a_bldg450"), ("p", "r2026a_poi")]:
    ols = sm.OLS(np.log1p(d[t]), X).fit()
    d[f"base_ols_{l}"] = -(ols.resid / ols.resid.std())
d["base_ratio_p"] = -(np.log1p(d.r2026a_poi) - np.log1p(d.hu))

rows = []
for l, truth, ok in [("bldg", "ref_gap_b", d.ref_bldg.notna()), ("poi", "ref_gap_p", d.ref_ratio_p.notna())]:
    s = d[ok]
    pre = "b" if l == "bldg" else "p"
    for name, score in [("conformal model", s[f"{l}_deficit_z"]), ("OLS log-HU", s[f"base_ols_{pre}"]),
                        ("map/housing ratio", s[f"base_ratio_{pre}"])]:
        flag = s[f"{l}_flag"].values if name == "conformal model" else (score >= np.quantile(score, 1 - s[f"{l}_flag"].mean())).values
        r = flag_skill(flag, score.values, s[truth].values); r.update({"layer": l, "method": name})
        rows.append(r)
    for reg, g in s.groupby("region"):
        r = flag_skill(g[f"{l}_flag"].values, g[f"{l}_deficit_z"].values, g[truth].values)
        r.update({"layer": l, "method": f"conformal model | {reg}"}); rows.append(r)
sk = pd.DataFrame(rows)
sk.to_csv(f"{T}/flag_skill.csv", index=False)
print(sk[["layer", "method", "n", "prevalence", "n_flag", "precision", "recall", "lift", "auc", "pr_auc"]].round(3).to_string())

# continuous agreement: model shortfall (log) vs reference shortfall (log)
cont = {"bldg_spearman_deficit_vs_refratio": spearman(d.bldg_deficit_z.values, -np.log(d.ref_ratio_b.clip(lower=1e-3)).values),
        "poi_spearman_deficit_vs_refratio": spearman(d.poi_deficit_z.values, -np.log(d.ref_ratio_p.clip(lower=1e-3)).values)}

# 3. deletion test (power)
dt = []
for l in ["bldg", "poi"]:
    o = ex[[c for c in ex.columns if c.startswith(l + "_")]].copy(); o.columns = [c[len(l) + 1:] for c in o.columns]
    dt.append(deletion_test(o, seed=mc["seed"]).assign(layer=l))
dt = pd.concat(dt); dt.to_csv(f"{T}/deletion_test.csv", index=False)
print(dt.round(3).to_string())

# 4. county-level POI check (exact CBP aggregation)
cb = pd.read_parquet("data/processed/cbp_county.parquet")
cty = d.groupby("county").agg(poi=("r2026a_poi", "sum"), exp=("poi_expected", "sum")).reset_index().merge(cb, on="county")
cont["county_n"] = len(cty)
cont["county_spearman_poi_vs_cbp"] = spearman(np.log1p(cty.poi.values), np.log1p(cty.ref_est_cbp.values))
cont["county_spearman_expected_vs_cbp"] = spearman(np.log1p(cty.exp.values), np.log1p(cty.ref_est_cbp.values))
json.dump(cont, open(f"{T}/phase4_continuous.json", "w"), indent=2)
print(cont)
d.to_parquet("data/processed/validation_frame.parquet", index=False)
