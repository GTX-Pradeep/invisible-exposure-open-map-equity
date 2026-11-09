"""Write paper/numbers.tex (LaTeX macros) and paper/tab_*.tex from result tables, so every number in the
manuscript is generated, not typed."""
import json
import numpy as np
import pandas as pd

T = "outputs/tables"; OUT = "paper"
M = {}
pc = lambda x, d=1: f"{100 * x:.{d}f}\\%"
f2 = lambda x: f"{x:.2f}"
ci = lambda a, b, fmt=f2: f"[{fmt(a)}, {fmt(b)}]"

d = pd.read_parquet("data/processed/catchup_frame.parquet")
M["NTracts"] = f"{len(d):,}"
M["NHU"] = f"{d.hu.sum() / 1e6:.1f}"; M["NPop"] = f"{d['pop'].sum() / 1e6:.1f}"
M["NBldg"] = f"{d.r2026a_bldg.sum() / 1e6:.1f}"; M["NPoi"] = f"{d.r2026a_poi.sum() / 1e6:.1f}"
s = d[d.ref_bldg.notna()]
M["RefCorr"] = f"{np.corrcoef(np.log1p(s.r2026a_bldg450), np.log1p(s.ref_bldg))[0, 1]:.3f}"
M["RefMedRatio"] = f2((s.r2026a_bldg450 / s.ref_bldg).median())
gap = s.r2026a_bldg450 / s.ref_bldg < 0.8
M["RefGapShare"] = pc(gap.mean())
for k, m in [("Rural", s.rural == "rural"), ("Urban", s.rural == "urban"), ("Tribal", s.tribal == "tribal"), ("NonTribal", s.tribal == "non-tribal")]:
    M[f"RefGap{k}"] = pc(gap[m].mean())

p3 = json.load(open(f"{T}/phase3_summary.json"))
M["CovBldg"] = pc(p3["bldg"]["coverage"]); M["CovPoi"] = pc(p3["poi"]["coverage"])
M["FlagBldg"] = f"{p3['bldg']['n_flag']:,}"; M["FlagPoi"] = f"{p3['poi']['n_flag']:,}"
cv = pd.read_csv(f"{T}/cv_schemes.csv")
g = lambda l, sc, ca: cv[(cv.layer == l) & (cv.scheme == sc) & (cv.calibration == ca)].iloc[0]
M["RTwoBldg"] = f2(g("bldg", "spatial", "global").r2_log); M["RTwoPoi"] = f2(g("poi", "spatial", "global").r2_log)
M["CovSpatRegMinBldg"] = pc(g("bldg", "spatial", "global").cov_region_min); M["CovSpatRegMaxBldg"] = pc(g("bldg", "spatial", "global").cov_region_max)
M["CovMondRegMinBldg"] = pc(g("bldg", "spatial", "mondrian-region").cov_region_min); M["CovMondRegMaxBldg"] = pc(g("bldg", "spatial", "mondrian-region").cov_region_max)
M["CovLoroBldg"] = pc(g("bldg", "region", "global").coverage); M["CovLoroMinBldg"] = pc(g("bldg", "region", "global").cov_region_min)

sk = pd.read_csv(f"{T}/flag_skill.csv")
r = lambda l, m: sk[(sk.layer == l) & (sk.method == m)].iloc[0]
M["PrecBldg"] = f2(r("bldg", "conformal model").precision); M["RecBldg"] = f2(r("bldg", "conformal model").recall)
M["PrevBldg"] = pc(r("bldg", "conformal model").prevalence); M["LiftBldg"] = f"{r('bldg', 'conformal model').lift:.1f}"
M["PRAUCBldg"] = f2(r("bldg", "conformal model").pr_auc); M["PRAUCOlsBldg"] = f2(r("bldg", "OLS log-HU").pr_auc)
M["PRAUCRatioBldg"] = f2(r("bldg", "map/housing ratio").pr_auc)
M["PrecPoi"] = f2(r("poi", "conformal model").precision); M["PrevPoi"] = pc(r("poi", "conformal model").prevalence)
dt = pd.read_csv(f"{T}/deletion_test.csv")
dd = lambda l, f: pc(dt[(dt.layer == l) & np.isclose(dt.removed_share, f)].detection_rate.iloc[0], 0)
M["DelThirtyBldg"], M["DelFiftyBldg"], M["DelThirtyPoi"], M["DelFiftyPoi"] = dd("bldg", .3), dd("bldg", .5), dd("poi", .3), dd("poi", .5)
c4 = json.load(open(f"{T}/phase4_continuous.json"))
M["CountyRho"] = f2(c4["county_spearman_poi_vs_cbp"]); M["CountyN"] = str(c4["county_n"])

fdr = pd.read_csv(f"{T}/confirmatory_fdr.csv")
M["NFdrFamily"] = str(len(fdr))
q = lambda **kw: fdr.loc[np.logical_and.reduce([fdr[k] == v for k, v in kw.items()])].iloc[0]
x = q(hyp="H1", layer="poi", group="svi")
M["PoiSviHi"], M["PoiSviLo"], M["PoiSviAor"] = pc(x.rate_hi), pc(x.rate_lo), f2(x.adj_odds_ratio)
for hz, grp, key in [("wildfire", "rural", "HFiveWildRural"), ("drought", "rural", "HFiveDroughtRural"), ("heat", "tribal", "HFiveHeatTribal")]:
    x = q(hyp="H5", hazard_name=hz, group=grp)
    M[key] = f"{x.rate_ratio:.1f}" if x.rate_ratio >= 0.95 else f2(x.rate_ratio)
    M[key + "CI"] = ci(x.ci_lo, x.ci_hi, lambda v: f"{v:.1f}")
he = json.load(open(f"{T}/hidden_exposure_totals.json"))
M["HEAll"] = f"{he['all']['missing_structures_lower']:,.0f}"
h4 = json.load(open(f"{T}/h4_provenance.json"))
b4, p4 = h4[0], h4[1]
M["HFourDprBldg"] = f"{b4['d_pr_auc']:+.3f}"; M["HFourDprBldgCI"] = ci(*b4["d_pr_auc_ci"], lambda v: f"{v:+.3f}")
M["HFourDaucPoi"] = f"{p4['d_roc_auc']:+.3f}"; M["HFourDaucPoiCI"] = ci(*p4["d_roc_auc_ci"], lambda v: f"{v:+.3f}")
dom = pd.read_csv(f"{T}/h4_gap_by_dominant_source.csv").set_index("dominant")
M["GapMsft"], M["GapOsm"] = pc(dom.loc["msft", "gap_rate"]), pc(dom.loc["osm", "gap_rate"])

sn = pd.read_csv(f"{T}/h3_snapshots.csv").set_index("snapshot")
M["GainBldg"] = f"{(sn.loc['r2026b', 'buildings'] - sn.loc['r2023', 'buildings']) / 1e6:.1f}"
sm = pd.read_csv(f"{T}/h3_source_mix.csv", index_col=0)
M["OsmShareA"], M["OsmShareC"] = pc(sm.loc["osm_share", "r2023"], 0), pc(sm.loc["osm_share", "r2026b"], 0)
M["GapShareA"], M["GapShareB"] = pc(sn.loc["r2023", "share_tracts_lt80"]), pc(sn.loc["r2026a", "share_tracts_lt80"])
M["GapRuralA"], M["GapRuralC"] = pc(sn.loc["r2023", "lt80_rural_rural"]), pc(sn.loc["r2026b", "lt80_rural_rural"])
M["GapSviC"] = pc(sn.loc["r2026b", "lt80_svi_Q4"])
h3 = fdr[fdr.hyp == "H3"]
did = lambda grp: h3[(h3.group == grp) & (h3.outcome == "gap_rate_DiD")].iloc[0]
for grp, k in [("rural", "Rural"), ("tribal", "Tribal")]:
    x = did(grp)
    M[f"Did{k}PP"] = f"{abs(x.adj_diff) * 100:.1f}"; M[f"Did{k}CI"] = ci(x.ci_lo * 100, x.ci_hi * 100, lambda v: f"{v:.1f}")
    M[f"Did{k}P"] = f"{x.p_bh:.3f}"
x = h3[(h3.group == "rural") & (h3.outcome == "d_lc")].iloc[0]
M["HThreeRural"] = f"$+${x.adj_diff:.3f} log points, 95\\% CI {x.ci_lo:.3f}--{x.ci_hi:.3f}"; M["HThreeRuralP"] = f"{x.p_bh:.3f}"

ex = json.load(open(f"{T}/exploratory.json"))
e1 = ex["E1"]
M["EOneLost"] = f"{e1['buildings_lost'] / 1e3:,.0f}{{,}}000".replace("{,}000", ",000") if False else f"{round(e1['buildings_lost'], -3):,.0f}"
M["EOneTracts"] = str(e1["tracts_regressed_gt20pct"]); M["EOneBexar"] = str(e1["of_which_bexar"])
M["EOneResidents"] = f"{round(e1['residents'], -3):,.0f}"
M["EOneSviShare"] = pc(e1["share_svi_q4_regressed"], 0); M["EOneSviAll"] = pc(e1["share_svi_q4_all"], 0)
M["EOneFlagAfter"] = pc(e1["flag_rate_after"], 0); M["EOneFlagBefore"] = pc(e1["flag_rate_before"], 1)
M["EOneFlagOther"] = pc(e1["flag_rate_other_tracts_after"], 1); M["EOneRecall"] = pc(e1["recall_of_ref_gaps_in_regressed"], 0)
reg = d.loss_aug_oct > 0.2
M["EOneRefGapAfter"] = pc((d.r2026b_bldg450[reg] / d.ref_bldg[reg] < 0.8).mean(), 0)

e3 = pd.read_csv(f"{T}/e3_h3_sensitivity.csv")
parts = []
for grp in ["rural", "tribal"]:
    for v in e3.variant.unique():
        x = e3[(e3.group == grp) & (e3.variant == v)].iloc[0]
        parts.append(f"{grp} {x.adj_diff:+.3f} ({v}; 95\\% CI {x.ci_lo:.3f}--{x.ci_hi:.3f})")
M["EThreeSummary"] = "; ".join(parts)

e2 = pd.read_csv(f"{T}/e2_normalization.csv"); e2f = e2[e2.analysis == "E2-flags"]
def aor(o, grp):
    x = e2f[(e2f.outcome == o) & (e2f.group == grp)].iloc[0]
    return f"{x.adj_odds_ratio:.2f} [{x.aor_ci_lo:.2f}, {x.aor_ci_hi:.2f}]"
e2c = e2[e2.analysis == "E2"]
def cdiff(o, grp):
    x = e2c[(e2c.outcome == o) & (e2c.group == grp)].iloc[0]
    return f"{x.adj_diff:+.3f} [{x.ci_lo:.3f}, {x.ci_hi:.3f}]"
M["ETwoText"] = (
    f"For rural vs.\\ urban tracts the adjusted odds ratio of a reference gap is {aor('ref_gap_b', 'rural')}, but {aor('bldg_flag', 'rural')} for the "
    f"map-trained flag and {aor('anchored_flag', 'rural')} for the reference-anchored flag; for tribal vs.\\ non-tribal tracts the values are "
    f"{aor('ref_gap_b', 'tribal')}, {aor('bldg_flag', 'tribal')} and {aor('anchored_flag', 'tribal')}. "
    f"\\emph{{Absorption}} is visible in the expectation itself: relative to the reference, observed completeness in rural tracts is lower by "
    f"{cdiff('obs_minus_ref', 'rural')} log points (region FE), and the map-trained expectation is already lower by {cdiff('exp_minus_ref', 'rural')}, "
    f"so it reproduces {pc(ex['E2_absorbed_share_rural'], 0)} of the rural shortfall ({pc(ex['E2_absorbed_share_tribal'], 0)} of the tribal one). "
    f"\\emph{{Resolution}} limits even the reference-anchored model: its tract-level residual SD is {ex['E2_resid_sd_log_anchored']:.2f} log points "
    f"(map-trained: {ex['E2_resid_sd_log_maptrained']:.2f}), against {ex['E2_gap_threshold_log']:.2f} for a 20\\% gap, and it flags only "
    f"{pc(ex['E2_anchored_flag_rate'])} of tracts (precision {ex['E2_anchored_skill']['precision']:.2f}, recall {ex['E2_anchored_skill']['recall']:.2f} "
    f"for reference gaps; map-trained {ex['E2_maptrained_skill_same_tracts']['precision']:.2f} and {ex['E2_maptrained_skill_same_tracts']['recall']:.2f}).")

orig = pd.read_csv(f"{T}/original_prereg_tests.csv")
ot = orig[["hyp", "outcome", "n_a", "n_b", "mean_a", "mean_b", "rank_biserial", "p", "p_bh"]].copy()
ot["hyp"] = ot.hyp.str.replace(" x ", " $\\times$ ").str.replace("->", "$\\to$")
for col in ["mean_a", "mean_b", "rank_biserial", "p", "p_bh"]:
    ot[col] = ot[col].map("{:.3f}".format)
ot["outcome"] = ot.outcome.str.replace("_", "\\_")
OT = ot
M["OrigHOne"] = f"{orig.loc[0, 'mean_a']:.1f} vs.\\ {orig.loc[0, 'mean_b']:.1f}"
M["OrigHOneP"] = f"{orig.loc[0, 'p_bh']:.4f}"

rb = pd.read_csv(f"{T}/robustness.csv")
def rtxt():
    x = rb[~rb.variant.str.startswith("reference gap")].copy()
    x["variant"] = x.variant.str.replace("%", "\\%").str.replace("HU<50", "HU $<$ 50")
    x["sig"] = (x.rd_ci_lo > 0) | (x.rd_ci_hi < 0)
    prim = x[x.variant == "primary"].set_index(["layer", "group"]).sig
    x["changed"] = [s_ != prim.loc[(l, g)] for s_, l, g in zip(x.sig, x.layer, x.group)]
    nspec = x.variant.nunique()
    ch = x[x.changed]
    parts = [f"Across {nspec} specifications (primary; no housing-type covariates; negative-binomial GLM; 80\\% and 95\\% ranges; "
             f"within-region calibration; excluding tracts with fewer than 50 housing units), {len(x) - len(ch)} of {len(x)} flag contrasts keep "
             f"the significance status of the primary analysis."]
    poi_svi = x[(x.layer == "poi") & (x.group == "svi")]
    parts.append(f"The lower POI flag rate in high-SVI tracts holds in every specification (risk difference {poi_svi.risk_diff.max():+.3f} to "
                 f"{poi_svi.risk_diff.min():+.3f}).")
    if len(ch):
        lst = "; ".join(f"{r.variant}, {'building' if r.layer == 'bldg' else 'POI'} {r.group}: RD {r.risk_diff:+.3f} "
                        f"[{r.rd_ci_lo:+.3f}, {r.rd_ci_hi:+.3f}]" for r in ch.itertuples())
        parts.append(f"The exceptions are: {lst}.")
    nh = x[(x.variant == "no housing-type covariates") & (x.layer == "bldg") & (x.group == "svi")].iloc[0]
    if (nh.rd_ci_lo > 0):
        parts.append(f"Most notably, dropping units-in-structure covariates makes building flags significantly more common in high-SVI tracts "
                     f"(aOR {nh.adj_odds_ratio:.2f}), consistent with absorption: mobile-home and multi-unit housing shares, which correlate with SVI, "
                     f"explain away part of the high-SVI shortfall in the primary model.")
    parts.append("Details are in Appendix Table~\\ref{tab:robust}.")
    return " ".join(parts)
M["RobustText"] = rtxt()
M["RobustTextShort"] = M["RobustText"].replace("Details are in Appendix Table~\\ref{tab:robust}.", "Full results are in \\texttt{outputs/tables/robustness.csv}.")

with open(f"{OUT}/numbers.tex", "w") as fh:
    for k, v in M.items():
        assert k.isalpha(), k
        fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

# ------------------------------------------------------------------ tables
def tex_table(df, colfmt, header):
    lines = [f"\\begin{{tabular}}{{{colfmt}}}", "\\toprule", header + " \\\\", "\\midrule"]
    lines += [" & ".join(str(v) for v in row) + " \\\\" for row in df.itertuples(index=False)]
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines)

k = sk[~sk.method.str.contains(r"\|")].copy()
k["layer"] = k.layer.map({"bldg": "Buildings", "poi": "POIs"})
k = k[["layer", "method", "n", "prevalence", "n_flag", "precision", "recall", "lift", "auc", "pr_auc"]]
k["prevalence"] = (k.prevalence * 100).map("{:.1f}\\%".format)
for c in ["precision", "recall", "auc", "pr_auc"]:
    k[c] = k[c].map("{:.3f}".format)
k["lift"] = k.lift.map("{:.1f}".format); k["n"] = k.n.map("{:,}".format)
open(f"{OUT}/tab_skill.tex", "w").write(tex_table(k, "llrrrrrrrr", "Layer & Method & $n$ & Prev. & Flags & Prec. & Recall & Lift & ROC-AUC & PR-AUC"))

GL = {"svi": "SVI Q4 vs Q1", "cvi": "CVI top vs bottom", "rural": "Rural vs urban", "tribal": "Tribal vs non-tribal"}
rows = []
for _, x in fdr.iterrows():
    lay = {"bldg": "Bldg", "poi": "POI"}[x.layer]
    if x.hyp in ("H1", "H2"):
        est = f"RD {x.risk_diff:+.3f} [{x.rd_ci_lo:+.3f}, {x.rd_ci_hi:+.3f}]; aOR {x.adj_odds_ratio:.2f}"
        rates = f"{100 * x.rate_hi:.1f}\\% / {100 * x.rate_lo:.1f}\\%"
        hyp = x.hyp
    elif x.hyp == "H5":
        est = f"RR {x.rate_ratio:.2f} [{x.ci_lo:.2f}, {x.ci_hi:.2f}]"
        rates = f"{x.rate_hi_per1000hu:.2f} / {x.rate_lo_per1000hu:.2f}"
        hyp = f"H5 {x.hazard_name}"
    else:
        sub = "a" if x.outcome == "d_lc" else "b"
        est = f"$\\Delta$ {x.adj_diff:+.3f} [{x.ci_lo:+.3f}, {x.ci_hi:+.3f}]"
        rates = f"{x.mean_hi:.3f} / {x.mean_lo:.3f}" if x.outcome == "d_lc" else "--"
        hyp = f"H3{sub}"
    rows.append([hyp, lay, GL[x.group], rates, est, f"{x.p:.3f}", f"{x.p_bh:.3f}", "\\checkmark" if x.reject_bh else ""])
open(f"{OUT}/tab_confirmatory.tex", "w").write("\\resizebox{\\textwidth}{!}{" + tex_table(pd.DataFrame(rows), "lllllrrc",
    "Hyp. & Layer & Contrast & Group values & Estimate [95\\% CI] & $p$ & $p_{BH}$ & Sig.") + "}")

c = cv[["layer", "scheme", "calibration", "coverage", "flag_rate", "r2_log", "cov_region_min", "cov_region_max"]].copy()
for col in ["coverage", "flag_rate", "cov_region_min", "cov_region_max"]:
    c[col] = (c[col] * 100).map("{:.1f}".format)
c["r2_log"] = c.r2_log.map("{:.3f}".format)
open(f"{OUT}/tab_cv.tex", "w").write(tex_table(c, "lllrrrrr", "Layer & Folds & Calibration & Coverage \\% & Flags \\% & $R^2$ & Region min & Region max"))

e3t = e3[["variant", "group", "mean_hi", "mean_lo", "adj_diff", "ci_lo", "ci_hi", "p"]].copy()
for col in ["mean_hi", "mean_lo", "adj_diff", "ci_lo", "ci_hi", "p"]:
    e3t[col] = e3t[col].map("{:.3f}".format)
open(f"{OUT}/tab_e3.tex", "w").write(tex_table(e3t, "llrrrrrr", "Variant & Group & Mean (hi) & Mean (lo) & Adj. diff. & CI low & CI high & $p$"))

rt = rb[["variant", "layer", "group", "flag_rate", "risk_diff", "rd_ci_lo", "rd_ci_hi", "adj_odds_ratio"]].copy()
rt["flag_rate"] = (rt.flag_rate * 100).map("{:.1f}".format)
for col in ["risk_diff", "rd_ci_lo", "rd_ci_hi"]:
    rt[col] = rt[col].map("{:+.3f}".format)
rt["adj_odds_ratio"] = rt.adj_odds_ratio.map("{:.2f}".format)
rt["variant"] = rt.variant.str.replace("%", "\\%").str.replace("<", "$<$")
lt = ["{\\footnotesize", "\\begin{longtable}{lllrrrrr}",
      "\\caption{Robustness of building and POI flag contrasts (risk difference, cluster-bootstrap 95\\% CI).}\\label{tab:robust}\\\\",
      "\\toprule", "Variant & Layer & Group & Flags \\% & RD & CI low & CI high & aOR \\\\", "\\midrule", "\\endhead"]
lt += [" & ".join(str(v) for v in row) + " \\\\" for row in rt.itertuples(index=False)]
lt += ["\\bottomrule", "\\end{longtable}", "}"]
open(f"{OUT}/tab_robust.tex", "w").write("\n".join(lt))
open(f"{OUT}/tab_original.tex", "w").write("{\\footnotesize\n" + tex_table(OT, "p{4.3cm}lrrrrrrr", "Hypothesis (original wording) & Outcome & $n_a$ & $n_b$ & Mean $a$ & Mean $b$ & $r_{rb}$ & $p$ & $p_{BH}$") + "\n}")
print(f"wrote {len(M)} macros")
