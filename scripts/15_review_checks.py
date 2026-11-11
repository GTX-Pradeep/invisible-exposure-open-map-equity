"""Reproduce, from this repository alone, the evidence behind the review points of 2026-11-11.

usage: python scripts/15_review_checks.py          (run from the repository root)
writes outputs/tables/review/review_checks.csv (one row per number, with its source file) and prints it.

  R1  relative RMSE of roads, fire, EMS and buildings, re-estimated here (scripts/16_relative_rmse.py; run it first),
      with the companion caches' earlier values as a note
  R2  Microsoft footprints as "ground truth": how circular such a check is, and what the independent reference
      (USA Structures) shows, on all tracts (the original 25-tract sample is not stored in this repository)
  R3  why "consistent with H4" is wrong: H4 (provenance improves gap detection) was null
  R4  boundary-assignment loss (dropped as a limitation: too small to matter)
  R5  the other review numbers: reference gaps by rural/tribal, ROC/PR-AUC of the scores,
      one-sided tail rates, and the largest difference in the reproduction check
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

rows = []
def add(check, item, value, source, note=""):
    rows.append({"check": check, "item": item, "value": value, "source": source, "note": note})

res = pd.read_csv("deliverables/dataset/invisible_exposure_tract_results.csv", dtype={"GEOID": str})
tm = pd.read_csv("deliverables/dataset/tracts_model_table.csv", dtype={"GEOID": str},
                 usecols=["GEOID", "r2026a_bldg", "r2026a_src_msft"])
d = res.merge(tm[["GEOID"] + [c for c in tm.columns if c not in res.columns]], on="GEOID")
d = d[d.ref_bldg > 0].copy()
d["ref_gap"] = d.r2026a_bldg450 < 0.8 * d.ref_bldg          # the paper's reference gap
d["msft_share"] = d.r2026a_src_msft / d.r2026a_bldg.where(d.r2026a_bldg > 0)

# ---- R1 relative RMSE (RMSE / SD of the count), best model, spatial folds
# Primary: re-estimated from this repository's data by scripts/16_relative_rmse.py.
# The companion project's caches (no longer kept here) gave 0.47-0.49 / 0.52-0.53 / 0.91-0.92 / 0.99.
rr = Path("outputs/tables/review/relative_rmse_repo.csv")
assert rr.exists(), "run scripts/16_relative_rmse.py first"
rr = pd.read_csv(rr)
for comp in ["buildings", "highway", "fire", "ems"]:
    q = rr[(rr.component == comp) & (rr.design == "spatial") & (rr.model != "constant")].sort_values("relative_rmse").iloc[0]
    add("R1 relative RMSE", f"{comp}: this repo (best={q.model})", round(q.relative_rmse, 3), "outputs/tables/review/relative_rmse_repo.csv",
        "earlier companion caches: " + {"buildings": "0.47-0.49", "highway": "0.52-0.53", "fire": "0.91-0.92", "ems": "0.99"}[comp])
hw = pd.read_csv("outputs/tables/review/highway_loro_repo.csv").set_index("region").predicted_over_observed
add("R1 highway transfer", "predicted/observed km, region held out: Maricopa / south-central TX",
    f"{hw['maricopa-az']:.2f} / {hw['south-central-tx']:.2f}", "outputs/tables/review/highway_loro_repo.csv", "the values the paper now quotes")

# ---- R2 Microsoft as "ground truth": circularity and the independent check, on all tracts
# The 25 sampled tracts are not recorded in this repository, so the check is run on every tract instead:
# a comparison of Overture with Microsoft footprints is mechanical wherever Overture's buildings are Microsoft's own.
add("R2 ground truth", "original 25-tract sample", "not reproducible from this repo",
    "-", "the sampled GEOIDs were never stored here; the all-tract version below needs no sample")
add("R2 ground truth", "median Microsoft share of Overture buildings (all tracts)", round(d.msft_share.median(), 3),
    "deliverables/dataset/tracts_model_table.csv")
bins = pd.cut(d.msft_share, [-0.001, 0.1, 0.5, 0.9, 1.0], labels=["<10%", "10-50%", "50-90%", ">=90%"])
for k, t in d.groupby(bins, observed=True):
    add("R2 ground truth", f"Microsoft share {k}: tracts / real gaps vs USA Structures",
        f"{len(t)} / {int(t.ref_gap.sum())} ({t.ref_gap.mean():.2%})", "deliverables/dataset/invisible_exposure_tract_results.csv",
        "in these tracts a Microsoft-based check compares the map largely with itself" if k in (">=90%", "50-90%") else "")
add("R2 ground truth", "real gaps vs USA Structures, all tracts", f"{int(d.ref_gap.sum())} of {len(d)} ({d.ref_gap.mean():.2%})",
    "deliverables/dataset/invisible_exposure_tract_results.csv", "USA Structures is independent of Overture's sources")

# ---- R3 H4
h4 = json.load(open("outputs/tables/h4_provenance.json"))
h4 = h4[0] if isinstance(h4, list) else h4
add("R3 H4", "change in PR-AUC when provenance is added", round(h4["d_pr_auc"], 4), "outputs/tables/h4_provenance.json",
    f"95% CI {[round(x, 4) for x in h4['d_pr_auc_ci']]} includes 0: H4 is null")
add("R3 H4", "change in ROC-AUC when provenance is added", round(h4["d_roc_auc"], 4), "outputs/tables/h4_provenance.json",
    f"95% CI {[round(x, 4) for x in h4['d_roc_auc_ci']]}")
n4 = pd.read_csv("outputs/tables/merged/n4_by_msft_dominance.csv").set_index("msft_dom")
add("R3 H4", "reference-gap rate, Microsoft-dominant vs other tracts",
    f"{n4.loc[True, 'ref_gap_rate']:.4f} vs {n4.loc[False, 'ref_gap_rate']:.4f}", "outputs/tables/merged/n4_by_msft_dominance.csv",
    "descriptive only; it is not a test of H4, so 'consistent with H4' overstates it")

# ---- R4 boundary loss
ac = pd.read_csv("eda/tables/03_assignment_completeness.csv")
for lay in ["buildings", "places"]:
    a = ac[ac.layer == lay]
    add("R4 boundary", f"{lay} not assigned to a tract", f"{int(a.unassigned.sum())} of {int(a.raw_features.sum()):,}",
        "eda/tables/03_assignment_completeness.csv", f"share {a.unassigned.sum() / a.raw_features.sum():.2e}")

# ---- R5 other review numbers
for c, hi in [("rural", "rural"), ("tribal", "tribal")]:
    r = d.groupby(c).ref_gap.mean()
    lo = [k for k in r.index if k != hi][0]
    add("R5 reference gaps", f"{hi} vs {lo}", f"{r[hi]:.4f} vs {r[lo]:.4f} ({r[hi] / r[lo]:.2f}x)",
        "deliverables/dataset/invisible_exposure_tract_results.csv", f"n = {len(d)} tracts with a reference count")
oof = Path("modelling/tables/oof_bldg_primary.parquet")
o = pd.read_parquet(oof).merge(d[["GEOID", "ref_gap", "r2026a_bldg450"]], on="GEOID")
m = pd.read_csv("data/external/merged_inputs.csv", dtype={"GEOID": str}, usecols=["GEOID", "exp_mu_nb"])
o = o.merge(m, on="GEOID", how="left")
y = o.ref_gap.astype(int)
scores = {"conformal log residual": o.q_med - o.y_log, "conformal deficit z": o.deficit_z,
          "NB shortfall (log)": np.log1p(o.exp_mu_nb) - np.log1p(o.r2026a_bldg450)}
for k, s in scores.items():
    s = s.fillna(s.min())
    add("R5 scores", f"{k}: ROC-AUC / PR-AUC", f"{roc_auc_score(y, s):.3f} / {average_precision_score(y, s):.3f}", str(oof),
        f"gap prevalence {y.mean():.4f}")
add("R5 tails", "share below the 90% range (flag) / above it", f"{(o.y_log < o.lower_log).mean():.4f} / {(o.y_log > o.upper_log).mean():.4f}",
    str(oof), "two-sided interval: the 5% one-sided rate is not guaranteed")
reg = res[["GEOID", "region"]].merge(o, on="GEOID").groupby("region").apply(lambda t: (t.y_log < t.lower_log).mean())
add("R5 tails", "share below the range by region (min-max)", f"{reg.min():.4f}-{reg.max():.4f}", str(oof))
rp = pd.read_csv("eda/tables/03_reproducibility.csv")
add("R5 reproduction", "columns reproduced / largest absolute difference", f"{int(rp.identical.sum())} / {rp.max_abs_diff.max():.1e}",
    "eda/tables/03_reproducibility.csv", "so: reproduces to floating-point precision")

out = Path("outputs/tables/review"); out.mkdir(parents=True, exist_ok=True)
t = pd.DataFrame(rows); t.to_csv(out / "review_checks.csv", index=False)
pd.set_option("display.width", 250, "display.max_colwidth", 70)
print(t[["check", "item", "value", "note"]].to_string(index=False))
