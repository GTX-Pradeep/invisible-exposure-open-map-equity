"""Exploratory R1-R2 (not pre-registered): validate both teams' reference-free scores against an independent reference.

The companion MapEquity pipeline planned to hand-label ~60 tracts to test whether its peer-normalised shortfall finds real
missing buildings (its experiment plan E1/E4/E9). USA Structures (ORNL/FEMA) already gives an independent count for every
study tract, so the same questions can be answered for all tracts at once.

R1  Score validity: Spearman with reference omission (1 - Overture>=450 sq ft / USA Structures, clipped at 0), ROC-AUC and
    PR-AUC for the reference gap (< 80%), and top-20% lift; county-cluster bootstrap 95% CIs.
R2  Group excess: is the rural/tribal over-representation of high scores larger or smaller than the over-representation of
    real gaps?  Ratio of rates with county-cluster bootstrap CIs; and the rural contrast per region.
Inputs: data/processed/audit_frame.parquet (this pipeline), data/external/companion/mapequity_risk.csv (scripts/11b).
Writes outputs/tables/merged/r1_*.csv, r2_*.csv, paper/numbers_reference.tex, paper/tab_refval.tex."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score

OUT_T, OUT_P = "outputs/tables/merged", "paper"
B, SEED = 1000, 20261111
d = pd.read_parquet("data/processed/audit_frame.parquet",
                    columns=["GEOID", "region", "county", "r2026a_bldg450", "ref_bldg", "ref_gap_b", "ur_class", "tribal_any",
                             "bldg_deficit_z", "hu"])
k = pd.read_csv("data/external/companion/mapequity_risk.csv", dtype={"GEOID": str})
d = d.merge(k, on="GEOID", how="inner", validate="one_to_one")
d = d[d.ref_bldg.notna() & (d.ref_bldg >= 10)].reset_index(drop=True)
d["omission"] = (1 - d.r2026a_bldg450 / d.ref_bldg).clip(lower=0)
d["gap"] = d.ref_gap_b.astype(bool)
d["rural"] = d.ur_class.eq("Rural")
d["tribal"] = d.tribal_any.fillna(False).astype(bool)
SCORES = {
    "MapEquity building shortfall (NB, peer-normalised)": d.building_shortfall,
    "MapEquity combined risk score": d.risk_score,
    "MapEquity non-POI risk score": d.non_poi_risk_score,
    "Conformal deficit (this paper)": d.bldg_deficit_z,
    "Raw sparsity (buildings per housing unit)": -np.log((d.r2026a_bldg450 + 1) / (d.hu + 1)),
}
cl = d.county.to_numpy()
uc = np.unique(cl)
idx = {c: np.where(cl == c)[0] for c in uc}
rng = np.random.default_rng(SEED)
draws = [np.concatenate([idx[c] for c in rng.choice(uc, len(uc))]) for _ in range(B)]
prev = d.gap.mean()


def metrics(i, s):
    g, s, om = d.gap.to_numpy()[i], s.to_numpy()[i], d.omission.to_numpy()[i]
    top = s >= np.quantile(s, 0.8)
    return {"spearman": spearmanr(s, om).statistic, "roc_auc": roc_auc_score(g, s), "pr_auc": average_precision_score(g, s),
            "lift_top20": g[top].mean() / g.mean()}


rows = []
full = np.arange(len(d))
for name, s in SCORES.items():
    est = metrics(full, s)
    bs = pd.DataFrame([metrics(i, s) for i in draws])
    for m, v in est.items():
        lo, hi = np.nanpercentile(bs[m], [2.5, 97.5])
        rows.append({"score": name, "metric": m, "estimate": v, "ci_lo": lo, "ci_hi": hi})
r1 = pd.DataFrame(rows)
r1.to_csv(f"{OUT_T}/r1_score_validation.csv", index=False)
w = r1.pivot(index="score", columns="metric", values="estimate").reindex(SCORES)
print(w.round(3).to_string())

# paired difference: MapEquity shortfall minus conformal deficit, ROC-AUC
a, b_ = SCORES["MapEquity building shortfall (NB, peer-normalised)"], SCORES["Conformal deficit (this paper)"]
dd = np.array([roc_auc_score(d.gap.to_numpy()[i], a.to_numpy()[i]) - roc_auc_score(d.gap.to_numpy()[i], b_.to_numpy()[i]) for i in draws])
pair = {"diff": roc_auc_score(d.gap, a) - roc_auc_score(d.gap, b_), "lo": np.percentile(dd, 2.5), "hi": np.percentile(dd, 97.5)}

# R2: group excess of high scores vs of real gaps
d["hi_me"] = d.risk_score >= d.risk_score.quantile(0.8)
d["hi_cf"] = d.bldg_deficit_z >= d.bldg_deficit_z.quantile(0.8)
r2 = []
for grp in ["rural", "tribal"]:
    gv = d[grp].to_numpy()
    for lab, col in [("MapEquity top-20% risk", "hi_me"), ("Conformal top-20% deficit", "hi_cf"), ("Reference gap (<80%)", "gap")]:
        y = d[col].to_numpy().astype(float)
        f = lambda i: y[i][gv[i]].mean() / y[i][~gv[i]].mean()
        bs = np.array([f(i) for i in draws])
        r2.append({"group": grp, "outcome": lab, "ratio": f(full), "ci_lo": np.nanpercentile(bs, 2.5), "ci_hi": np.nanpercentile(bs, 97.5)})
r2 = pd.DataFrame(r2)
r2.to_csv(f"{OUT_T}/r2_group_excess.csv", index=False)
print(r2.round(3).to_string())
fl = pd.read_parquet("data/processed/audit_frame.parquet", columns=["GEOID", "bldg_flag"])
rg = d.merge(fl, on="GEOID").groupby(["region", "rural"]).agg(n=("GEOID", "size"), flag_rate=("bldg_flag", "mean"),
                                                                me_top20=("hi_me", "mean"), ref_gap=("gap", "mean")).reset_index()
rg.to_csv(f"{OUT_T}/r2_region_rural.csv", index=False)
print(rg.round(3).to_string())

# ---- macros and table
pc = lambda x, n=1: f"{100 * x:.{n}f}\\%"
M = {}
key = {"MapEquity building shortfall (NB, peer-normalised)": "Me", "Conformal deficit (this paper)": "Cf", "Raw sparsity (buildings per housing unit)": "Raw",
       "MapEquity combined risk score": "MeRisk"}
for name, tag in key.items():
    for m, mm in [("roc_auc", "Auc"), ("spearman", "Rho"), ("lift_top20", "Lift")]:
        x = r1[(r1.score == name) & (r1.metric == m)].iloc[0]
        M[f"Rv{tag}{mm}"] = f"{x.estimate:.2f}"
        M[f"Rv{tag}{mm}CI"] = f"[{x.ci_lo:.2f}, {x.ci_hi:.2f}]"
M["RvPairDiff"] = f"{pair['diff']:+.3f}"; M["RvPairCI"] = f"[{pair['lo']:+.3f}, {pair['hi']:+.3f}]"
for grp, G in [("rural", "Rural"), ("tribal", "Tribal")]:
    for lab, tag in [("MapEquity top-20% risk", "Me"), ("Conformal top-20% deficit", "Cf"), ("Reference gap (<80%)", "Ref")]:
        x = r2[(r2.group == grp) & (r2.outcome == lab)].iloc[0]
        M[f"Rv{G}{tag}"] = f"{x.ratio:.2f}"; M[f"Rv{G}{tag}CI"] = f"[{x.ci_lo:.2f}, {x.ci_hi:.2f}]"
q = rg.set_index(["region", "rural"])
for reg, R in [("maricopa-az", "Az"), ("eastern-ok", "Ok")]:
    for rr, RR in [(True, "Rur"), (False, "Urb")]:
        M[f"RvFlag{R}{RR}"] = pc(q.loc[(reg, rr), "flag_rate"]); M[f"RvRef{R}{RR}"] = pc(q.loc[(reg, rr), "ref_gap"])
M["RvN"] = f"{len(d):,}"
with open(f"{OUT_P}/numbers_reference.tex", "w") as fh:
    fh.write("% generated by scripts/14_reference_validation.py -- do not edit\n")
    for kk, v in M.items():
        assert kk.isalpha(), kk
        fh.write(f"\\newcommand{{\\{kk}}}{{{v}}}\n")
lines = ["\\begin{tabular}{lcccc}\\toprule", "Score & Spearman (omission) & ROC-AUC & PR-AUC & Top-20\\% lift\\\\\\midrule"]
for name in SCORES:
    x = r1[r1.score == name].set_index("metric")
    cell = lambda m: f"{x.loc[m, 'estimate']:.2f} [{x.loc[m, 'ci_lo']:.2f}, {x.loc[m, 'ci_hi']:.2f}]"
    lines.append(f"{name} & {cell('spearman')} & {cell('roc_auc')} & {cell('pr_auc')} & {cell('lift_top20')}\\\\")
lines.append("\\bottomrule\\end{tabular}")
open(f"{OUT_P}/tab_refval.tex", "w").write("\n".join(lines) + "\n")
print(len(M), "macros written")
