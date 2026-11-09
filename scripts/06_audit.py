"""Phase 6: hidden exposure and the pre-registered equity contrasts (H1, H2, H5) with BH correction,
plus robustness runs.  Audit strata are joined here for the first time."""
import json
import numpy as np
import pandas as pd
import yaml
from coverage_risk.audit import CONTRASTS, bh, define_groups, exposure_ratio, flag_contrast, continuous_contrast

cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
T = "outputs/tables"
d = pd.read_parquet("data/processed/validation_frame.parquet")
st = pd.read_parquet("data/processed/strata_audit.parquet")
g = define_groups(st)
d = d.merge(g, on="GEOID").merge(st.drop(columns=["region"]), on="GEOID")
d.to_parquet("data/processed/audit_frame.parquet", index=False)

rows = []
for layer in ["bldg", "poi"]:
    for grp in ["svi", "cvi"]:
        rows.append({"hyp": "H1", "layer": layer, **flag_contrast(d, f"{layer}_flag", grp, seed=mc["seed"])})
    for grp in ["rural", "tribal"]:
        rows.append({"hyp": "H2", "layer": layer, **flag_contrast(d, f"{layer}_flag", grp, seed=mc["seed"])})
H = {"heat": "epht_heat_days_summer", "wildfire": "usfs_BP_mean", "drought": "usdm_summer_dsci"}
for hz, col in H.items():
    for grp in ["svi", "rural", "tribal"]:
        rows.append({"hyp": "H5", "layer": "bldg", "hazard_name": hz, **exposure_ratio(d, col, grp, seed=mc["seed"])})
res = pd.DataFrame(rows)
res.to_csv(f"{T}/h125_raw.csv", index=False)
print(res.drop(columns=[c for c in res.columns if c.startswith(("aor_ci", "rd_ci"))]).round(4).to_string())

# totals of hidden exposure
tot = {}
for hz, col in H.items():
    hi = d[col] >= d[col].quantile(2 / 3)
    tot[hz] = {"tracts_top_tercile": int(hi.sum()), "flagged_in_top": int((hi & d.bldg_flag).sum()),
               "missing_structures_lower": float(d.loc[hi, "bldg_shortfall_lower"].sum()),
               "missing_structures_median": float(d.loc[hi & d.bldg_flag, "bldg_shortfall"].sum()),
               "missing_pois_lower": float(d.loc[hi, "poi_shortfall_lower"].sum())}
tot["all"] = {"flagged_bldg": int(d.bldg_flag.sum()), "missing_structures_lower": float(d.bldg_shortfall_lower.sum()),
              "flagged_poi": int(d.poi_flag.sum()), "missing_pois_lower": float(d.poi_shortfall_lower.sum())}
json.dump(tot, open(f"{T}/hidden_exposure_totals.json", "w"), indent=2)
print(json.dumps(tot, indent=2))

# descriptive: flag rate and reference gap by group (for figures)
desc = []
for grp, (hi, lo) in CONTRASTS.items():
    for lvl in [hi, lo]:
        s = d[d[grp] == lvl]
        desc.append({"group": grp, "level": lvl, "n": len(s), "bldg_flag": s.bldg_flag.mean(), "poi_flag": s.poi_flag.mean(),
                     "ref_gap_b": s.ref_gap_b.mean(), "ref_gap_p": s.ref_gap_p.mean(),
                     "median_ref_ratio_b": s.ref_ratio_b.median(), "median_ref_ratio_p": s.ref_ratio_p.median()})
pd.DataFrame(desc).to_csv(f"{T}/group_descriptives.csv", index=False)
print(pd.DataFrame(desc).round(3).to_string())
