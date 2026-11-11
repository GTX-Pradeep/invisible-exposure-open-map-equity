"""Write paper/numbers_merged.tex, paper/tab_baselines.tex and paper/tab_hazard_robust.tex from the N1-N5 outputs
(scripts/11_merged_exploratory.py). Separate from 10_paper_numbers.py so the frozen numbers.tex is never touched."""
import json

import numpy as np
import pandas as pd

T = "outputs/tables/merged"; OUT = "paper"
M = {}
pc = lambda x, d=1: f"{100 * x:.{d}f}\\%"
f2 = lambda x: f"{x:.2f}"
ci = lambda a, b, fmt=f2: f"[{fmt(a)}, {fmt(b)}]"
J = json.load(open(f"{T}/merged.json"))

# ---- N1: regressed tracts
n1 = pd.read_csv(f"{T}/n1_regressed_profile.csv")
g = lambda y, c, cl="county": n1[(n1.measure == y) & (n1.comparison == c) & (n1.bootstrap_cluster == cl)].iloc[0]
S = "other South-Central TX tracts"
M["MgRegTracts"] = f"{J['N1']['n_regressed']:,}"; M["MgRegBexar"] = f"{J['N1']['n_regressed_bexar']:,}"
M["MgRegMsftPooled"] = pc(J["N1"]["regressed_msft_share_pooled"])
M["MgRegMsftMean"] = pc(g("msft_share", S).mean_regressed); M["MgSctxMsftMean"] = pc(g("msft_share", S).mean_comparison)
M["MgRegDom"] = pc(g("msft_dom", S).mean_regressed, 0); M["MgSctxDom"] = pc(g("msft_dom", S).mean_comparison, 0)
M["MgRegDomDiff"] = f"{100 * g('msft_dom', S)['diff']:.0f}"
M["MgRegDomCICounty"] = ci(100 * g("msft_dom", S).ci_lo, 100 * g("msft_dom", S).ci_hi, lambda x: f"{x:.0f}")
M["MgRegDomCITract"] = ci(100 * g("msft_dom", S, "GEOID").ci_lo, 100 * g("msft_dom", S, "GEOID").ci_hi, lambda x: f"{x:.0f}")
M["MgRegClass"] = pc(g("class_share", S).mean_regressed); M["MgSctxClass"] = pc(g("class_share", S).mean_comparison)
M["MgRegSpearman"] = f2(J["N1"]["spearman_loss_vs_msft_share_regressed"])
M["MgRegLossLeMsft"] = pc(J["N1"]["share_regressed_where_loss_le_msft_count"], 0)

# ---- semantic blindspot and N4 (Microsoft-dominant = >= 90% of 2026-08 buildings from Microsoft)
r = pd.read_csv("deliverables/dataset/invisible_exposure_tract_results.csv", dtype={"GEOID": str})
m = pd.read_csv("data/external/merged_inputs.csv", dtype={"GEOID": str})
d = r.merge(m, on="GEOID")
dom = d.r2026a_src_msft / d.r2026a_bldg.clip(lower=1) >= 0.90
M["MgDomTracts"] = f"{int(dom.sum()):,}"; M["MgDomTractShare"] = pc(dom.mean(), 0)
M["MgDomPop"] = f"{d.loc[dom, 'pop'].sum() / 1e6:.2f}"
M["MgDomLabel"] = pc(d.loc[dom, "mec_bldg_n_class"].sum() / d.loc[dom, "mec_bldg_n"].sum())
M["MgOtherLabel"] = pc(d.loc[~dom, "mec_bldg_n_class"].sum() / d.loc[~dom, "mec_bldg_n"].sum())
M["MgDomHeight"] = pc(d.loc[dom, "mec_bldg_n_height"].sum() / d.loc[dom, "mec_bldg_n"].sum(), 0)
M["MgOtherHeight"] = pc(d.loc[~dom, "mec_bldg_n_height"].sum() / d.loc[~dom, "mec_bldg_n"].sum(), 0)
M["MgDomRural"] = pc((d.loc[dom, "rural"] == "rural").mean(), 0); M["MgOtherRural"] = pc((d.loc[~dom, "rural"] == "rural").mean(), 0)
M["MgDomTribal"] = pc((d.loc[dom, "tribal"] == "tribal").mean(), 0); M["MgOtherTribal"] = pc((d.loc[~dom, "tribal"] == "tribal").mean(), 0)
bd = pd.read_csv(f"{T}/n4_by_msft_dominance.csv").set_index("msft_dom")
M["MgDomGap"] = pc(bd.loc[True, "ref_gap_rate"]); M["MgOtherGap"] = pc(bd.loc[False, "ref_gap_rate"])
n4 = J["N4"]; det = n4["detector"]
M["MgClassAUC"] = f2(det["roc_auc"]); M["MgClassAUCCI"] = ci(*det["roc_auc_ci"])
M["MgClassOR"] = f"{n4['class_share_or_per_unit']:.1f}"; M["MgClassORCI"] = ci(*n4["ci"], lambda x: f"{x:.1f}")
fam = pd.read_csv(f"{T}/n_family_fdr.csv")
M["MgClassPbh"] = f2(fam[fam.test == "class_share coefficient"].p_bh.iloc[0])
M["MgNFam"] = f"{len(fam)}"

# ---- N3 baselines
b = pd.read_csv(f"{T}/n3_baselines.csv").set_index("method")
pp = pd.read_csv(f"{T}/n3_paired.csv")
M["MgBudget"] = f"{J['N3']['budget']:,}"
M["MgLiftIF"] = f"{b.loc['Isolation Forest (experiments)', 'lift']:.1f}"
M["MgLiftNB"] = f"{b.loc['NB shortfall (experiments)', 'lift']:.1f}"
M["MgLiftRatio"] = f"{b.loc['map/housing ratio (IE)', 'lift']:.1f}"
M["MgLiftMin"] = f"{b.drop(index='random flags (1,000 draws)').lift.min():.1f}"
M["MgLiftMax"] = f"{b.drop(index='random flags (1,000 draws)').lift.max():.1f}"
x = pp[(pp.minus == "conformal model (IE)") & (pp.method == "XGB shortfall (experiments)") & (pp.metric == "roc_auc")].iloc[0]
M["MgXgbAucDiff"] = f"{x['diff']:+.2f}"; M["MgXgbAucDiffCI"] = ci(x.ci_lo, x.ci_hi)
x = pp[(pp.minus == "conformal model (IE)") & (pp.method == "map/housing ratio (IE)") & (pp.metric == "roc_auc")].iloc[0]
M["MgRatioAucDiff"] = f"{x['diff']:+.2f}"; M["MgRatioAucDiffCI"] = ci(x.ci_lo, x.ci_hi)
g5 = J["N5_ranking"]["G_minus_E"]
M["MgGERecall"] = f"{g5['recall'][0]:.3f}"; M["MgGERecallCI"] = ci(g5["recall"][1], g5["recall"][2], lambda v: f"{v:.3f}")

names = {"conformal model (IE)": "Conformal model (this paper)", "Isolation Forest (experiments)": "Isolation Forest on log counts",
         "NB shortfall (experiments)": "NB GLM shortfall", "map/housing ratio (IE)": "Map/housing ratio",
         "XGB shortfall (experiments)": "XGBoost shortfall", "OLS log-HU (IE)": "OLS on housing units and area",
         "XGB model E: structure+rural+region (project)": "XGBoost, structure + rural + region",
         "XGB model G: E + neighbour density (project)": "\\quad + neighbours' building density",
         "random flags (1,000 draws)": "Random flags (1,000 draws)"}
rows = ["\\begin{tabular}{lrrrrr}\\toprule", "Method & Precision & Recall & Lift & ROC-AUC & PR-AUC\\\\\\midrule"]
for k, lab in names.items():
    z = b.loc[k]
    rows.append(f"{lab} & {z.precision:.3f} & {z.recall:.3f} & {z.lift:.2f} & {z.auc:.3f} & {z.pr_auc:.3f}\\\\")
rows += ["\\bottomrule\\end{tabular}"]
open(f"{OUT}/tab_baselines.tex", "w").write("\n".join(rows) + "\n")

# ---- N2 hazard robustness
h = pd.read_csv(f"{T}/n2_hazard_robustness.csv"); v = pd.read_csv(f"{T}/n2_verdicts.csv")
hv = lambda hz, gr, var: h[(h.hazard == hz) & (h.group == gr) & h.variant.str.startswith(var)].iloc[0]
w = hv("drought", "rural", "primary, terciles within region")
M["MgDroughtWithin"] = f2(w.rate_ratio); M["MgDroughtWithinCI"] = ci(w.ci_lo, w.ci_hi)
wf = h[(h.hazard == "wildfire") & (h.group == "rural")]
M["MgWildMin"] = f2(wf.rate_ratio.min()); M["MgWildMax"] = f2(wf.rate_ratio.max())
lab = {"primary (H5, pooled terciles)": "H5 primary", "primary, terciles within region": "Within-region terciles",
       "primary, Mantel-Haenszel over regions": "Mantel--Haenszel"}
keep = v[v.verdict != "primary not significant"]
rows = ["\\begin{tabular}{llll}\\toprule", "Hazard $\\times$ group & Variant & RR [95\\% CI] & Verdict\\\\\\midrule"]
for it in keep.itertuples():
    sub = h[(h.hazard == it.hazard) & (h.group == it.group)]
    for j, z in enumerate(sub.itertuples()):
        name = lab.get(z.variant, z.variant.replace("alternative: ", "Alt.: ").replace("_", "\\_"))
        rr = f"{z.rate_ratio:.2f} [{z.ci_lo:.2f}, {z.ci_hi:.2f}]"
        first = (it.hazard + " $\\times$ " + it.group) if j == 0 else ""
        verdict = it.verdict if j == 0 else ""
        rows.append(f"{first} & {name} & {rr} & {verdict}" + "\\\\")
    rows.append("\\addlinespace")
rows += ["\\bottomrule\\end{tabular}"]
open(f"{OUT}/tab_hazard_robust.tex", "w").write("\n".join(rows) + "\n")

# ---- roads and facilities: re-estimated from this repository's data (scripts/16_relative_rmse.py)
rr = pd.read_csv("outputs/tables/review/relative_rmse_repo.csv")
best = lambda comp: rr[(rr.component == comp) & (rr.design == "spatial") & (rr.model != "constant")].relative_rmse.min()
M["MgRrmseHwy"] = f2(best("highway")); M["MgRrmseFire"] = f2(best("fire")); M["MgRrmseEms"] = f2(best("ems"))
M["MgRrmseBldg"] = f2(best("buildings"))
rat = pd.read_csv("outputs/tables/review/highway_loro_repo.csv").set_index("region").predicted_over_observed
M["MgHwyLoroAz"] = f2(rat["maricopa-az"]); M["MgHwyLoroTx"] = f2(rat["south-central-tx"])

# ---- data checks (eda/) and model checks (modelling/): reproducibility and limitations
from pathlib import Path
rp = pd.read_csv("eda/tables/03_reproducibility.csv")
M["MgReproCols"] = f"{int((rp.identical == 1).sum())}"; M["MgReproColsTotal"] = f"{len(rp)}"
ua = pd.read_csv("eda/tables/03_unassigned_places.csv")
M["MgBoundaryPlaces"] = f"{int(ua.of_which_on_a_boundary.sum())}"
tm = pd.read_csv("deliverables/dataset/tracts_model_table.csv", usecols=["ref_img_min", "ref_img_max"])
M["MgImgFirst"] = str(tm.ref_img_min.dropna().min())[:4]; M["MgImgLast"] = str(tm.ref_img_max.dropna().max())[:4]
gr = pd.read_csv("modelling/tables/01_settings_grid.csv").set_index("variant")
seed = gr[gr.setting == "randomness"].flag_overlap_jaccard.mean()
M["MgSeedOverlap"] = f2(seed); M["MgSeedChanged"] = pc(1 - seed, 0)
M["MgNVariants"] = f"{len(gr)}"
oth = gr[~gr.setting.isin(["-", "randomness", "inputs"])]
M["MgSettingsOverlapMin"] = f2(oth.flag_overlap_jaccard.min()); M["MgSettingsOverlapMax"] = f2(oth.flag_overlap_jaccard.max())
M["MgCovMin"] = pc(gr.coverage.min()); M["MgCovMax"] = pc(gr.coverage.max())
M["MgRTwoPrim"] = f"{gr.loc['primary (published)', 'r2_log']:.3f}"
M["MgRTwoNoHt"] = f"{gr.loc['no housing-type inputs', 'r2_log']:.3f}"; M["MgLiftNoHt"] = f"{gr.loc['no housing-type inputs', 'lift']:.1f}"
M["MgOverlapNoHt"] = f2(gr.loc["no housing-type inputs", "flag_overlap_jaccard"])
cal = pd.read_csv("modelling/tables/02_calibration_by_decile.csv")
sz = cal[cal.iloc[:, 0] == "expected-size decile"].set_index(cal.columns[1]).flag_rate
M["MgFlagSmallDecile"] = pc(sz.iloc[0], 0); M["MgFlagLargeDecile"] = pc(sz.iloc[-1], 0)
oof = Path("modelling/tables/oof_bldg_primary.parquet")
if oof.exists():
    o = pd.read_parquet(oof).merge(pd.read_csv("deliverables/dataset/invisible_exposure_tract_results.csv", dtype={"GEOID": str},
                                   usecols=["GEOID", "region", "bldg_flag"]), on="GEOID")
    wa = o[o.region == "eastern-wa"]
    M["MgWaFlag"] = pc(wa.flag.mean()); M["MgWaAbove"] = pc((wa.y_log > wa.upper_log).mean(), 0)
    M["MgReproFlags"] = f"{int((o.flag == o.bldg_flag).sum()):,}"; M["MgReproFlagsTotal"] = f"{len(o):,}"
ac = pd.read_csv("eda/tables/03_assignment_completeness.csv")
for lay, k in [("buildings", "Bldg"), ("places", "Poi")]:
    a = ac[ac.layer == lay]
    M[f"MgUnassigned{k}"] = f"{int(a.unassigned.sum()):,}"; M[f"MgRaw{k}"] = f"{int(a.raw_features.sum()):,}"
gq = pd.read_csv("deliverables/dataset/tracts_model_table.csv", usecols=["pop", "gq_pop"])
M["MgGqTracts"] = f"{int((gq.gq_pop > 0.5 * gq['pop']).sum())}"
mo = pd.read_csv("modelling/tables/02_moran.csv").set_index("region")["building residual"]
M["MgMoranMin"] = f2(mo.min()); M["MgMoranMax"] = f2(mo.max())

with open(f"{OUT}/numbers_merged.tex", "w") as f:
    f.write("% generated by scripts/12_merged_numbers.py -- do not edit\n")
    for k, val in M.items():
        f.write(f"\\newcommand{{\\{k}}}{{{val}}}\n")
print(len(M), "macros"); print("\n".join(f"{k} = {v}" for k, v in M.items()))
