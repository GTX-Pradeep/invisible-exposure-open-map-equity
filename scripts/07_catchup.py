"""Phase 7 (H3): did open-map building coverage catch up in disadvantaged tracts, 2023 -> 2026?
Reference completeness change per tract and re-run expectation models per snapshot."""
import numpy as np
import pandas as pd
import yaml
from coverage_risk.audit import CONTRASTS, boot_p, cluster_sums, continuous_contrast, fast_boot
from coverage_risk.model import STRUCTURAL, crossfit_cqr, make_folds

cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
T = "outputs/tables"; P = "data/processed"
d = pd.read_parquet(f"{P}/audit_frame.parquet")
for r in ["r2023", "r2026b"]:
    d = d.merge(pd.read_parquet(f"{P}/overture_{r}_buildings.parquet")[["GEOID", f"{r}_bldg", f"{r}_bldg450", f"{r}_src_osm", f"{r}_src_msft"]], on="GEOID")
ok = d.ref_bldg.notna() & (d.ref_bldg >= 10)
for r in ["r2023", "r2026a", "r2026b"]:
    d[f"lc_{r}"] = np.log((d[f"{r}_bldg450"] + 1) / (d.ref_bldg + 1))
    d[f"gap_{r}"] = (d[f"{r}_bldg450"] / d.ref_bldg) < 0.8
d["d_lc"] = d.lc_r2026b - d.lc_r2023
d["d_lc_aug_oct"] = d.lc_r2026b - d.lc_r2026a

# snapshot summaries
summ = []
for r in ["r2023", "r2026a", "r2026b"]:
    s = d[ok]
    summ.append({"snapshot": r, "buildings": d[f"{r}_bldg"].sum(), "buildings450": d[f"{r}_bldg450"].sum(),
                 "median_ratio": float(np.exp(s[f"lc_{r}"].median())), "share_tracts_lt80": s[f"gap_{r}"].mean(),
                 **{f"lt80_{g}_{lv}": s.loc[s[g] == lv, f"gap_{r}"].mean() for g, (hi, lo) in CONTRASTS.items() for lv in (hi, lo)}})
summ = pd.DataFrame(summ); summ.to_csv(f"{T}/h3_snapshots.csv", index=False)
print(summ.T.to_string())

rows = []
s = d[ok].copy()
for grp in ["svi", "rural", "tribal", "cvi"]:
    rows.append({"hyp": "H3", "layer": "bldg", **continuous_contrast(s, "d_lc", grp)})
# change in reference-gap rate (2023 -> 2026-10) by group: difference-in-differences with cluster bootstrap
for grp, (hi, lo) in CONTRASTS.items():
    x = s[s[grp].isin([hi, lo])].copy(); x["g"] = (x[grp] == hi).astype(int)
    for k, gv in (("1", 1), ("0", 0)):
        m = (x.g == gv).astype(float)
        x["n" + k], x["a" + k], x["b" + k] = m, m * x.gap_r2023, m * x.gap_r2026b
    agg = cluster_sums(x, ["n1", "a1", "b1", "n0", "a0", "b0"])
    est, lo_, hi_, reps = fast_boot(agg, lambda z: (z["b1"] - z["a1"]) / z["n1"] - (z["b0"] - z["a0"]) / z["n0"], 2000, mc["seed"])
    rows.append({"hyp": "H3", "layer": "bldg", "outcome": "gap_rate_DiD", "group": grp, "contrast": f"{hi} vs {lo}",
                 "n_hi": int(x.g.sum()), "n_lo": int((1 - x.g).sum()), "adj_diff": est, "ci_lo": lo_, "ci_hi": hi_, "p": boot_p(reps)})
h3 = pd.DataFrame(rows); h3.to_csv(f"{T}/h3_raw.csv", index=False)
print(h3.round(4).to_string())

# expectation model re-run on each snapshot (same structural features, same folds)
folds = make_folds(d, "spatial", k=10, seed=mc["seed"], km=mc["spatial_block_km"])
fl = {}
for r in ["r2023", "r2026a", "r2026b"]:
    o = crossfit_cqr(d, f"{r}_bldg450", STRUCTURAL, folds, mc["alpha"], mc["lgbm"], mc["seed"])
    d[f"flag_{r}"] = o.flag.values; d[f"cov_{r}"] = o.covered.values
fr = []
for r in ["r2023", "r2026a", "r2026b"]:
    row = {"snapshot": r, "coverage": d[f"cov_{r}"].mean(), "flag_rate": d[f"flag_{r}"].mean()}
    for g, (hi, lo) in CONTRASTS.items():
        for lv in (hi, lo):
            row[f"flag_{g}_{lv}"] = d.loc[d[g] == lv, f"flag_{r}"].mean()
    fr.append(row)
pd.DataFrame(fr).to_csv(f"{T}/h3_flag_rates_by_snapshot.csv", index=False)
print(pd.DataFrame(fr).T.round(4).to_string())
# source composition change
src = {r: {"osm_share": d[f"{r}_src_osm"].sum() / d[f"{r}_bldg"].sum(), "msft_share": d[f"{r}_src_msft"].sum() / d[f"{r}_bldg"].sum()} for r in ["r2023", "r2026a", "r2026b"]}
pd.DataFrame(src).to_csv(f"{T}/h3_source_mix.csv"); print(src)
d.to_parquet(f"{P}/catchup_frame.parquet", index=False)
