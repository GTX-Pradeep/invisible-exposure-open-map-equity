"""Pre-registered robustness runs: re-derive flags under alternative specifications and re-estimate the
H1/H2 flag contrasts (risk difference, adjusted odds ratio)."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from coverage_risk.audit import flag_contrast
from coverage_risk.features import HOUSING_TYPE_COLS
from coverage_risk.model import STRUCTURAL, crossfit_cqr, make_folds

cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
d = pd.read_parquet("data/processed/audit_frame.parquet")
folds = make_folds(d, "spatial", k=10, seed=mc["seed"], km=mc["spatial_block_km"])
TGT = {"bldg": "r2026a_bldg450", "poi": "r2026a_poi"}


def nb_flags(target, alpha=0.10):
    feats = ["log_hu", "log_pop", "log_land_km2", "log_hu_density", "log_struct_equiv", "log_jobs", "sh_u_mobile", "sh_u50p",
             "vacant_share", "sh_yb2010", "sh_yb2020p"]
    X = sm.add_constant(d[feats].fillna(0).astype(float).values); y = d[target].values
    mu = np.empty(len(d))
    for f in np.unique(folds):
        tr, te = folds != f, folds == f
        m = sm.GLM(y[tr], X[tr], family=sm.families.NegativeBinomial(alpha=0.5)).fit()
        mu[te] = m.predict(X[te])
    s = np.log1p(mu) - np.log1p(y)  # one-sided score: how far below expectation
    lower = np.empty(len(d))
    for f in np.unique(folds):
        cal = np.sort(s[folds != f]); m = len(cal)
        lower[folds == f] = np.log1p(mu[folds == f]) - cal[min(m - 1, int(np.ceil((1 - alpha / 2) * (m + 1))) - 1)]
    return np.log1p(y) < lower


variants = {}
for layer, t in TGT.items():
    variants[("primary", layer)] = d[f"{layer}_flag"].values
    feats = [c for c in STRUCTURAL if c not in HOUSING_TYPE_COLS]
    variants[("no housing-type covariates", layer)] = crossfit_cqr(d, t, feats, folds, mc["alpha"], mc["lgbm"], mc["seed"]).flag.values
    variants[("negative-binomial GLM", layer)] = nb_flags(t)
    variants[("80% range", layer)] = crossfit_cqr(d, t, STRUCTURAL, folds, 0.20, mc["lgbm"], mc["seed"]).flag.values
    variants[("95% range", layer)] = crossfit_cqr(d, t, STRUCTURAL, folds, 0.05, mc["lgbm"], mc["seed"]).flag.values
    variants[("Mondrian (region) calibration", layer)] = crossfit_cqr(d, t, STRUCTURAL, folds, mc["alpha"], mc["lgbm"], mc["seed"], mondrian=d.region).flag.values
variants[("reference gap (USA Structures <80%)", "bldg")] = d.ref_gap_b.fillna(False).values
variants[("reference gap (ZBP)", "poi")] = d.ref_gap_p.fillna(False).values

rows = []
for (name, layer), fl in variants.items():
    x = d.copy(); x["f"] = fl.astype(float)
    sub = {"all tracts": x, "excluding HU<50": x[x.hu >= 50]}
    for sname, xx in sub.items():
        if sname != "all tracts" and name != "primary":
            continue
        for grp in ["svi", "cvi", "rural", "tribal"]:
            r = flag_contrast(xx, "f", grp, n_boot=500, seed=mc["seed"])
            rows.append({"variant": name if sname == "all tracts" else f"primary, {sname}", "layer": layer, "flag_rate": xx.f.mean(), **r})
rb = pd.DataFrame(rows)
rb.to_csv("outputs/tables/robustness.csv", index=False)
print(rb[["variant", "layer", "group", "flag_rate", "rate_hi", "rate_lo", "risk_diff", "rd_ci_lo", "rd_ci_hi", "adj_odds_ratio", "p"]].round(3).to_string())
