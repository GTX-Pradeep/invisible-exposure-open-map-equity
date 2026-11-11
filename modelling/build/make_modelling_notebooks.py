"""Generates modelling/01_model_settings.ipynb (build step 7) and modelling/02_residual_diagnostics.ipynb (step 8).
Inputs: modelling/tables/01_settings_grid.csv and oof_*_primary.parquet from run_settings_grid.py, plus
data/processed/tracts_all.parquet. Takeaways: modelling/build/takeaways.json. Run from the repo root."""
import json, sys
import nbformat as nbf

T = {} if "draft" in sys.argv else json.load(open("modelling/build/takeaways.json"))
SETUP = '''import warnings, os, json
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path.cwd().parent if Path.cwd().name in ("modelling", "notebooks", "eda") else Path.cwd()
os.chdir(ROOT)
import numpy as np, pandas as pd, matplotlib.pyplot as plt, yaml
pd.set_option("display.width", 170); pd.set_option("display.max_columns", 30); pd.set_option("display.precision", 3)
plt.rcParams.update({"figure.dpi": 100, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})
REG = ["maricopa-az", "northern-ca", "eastern-ok", "south-central-tx", "eastern-wa"]
COL = dict(zip(REG, ["#e07b39", "#c0504d", "#6a9e4f", "#3b6fb6", "#8e6bbf"]))
TAB, FIG = Path("modelling/tables"), Path("modelling/figures"); FIG.mkdir(parents=True, exist_ok=True)
def save(name):
    plt.tight_layout(); plt.savefig(FIG / f"{name}.png", dpi=130, bbox_inches="tight"); plt.show()
cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
df = pd.read_parquet("data/processed/tracts_all.parquet")'''


def build(path, title, intro, sections, summary_key):
    C = [nbf.v4.new_markdown_cell(f"# {title}\n\n{intro}"), nbf.v4.new_code_cell(SETUP)]
    for k, h, code in sections:
        C += [nbf.v4.new_markdown_cell(h), nbf.v4.new_code_cell(code)]
        if k in T: C.append(nbf.v4.new_markdown_cell("**Takeaway.** " + T[k]))
    if summary_key in T: C += [nbf.v4.new_markdown_cell("## Summary"), nbf.v4.new_markdown_cell(T[summary_key])]
    nb = nbf.v4.new_notebook(); nb["cells"] = C; nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nbf.write(nb, path); print("wrote", path, len(C), "cells")


build("modelling/01_model_settings.ipynb", "01 · Model settings: where they come from and how much they matter",
      "Build step 7. The expectation model's settings live in `config/config.yaml`. Some were fixed by the pre-registration, "
      "the LightGBM ones were chosen once and never documented. This notebook records the origin of each, confirms that the "
      "published model is reproduced exactly from the data on disk, and measures how coverage, fit and the flagged tracts "
      "change when each setting is varied on its own (buildings, the primary layer). It is a post-hoc sensitivity analysis: "
      "the primary specification is not changed by it, and no audit variable is used. The refits are done by "
      "`modelling/build/run_settings_grid.py` (about 30 minutes); this notebook only reads its results.", [
("origin", "## 1. Where each setting comes from", '''import sys; sys.path.insert(0, "src")
from coverage_risk.model import STRUCTURAL
rows = [("target", "log(1 + count) of buildings >= 450 sq ft, and of places", "matches the USA Structures threshold; log because counts are skewed (eda/04)"),
        ("inputs", f"{len(STRUCTURAL)} structural columns (coverage_risk.model.STRUCTURAL)", "ACS housing and population, land, LODES jobs; audit, reference and outcome columns refused by assert_no_leakage"),
        ("model", "LightGBM quantile regression at 0.05, 0.5, 0.95", "nonlinear, handles skew and collinearity (eda/04); quantiles give the range directly"),
        ("alpha", f"{mc['alpha']} (90% range)", "pre-registered; 80% and 95% are pre-registered robustness checks"),
        ("calibration", "CQR, global", "pre-registered primary; within-region (Mondrian) is a pre-registered robustness check"),
        ("cross-fitting", f"10 folds of {mc['spatial_block_km']} km spatial blocks", "pre-registered; checked against residual autocorrelation in 02"),
        ("seed", str(mc["seed"]), "fixed for reproducibility"),
        ("LightGBM", ", ".join(f"{k}={v}" for k, v in mc["lgbm"].items()), "chosen once, not tuned and not documented before this notebook; checked in section 3")]
display(pd.DataFrame(rows, columns=["setting", "value", "origin / reason"]).set_index("setting"))'''),
("repro", "## 2. Is the published model reproduced from the data on disk?", '''g = pd.read_csv(TAB / "01_settings_grid.csv")
oof = pd.read_parquet(TAB / "oof_bldg_primary.parquet")
pub = pd.read_csv("deliverables/dataset/invisible_exposure_tract_results.csv", dtype={"GEOID": str})
m = pub.merge(oof, on="GEOID")
rep = pd.Series({"tracts compared": len(m), "max relative difference, expected count": (np.abs(m.bldg_expected - m.expected) / m.bldg_expected.clip(lower=1)).max(),
                 "max difference, lower bound": np.abs(m.bldg_lower - m.lower).max(), "flags identical": (m.bldg_flag == m.flag).mean(),
                 "flagged tracts": int(m.flag.sum()), "published summary": json.load(open("outputs/tables/phase3_summary.json"))["bldg"]["n_flag"]})
display(rep.to_frame("value"))'''),
("grid", "## 3. Sensitivity: one setting at a time", '''show = ["variant", "setting", "coverage", "cov_region_min", "cov_region_max", "n_flag", "r2_log", "mae_log", "width_log", "precision", "recall", "lift", "pr_auc", "flag_overlap_jaccard", "deficit_spearman_vs_primary"]
fmt = {c: "{:.3f}" for c in show[2:]} | {"n_flag": "{:,.0f}"}
display(g[show].style.format(fmt).background_gradient(subset=["flag_overlap_jaccard"], cmap="RdYlGn", vmin=0, vmax=1))
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6), sharey=True)
yy = np.arange(len(g))[::-1]
for a, c, ref, lab in [(ax[0], "coverage", .90, "coverage of 90% range"), (ax[1], "lift", g.lift[0], "lift vs USA Structures gaps"), (ax[2], "flag_overlap_jaccard", 1, "overlap of flagged tracts with primary (Jaccard)")]:
    a.barh(yy, g[c], color=["#3b6fb6" if s != "-" else "#e07b39" for s in g.setting]); a.axvline(ref, color="k", ls="--", lw=.8); a.set_title(lab, fontsize=10)
ax[0].set_yticks(yy); ax[0].set_yticklabels(g.variant, fontsize=8); ax[0].set_xlim(.8, .95)
save("01_settings_sensitivity")'''),
("seedfloor", "## 4. How much changes from randomness alone?", '''seeds = g[g.setting.isin(["-", "randomness"])]
floor = g.loc[g.setting == "randomness", "flag_overlap_jaccard"].mean()
others = g[~g.setting.isin(["-", "randomness"])].assign(beyond_seed_noise=lambda x: x.flag_overlap_jaccard < floor - 0.05)
print(f"flag overlap between seeds (same settings): {floor:.2f}")
display(others[["variant", "setting", "flag_overlap_jaccard", "lift", "coverage", "beyond_seed_noise"]].style.format({"flag_overlap_jaccard": "{:.2f}", "lift": "{:.2f}", "coverage": "{:.3f}"}))'''),
], "01_summary")

build("modelling/02_residual_diagnostics.ipynb", "02 · Residual diagnostics",
      "Build step 8. Out-of-fold residuals of the primary building model, r = log(1 + observed) − predicted median "
      "(positive = more buildings than expected), plus the place model where useful. Are the errors well behaved, is the "
      "90% range calibrated across tract types, do errors drift with any input, and do they cluster in space? The last "
      "question matters twice: clustered errors break the independence that random cross-validation assumes, and the "
      "distance at which they stop being correlated tells whether 50 km blocks are large enough. No audit variable is used.", [
("dist", "## 1. Residual distribution", '''o = pd.read_parquet(TAB / "oof_bldg_primary.parquet").merge(df[["GEOID", "region", "county", "lat", "lon", "hu", "pop", "land_km2", "jobs", "gq_pop", "sh_u_mobile", "vacant_share", "hu_density", "ref_bldg", "r2026a_bldg450"]], on="GEOID")
o["r"] = o.y_log - o.q_med
o["region"] = pd.Categorical(o.region, REG, ordered=True)
d = o.groupby("region", observed=True).r.agg(["mean", "median", "std", "skew", lambda x: (x.abs() > .5).mean(), lambda x: (x < -np.log(2)).mean()])
d.columns = ["mean", "median", "sd", "skew", "share |r| > 0.5", "share below half of expected"]
d.loc["all"] = [o.r.mean(), o.r.median(), o.r.std(), o.r.skew(), (o.r.abs() > .5).mean(), (o.r < -np.log(2)).mean()]
d.to_csv(TAB / "02_residual_summary.csv"); display(d)
fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
for rg in REG:
    ax[0].hist(o.loc[o.region == rg, "r"].clip(-2, 2), bins=80, histtype="step", lw=1.3, color=COL[rg], label=rg, density=True)
ax[0].set_xlabel("residual (log points); negative = fewer buildings than expected"); ax[0].legend(fontsize=7)
from scipy import stats
qq = stats.probplot(o.r, dist="norm"); ax[1].scatter(qq[0][0], qq[0][1], s=2, color="#3b6fb6"); ax[1].plot(qq[0][0], qq[1][0] * qq[0][0] + qq[1][1], "k--", lw=.8)
ax[1].set_xlabel("normal quantile"); ax[1].set_ylabel("residual quantile"); ax[1].set_title("normal Q-Q", fontsize=10)
save("02_residual_distribution")'''),
("calib", "## 2. Is the 90% range calibrated across tract types?", '''o["size_decile"] = pd.qcut(o.expected, 10, labels=False) + 1
o["land_decile"] = pd.qcut(o.land_km2.rank(method="first"), 10, labels=False) + 1
cal = pd.concat({"expected-size decile": o.groupby("size_decile").agg(coverage=("covered", "mean"), flag_rate=("flag", "mean"), n=("r", "size")),
                 "land-area decile": o.groupby("land_decile").agg(coverage=("covered", "mean"), flag_rate=("flag", "mean"), n=("r", "size"))})
cal.to_csv(TAB / "02_calibration_by_decile.csv")
reg = o.groupby("region", observed=True).agg(coverage=("covered", "mean"), flag_rate=("flag", "mean"), above_upper=("y_log", lambda s: (s > o.loc[s.index, "upper_log"]).mean()))
display(reg.style.format("{:.3f}"))
fig, ax = plt.subplots(1, 2, figsize=(13, 3.6))
for a, k, lab in [(ax[0], "expected-size decile", "decile of expected building count (1 = smallest)"), (ax[1], "land-area decile", "decile of land area (1 = smallest)")]:
    c = cal.loc[k]; a.plot(c.index, c.coverage, "o-", color="#3b6fb6", label="coverage"); a.plot(c.index, c.flag_rate * 5 + .4, "s--", color="#e07b39", label="flag rate (×5, +0.4)")
    a.axhline(.9, color="k", lw=.8); a.axhline(.05 * 5 + .4, color="#e07b39", lw=.6, ls=":"); a.set_xlabel(lab); a.set_ylim(.4, 1); a.legend(fontsize=7)
save("02_calibration")
print("flag rate by expected-size decile:", cal.loc["expected-size decile", "flag_rate"].round(3).tolist())'''),
("drift", "## 3. Do the errors drift with any input?", '''X = {"log10 housing units": np.log10(o.hu + 1), "log10 land km²": np.log10(o.land_km2 + .01), "log10 housing per km²": np.log10(o.hu_density.fillna(0) + .1),
     "mobile-home share": o.sh_u_mobile, "group-quarters share": o.gq_pop / o["pop"].replace(0, np.nan), "vacancy share": o.vacant_share, "log10 jobs": np.log10(o.jobs + 1)}
fig, axs = plt.subplots(1, len(X), figsize=(22, 3.3), sharey=True); rows = []
for a, (k, v) in zip(axs, X.items()):
    b = pd.qcut(v.rank(method="first"), 10, labels=False)
    s = o.r.groupby(b).agg(["mean", "sem"]); x = v.groupby(b).median()
    a.errorbar(x, s["mean"], yerr=1.96 * s["sem"], fmt="o-", ms=3, color="#3b6fb6"); a.axhline(0, color="k", lw=.8); a.set_title(k, fontsize=9)
    rows.append({"input": k, "lowest-decile mean residual": s["mean"].iloc[0], "highest-decile mean residual": s["mean"].iloc[-1], "range of decile means": s["mean"].max() - s["mean"].min()})
axs[0].set_ylabel("mean residual (log points)"); save("02_residual_drift")
dr = pd.DataFrame(rows).set_index("input"); dr.to_csv(TAB / "02_residual_drift.csv"); display(dr)'''),
("moran", "## 4. Do errors cluster in space? (Moran's I, 8 nearest tracts within region)", '''from sklearn.neighbors import BallTree
rng = np.random.default_rng(0)
def moran(z, nb, perms=199):
    z = (z - z.mean()) / z.std(); obs = (z * z[nb].mean(axis=1)).sum() / (z ** 2).sum()
    null = np.array([(p * p[nb].mean(axis=1)).sum() / (p ** 2).sum() for p in (rng.permutation(z) for _ in range(perms))])
    return obs, (1 + (null >= obs).sum()) / (perms + 1)
poi = pd.read_parquet(TAB / "oof_poi_primary.parquet")[["GEOID", "y_log", "q_med", "flag"]].rename(columns={"y_log": "py", "q_med": "pq", "flag": "pflag"})
o = o.merge(poi, on="GEOID"); o["r_poi"] = o.py - o.pq
rows = []
for rg in REG:
    s = o[o.region == rg].reset_index(drop=True)
    nb = BallTree(np.radians(s[["lat", "lon"]].values), metric="haversine").query(np.radians(s[["lat", "lon"]].values), k=9)[1][:, 1:]
    for lab, v in [("building residual", s.r.values), ("building flag", s.flag.astype(float).values), ("place residual", s.r_poi.values)]:
        i, p = moran(v.astype(float), nb); rows.append({"region": rg, "quantity": lab, "moran_I": i, "perm_p": p})
mi = pd.DataFrame(rows).pivot(index="region", columns="quantity", values="moran_I").reindex(REG)
mi.to_csv(TAB / "02_moran.csv"); display(mi.style.format("{:.3f}"))
print("all permutation p-values:", sorted(set(np.round([r["perm_p"] for r in rows], 3))))'''),
("decay", "## 5. How far does the correlation reach, compared with the 50 km blocks?", '''EDGES = [0, 2, 5, 10, 20, 35, 50, 75, 100, 150, 250]
rows = []
for rg in REG:
    s = o[o.region == rg]; n = len(s)
    i, j = rng.integers(0, n, 400_000), rng.integers(0, n, 400_000); k = i != j; i, j = i[k], j[k]
    la, lo = np.radians(s.lat.values), np.radians(s.lon.values)
    dkm = 6371 * 2 * np.arcsin(np.sqrt(np.sin((la[i] - la[j]) / 2) ** 2 + np.cos(la[i]) * np.cos(la[j]) * np.sin((lo[i] - lo[j]) / 2) ** 2))
    z = ((s.r - s.r.mean()) / s.r.std()).values
    b = pd.cut(dkm, EDGES)
    g = pd.DataFrame({"b": b, "p": z[i] * z[j]}).groupby("b", observed=True).p.agg(["mean", "size"])
    g["region"] = rg; rows.append(g.reset_index())
dc = pd.concat(rows); dc["mid_km"] = dc.b.apply(lambda x: (x.left + x.right) / 2)
dc.to_csv(TAB / "02_distance_decay.csv", index=False)
fig, ax = plt.subplots(figsize=(9, 3.8))
for rg in REG:
    s = dc[(dc.region == rg) & (dc["size"] >= 200)]; ax.plot(s.mid_km, s["mean"], "o-", ms=3, color=COL[rg], label=rg)
ax.axhline(0, color="k", lw=.8); ax.axvline(mc["spatial_block_km"], color="k", ls="--", lw=.8); ax.set_xscale("log")
ax.set_xlabel("distance between two tracts (km, log scale); dashed = block size"); ax.set_ylabel("residual correlation"); ax.legend(fontsize=7)
save("02_distance_decay")
w = dc[dc["size"] >= 200].pivot_table(index="mid_km", columns="region", values="mean")[REG]; display(w.style.format("{:.3f}"))'''),
("maps", "## 6. Where are the residuals?", '''fig, axs = plt.subplots(1, 5, figsize=(22, 4.6))
for a, rg in zip(axs, REG):
    s = o[o.region == rg]; sc = a.scatter(s.lon, s.lat, c=s.r.clip(-1, 1), cmap="RdBu", vmin=-1, vmax=1, s=4)
    a.scatter(s.lon[s.flag], s.lat[s.flag], facecolors="none", edgecolors="k", s=14, lw=.5); a.set_title(rg, fontsize=10); a.set_xticks([]); a.set_yticks([]); a.set_aspect("equal")
plt.colorbar(sc, ax=axs, shrink=.7, label="residual (red = fewer buildings than expected); circles = flagged")
plt.savefig(FIG / "02_residual_maps.png", dpi=130, bbox_inches="tight"); plt.show()'''),
], "02_summary")
