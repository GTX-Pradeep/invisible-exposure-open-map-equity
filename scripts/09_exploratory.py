"""Exploratory (not pre-registered) analyses, labelled as such in the paper.
E1  Release regression: Overture 2026-09/10 dropped Microsoft footprints in Bexar County, TX; does the
    reference-free model detect it?
E2  Normalization bias: does a map-trained expectation absorb group-structured under-mapping?
    Compared with a reference-anchored expectation (same structural model trained on USA Structures).
E3  H3 sensitivity to the release regression (Aug-2026 endpoint; excluding Bexar County)."""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import yaml
from coverage_risk.audit import CONTRASTS, continuous_contrast, flag_contrast
from coverage_risk.model import STRUCTURAL, crossfit_cqr, make_folds

cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
T = "outputs/tables"
d = pd.read_parquet("data/processed/catchup_frame.parquet")
out = {}

# E1
d["loss_aug_oct"] = (d.r2026a_bldg450 - d.r2026b_bldg450) / d.r2026a_bldg450.clip(lower=1)
reg = d.loss_aug_oct > 0.20
gap_oct = d.r2026b_bldg450 / d.ref_bldg < 0.8
out["E1"] = {"tracts_regressed_gt20pct": int(reg.sum()), "of_which_bexar": int((reg & (d.county == "48029")).sum()),
             "buildings_lost": float((d.r2026a_bldg450 - d.r2026b_bldg450)[reg].sum()),
             "residents": float(d.loc[reg, "pop"].sum()), "housing_units": float(d.loc[reg, "hu"].sum()),
             "flag_rate_before": float(d.loc[reg, "flag_r2026a"].mean()), "flag_rate_after": float(d.loc[reg, "flag_r2026b"].mean()),
             "flag_rate_other_tracts_after": float(d.loc[~reg, "flag_r2026b"].mean()),
             "recall_of_ref_gaps_in_regressed": float((d.flag_r2026b & gap_oct & reg).sum() / max((gap_oct & reg).sum(), 1)),
             "share_svi_q4_regressed": float((d.loc[reg, "svi"] == "Q4").mean()), "share_svi_q4_all": float((d.svi == "Q4").mean()),
             "mean_svi_regressed": float(d.loc[reg, "svi_overall"].mean()), "mean_svi_all": float(d.svi_overall.mean())}

# E2: normalization bias
ok = d.ref_bldg.notna() & (d.ref_bldg >= 10)
s = d[ok].copy()
s["exp_minus_ref"] = s.bldg_q_med - np.log1p(s.ref_bldg)          # map-trained expectation relative to reference
s["obs_minus_ref"] = np.log1p(s.r2026a_bldg450) - np.log1p(s.ref_bldg)
rows = []
for grp in ["svi", "cvi", "rural", "tribal"]:
    for o in ["obs_minus_ref", "exp_minus_ref"]:
        rows.append({"analysis": "E2", **continuous_contrast(s, o, grp)})
# reference-anchored expectation: same structural model, target = USA Structures count; flag Overture below its lower bound
folds = make_folds(s, "spatial", k=10, seed=mc["seed"], km=mc["spatial_block_km"])
anc = crossfit_cqr(s, "ref_bldg", STRUCTURAL, folds, mc["alpha"], mc["lgbm"], mc["seed"])
s["anchored_flag"] = np.log1p(s.r2026a_bldg450.values) < anc.lower_log.values
for grp in ["svi", "cvi", "rural", "tribal"]:
    for o in ["bldg_flag", "anchored_flag", "ref_gap_b"]:
        x = s.copy(); x[o] = x[o].fillna(False).astype(float)
        rows.append({"analysis": "E2-flags", **flag_contrast(x, o, grp, n_boot=1000, seed=mc["seed"])})
e2 = pd.DataFrame(rows); e2.to_csv(f"{T}/e2_normalization.csv", index=False)
print(e2[["analysis", "outcome", "group", "mean_hi", "mean_lo", "adj_diff", "ci_lo", "ci_hi", "rate_hi", "rate_lo", "adj_odds_ratio", "p"]].round(4).to_string())
# absorption: share of the group's observed reference shortfall reproduced by the map-trained expectation
for grp in ["svi", "cvi", "rural", "tribal"]:
    o = e2[(e2.analysis == "E2") & (e2.group == grp)].set_index("outcome")
    out[f"E2_absorbed_share_{grp}"] = float(o.loc["exp_minus_ref", "adj_diff"] / o.loc["obs_minus_ref", "adj_diff"])
# resolution: residual SD of the structural expectation (log scale) vs. size of an 80%-threshold gap
out["E2_resid_sd_log_maptrained"] = float((s.bldg_y_log - s.bldg_q_med).std())
out["E2_resid_sd_log_anchored"] = float((anc.y_log - anc.q_med).std())
out["E2_gap_threshold_log"] = float(-np.log(0.8))
out["E2_anchored_coverage_of_ref"] = float(anc.covered.mean())
out["E2_anchored_flag_rate"] = float(s.anchored_flag.mean())
from coverage_risk.validation import flag_skill
out["E2_anchored_skill"] = flag_skill(s.anchored_flag.values, anc.lower_log.values - np.log1p(s.r2026a_bldg450.values), s.ref_gap_b.fillna(False).values)
out["E2_maptrained_skill_same_tracts"] = flag_skill(s.bldg_flag.values, s.bldg_deficit_z.values, s.ref_gap_b.fillna(False).values)

# E3: H3 sensitivity
rows = []
s["d_lc_aug"] = s.lc_r2026a - s.lc_r2023
nb = s[s.county != "48029"]
for label, frame, o in [("endpoint 2026-08-19", s, "d_lc_aug"), ("excluding Bexar County", nb, "d_lc")]:
    for grp in ["svi", "cvi", "rural", "tribal"]:
        rows.append({"analysis": "E3", "variant": label, **continuous_contrast(frame, o, grp)})
e3 = pd.DataFrame(rows); e3.to_csv(f"{T}/e3_h3_sensitivity.csv", index=False)
print(e3[["variant", "group", "mean_hi", "mean_lo", "adj_diff", "ci_lo", "ci_hi", "p"]].round(4).to_string())
json.dump(out, open(f"{T}/exploratory.json", "w"), indent=2, default=float)
print(json.dumps(out, indent=2, default=float))
d.assign(loss_aug_oct=d.loss_aug_oct).to_parquet("data/processed/catchup_frame.parquet", index=False)
