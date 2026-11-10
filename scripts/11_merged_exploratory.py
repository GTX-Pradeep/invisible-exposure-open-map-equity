"""Merged project: exploratory analyses N1-N5 (written 2026-11-10, before these were run; results in docs/merge_results.md).
Not pre-registered; never part of the H1-H5 FDR family.

    python scripts/11_merged_exploratory.py --part n1|n2|n3|n4|n5|fdr|all

Reads only released / imported tract tables, so no data/processed rerun is needed:
    deliverables/dataset/invisible_exposure_tract_results.csv, deliverables/dataset/tracts_model_table.csv,
    data/external/merged_inputs.csv (scripts/11a_import_merged.py)
Writes outputs/tables/merged/ (n*_*.csv, n_family_fdr.csv, merged.json).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score

from coverage_risk.audit import CONTRASTS, _boot_weights, boot_p as _boot_p, bh, cluster_sums, continuous_contrast, exposure_ratio, fast_boot
from coverage_risk.validation import flag_skill

SEED, NB = 20261109, 2000
T = Path("outputs/tables/merged")      # N1-N5 results; the frozen pre-registered tables stay in outputs/tables
T.mkdir(parents=True, exist_ok=True)
J = T / "merged.json"
BEXAR = "48029"


def boot_p(reps, null=0.0):
    """IE's two-sided bootstrap p, capped at 1 (ties at the null, e.g. identical flag sets, can push it above 1)."""
    return min(1.0, _boot_p(reps, null))


def load() -> pd.DataFrame:
    r = pd.read_csv("deliverables/dataset/invisible_exposure_tract_results.csv", dtype={"GEOID": str, "county": str})
    mt = pd.read_csv("deliverables/dataset/tracts_model_table.csv", dtype={"GEOID": str}, usecols=["GEOID", "struct_equiv"])
    m = pd.read_csv("data/external/merged_inputs.csv", dtype={"GEOID": str})
    d = r.merge(mt, on="GEOID", how="left", validate="one_to_one").merge(m, on="GEOID", how="left", validate="one_to_one", indicator=True)
    join = float((d._merge == "both").mean())
    assert join >= 0.99, f"join rate {join:.3f} below the 99% minimum threshold"
    d = d.drop(columns="_merge")
    d["county"] = d.county.str.zfill(5)
    d["truth"] = (d.r2026a_bldg450 / d.ref_bldg) < 0.8          # reference gap (flag_skill.csv definition)
    d["msft_share"] = d.r2026a_src_msft / d.r2026a_bldg.clip(lower=1)
    d["msft_dom"] = (d.msft_share >= 0.90).astype(float)        # MEC definition of Microsoft-dominant
    d["class_share"] = d.mec_bldg_n_class / d.mec_bldg_n.clip(lower=1)
    d["height_share"] = d.mec_bldg_n_height / d.mec_bldg_n.clip(lower=1)
    d["loss"] = (d.r2026a_bldg450 - d.r2026b_bldg450) / d.r2026a_bldg450.clip(lower=1)
    d["regressed"] = d.loss > 0.20                               # E1 definition
    return d, join


def jupdate(**kw):
    cur = json.load(open(J)) if J.exists() else {}
    cur.update(kw)
    json.dump(cur, open(J, "w"), indent=2, default=float)


def fam(rows, part):
    pd.DataFrame(rows).to_csv(T / f"_nfam_{part}.csv", index=False)


def diff_means(d, y, g_mask, c_mask, cluster):
    """Mean of y in g_mask minus mean in c_mask, bootstrap over clusters (multinomial weights)."""
    s = d[g_mask | c_mask].copy()
    s["g"] = g_mask[g_mask | c_mask].astype(float)
    s["v"] = s[y].astype(float)
    s = s.dropna(subset=["v"])
    s["y1"], s["n1"], s["y0"], s["n0"] = s.v * s.g, s.g, s.v * (1 - s.g), 1 - s.g
    agg = cluster_sums(s, ["y1", "n1", "y0", "n0"], cluster=cluster)
    est, lo, hi, reps = fast_boot(agg, lambda z: z["y1"] / z["n1"] - z["y0"] / z["n0"], NB, SEED)
    return {"mean_regressed": s.loc[s.g == 1, "v"].mean(), "mean_comparison": s.loc[s.g == 0, "v"].mean(), "n_regressed": int(s.g.sum()),
            "n_comparison": int((1 - s.g).sum()), "diff": est, "ci_lo": lo, "ci_hi": hi, "p": boot_p(reps, 0.0)}


# ---------------------------------------------------------------- N1
def n1(d):
    reg = d.regressed
    comps = {"all other tracts": ~reg, "other Bexar County tracts": (d.county == BEXAR) & ~reg,
             "other South-Central TX tracts": (d.region == "south-central-tx") & ~reg}
    rows, frows = [], []
    for y in ["msft_share", "msft_dom", "class_share", "height_share"]:
        for cname, cm in comps.items():
            for cl in ["county", "GEOID"]:
                r = {"measure": y, "comparison": cname, "bootstrap_cluster": cl, **diff_means(d, y, reg, cm, cl)}
                rows.append(r)
                if cl == "county" and y in ("msft_share", "msft_dom", "class_share"):
                    frows.append({"exp": "N1", "test": f"{y} regressed - {cname}", "estimate": r["diff"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"], "p": r["p"]})
    t = pd.DataFrame(rows); t.to_csv(T / "n1_regressed_profile.csv", index=False)
    R = d[reg]
    desc = {"n_regressed": int(reg.sum()), "n_regressed_bexar": int((reg & (d.county == BEXAR)).sum()),
            "buildings_lost_450": float((R.r2026a_bldg450 - R.r2026b_bldg450).sum()),
            "regressed_msft_share_pooled": float(R.r2026a_src_msft.sum() / R.r2026a_bldg.sum()),
            "share_regressed_where_loss_le_msft_count": float(((R.r2026a_bldg450 - R.r2026b_bldg450) <= R.r2026a_src_msft).mean()),
            "spearman_loss_vs_msft_share_regressed": float(R[["loss", "msft_share"]].corr("spearman").iloc[0, 1]),
            "regressed_class_share_pooled": float(R.mec_bldg_n_class.sum() / R.mec_bldg_n.sum()),
            "other_class_share_pooled": float(d.loc[~reg, "mec_bldg_n_class"].sum() / d.loc[~reg, "mec_bldg_n"].sum())}
    key = t[(t.measure == "msft_dom") & (t.comparison == "other South-Central TX tracts") & (t.bootstrap_cluster == "county")].iloc[0]
    one = bool(key["diff"] >= 0.20 and key["ci_lo"] > 0)
    keyg = t[(t.measure == "msft_dom") & (t.comparison == "other South-Central TX tracts") & (t.bootstrap_cluster == "GEOID")].iloc[0]
    desc.update({"rule_msft_dom_diff_vs_sctx": float(key["diff"]), "rule_ci_county": [float(key.ci_lo), float(key.ci_hi)],
                 "rule_ci_tract": [float(keyg.ci_lo), float(keyg.ci_hi)],
                 "decision": "one mechanism: ML bulk imports" if one else "two separate failures"})
    jupdate(N1=desc); fam(frows, "n1")
    print(t[t.bootstrap_cluster == "county"].round(3).to_string()); print(json.dumps(desc, indent=1, default=float))


# ---------------------------------------------------------------- N2
HAZ = {"heat": ("epht_heat_days_summer", [("alt_gehe_wbgt28_days_mean", 1), ("alt_hwd_maxtemp_mean", 1)]),
       "wildfire": ("usfs_BP_mean", [("alt_usfs_WHP_mean", 1), ("alt_mtbs_wildfire_burned_pct_land", 1)]),
       "drought": ("usdm_summer_dsci", [("alt_pmdi_mean", -1), ("alt_spi12_mean", -1)])}   # -1: low PMDI/SPI = drier


def top_tercile(v: pd.Series, by: pd.Series | None = None):
    """Top tercile on all tracts (or within `by`). If the cut equals the minimum (zero-inflated), use > cut."""
    def one(x):
        c = x.quantile(2 / 3)
        return (x > c) if c <= x.min() else (x >= c)
    return (v.groupby(by, group_keys=False).apply(one) if by is not None else one(v)).reindex(v.index).fillna(False).astype(bool)


def exposure(d, top, group, mh=False):
    hi, lo = CONTRASTS[group]
    s = d[d[group].isin([hi, lo])].copy()
    s["g"] = (s[group] == hi).astype(float)
    s["he"] = s.bldg_shortfall_lower * top[s.index].astype(float)
    s["he1"], s["hu1"], s["he0"], s["hu0"] = s.he * s.g, s.hu * s.g, s.he * (1 - s.g), s.hu * (1 - s.g)
    cols = ["he1", "hu1", "he0", "hu0"]
    agg = s.groupby("county")[cols].sum()
    reg = s.groupby("county").region.first()
    W = _boot_weights(len(agg), NB, SEED)
    if not mh:
        def stat(z):
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.where(z["he0"] > 0, (z["he1"] / z["hu1"]) / (z["he0"] / z["hu0"]), np.nan)
        obs = stat({c: np.array([agg[c].sum()]) for c in cols})[0]
        reps = stat({c: W @ agg[c].values for c in cols})
    else:   # Mantel-Haenszel rate ratio over regions
        def mhstat(sums):   # sums[c][r] arrays (n_rep,)
            num = sum(sums["he1"][r] * sums["hu0"][r] / (sums["hu1"][r] + sums["hu0"][r]) for r in sums["he1"])
            den = sum(sums["he0"][r] * sums["hu1"][r] / (sums["hu1"][r] + sums["hu0"][r]) for r in sums["he1"])
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.where(den > 0, num / den, np.nan)
        idx = {r: (reg == r).values for r in reg.unique()}
        obs = mhstat({c: {r: np.array([agg[c].values[m].sum()]) for r, m in idx.items()} for c in cols})[0]
        reps = mhstat({c: {r: W[:, m] @ agg[c].values[m] for r, m in idx.items()} for c in cols})
    lo_, hi_ = np.nanpercentile(reps, [2.5, 97.5])
    p = boot_p(np.log(reps[reps > 0]), 0.0) if np.isfinite(obs) and obs > 0 else np.nan
    return {"rate_ratio": obs, "ci_lo": lo_, "ci_hi": hi_, "p": p, "top_share": float(top.mean())}


def n2(d):
    rows, frows, checks = [], [], []
    for hz, (prim, alts) in HAZ.items():
        for grp in ["svi", "rural", "tribal"]:
            ie = exposure_ratio(d, prim, grp, n_boot=NB, seed=SEED)        # IE's own function, as in 06_audit.py
            mine = exposure(d, top_tercile(d[prim]), grp)
            checks.append(abs(ie["rate_ratio"] - mine["rate_ratio"]) < 1e-9)
            variants = [("primary (H5, pooled terciles)", d[prim], None, False)]
            variants += [(f"alternative: {c.replace('alt_', '')}", s * d[c], None, False) for c, s in alts]
            variants += [("primary, terciles within region", d[prim], d.region, False),
                         ("primary, Mantel-Haenszel over regions", d[prim], None, True)]
            for name, v, by, mh in variants:
                r = exposure(d, top_tercile(v, by), grp, mh=mh)
                rows.append({"hazard": hz, "group": grp, "variant": name, **r})
                if not name.startswith("primary (H5"):
                    frows.append({"exp": "N2", "test": f"{hz} {grp} {name}", "estimate": r["rate_ratio"], "ci_lo": r["ci_lo"], "ci_hi": r["ci_hi"], "p": r["p"]})
    t = pd.DataFrame(rows)
    assert all(checks), "re-implementation does not reproduce IE exposure_ratio"
    # N2 decision rule: same side of 1 as the primary, CI excluding 1, in >= 2 of the 3
    # alternative/within-region variants. Reading A counts {alt1, alt2, within-region terciles};
    # reading B adds Mantel-Haenszel (>= 2 of 4). "robust" only if both readings agree.
    verdict = []
    for (hz, grp), g in t.groupby(["hazard", "group"], sort=False):
        p0 = g[g.variant.str.startswith("primary (H5")].iloc[0]
        side = np.sign(np.log(p0.rate_ratio)) if p0.rate_ratio > 0 else 0
        ok = lambda r: (np.sign(np.log(r.rate_ratio)) == side) and (r.ci_lo > 1 or r.ci_hi < 1) if r.rate_ratio > 0 else False
        A = g[g.variant.str.startswith(("alternative", "primary, terciles"))]
        B = g[~g.variant.str.startswith("primary (H5")]
        a, b = int(sum(ok(r) for r in A.itertuples())), int(sum(ok(r) for r in B.itertuples()))
        prim_sig = bool(p0.ci_lo > 1 or p0.ci_hi < 1)
        lab = ("robust" if a >= 2 and b >= 2 else "indicator-dependent") if prim_sig else "primary not significant"
        verdict.append({"hazard": hz, "group": grp, "primary_ratio": p0.rate_ratio, "primary_ci": f"{p0.ci_lo:.2f}-{p0.ci_hi:.2f}",
                        "agree_A_of_3": a, "agree_B_of_4": b, "verdict": lab})
    v = pd.DataFrame(verdict)
    t.to_csv(T / "n2_hazard_robustness.csv", index=False); v.to_csv(T / "n2_verdicts.csv", index=False)
    jupdate(N2={"reproduces_IE_H5": True, "verdicts": v.to_dict("records")}); fam(frows, "n2")
    print(t.round(3).to_string()); print(v.round(3).to_string())


# ---------------------------------------------------------------- N3 / N5
def scores(d):
    s = d[d.ref_bldg.notna()].copy()
    import statsmodels.api as sm
    X = sm.add_constant(np.column_stack([np.log1p(s.hu), np.log1p(s.land_km2)]))
    ols = sm.OLS(np.log1p(s.r2026a_bldg450), X).fit()
    IF = [c for c in d.columns if c.startswith("if_")]
    ok = d[IF].notna().all(axis=1)
    iso = IsolationForest(n_estimators=300, random_state=20261025, n_jobs=1).fit(np.log1p(d.loc[ok, IF].clip(lower=0)))
    anom = pd.Series(np.nan, index=d.index); anom[ok] = -iso.score_samples(np.log1p(d.loc[ok, IF].clip(lower=0)))
    sc = {"conformal model (IE)": s.bldg_deficit_z,
          "OLS log-HU (IE)": pd.Series(-(ols.resid / ols.resid.std()).values, index=s.index),
          "map/housing ratio (IE)": -(np.log1p(s.r2026a_bldg450) - np.log1p(s.struct_equiv)),
          "Isolation Forest (experiments)": anom[s.index],
          "NB shortfall (experiments)": np.log1p(s.exp_mu_nb) - np.log1p(s.exp_y),
          "XGB shortfall (experiments)": np.log1p(s.exp_mu_xgb) - np.log1p(s.exp_y),
          "XGB model E: structure+rural+region (project)": np.log1p(s.prj_mu_E) - np.log1p(s.prj_y),
          "XGB model G: E + neighbour density (project)": np.log1p(s.prj_mu_G) - np.log1p(s.prj_y)}
    return s, sc


def topk(score, k):
    o = np.argsort(-np.nan_to_num(score.values, nan=-np.inf), kind="stable")
    f = np.zeros(len(score), bool); f[o[:k]] = True
    return f


def n3(d):
    s, sc = scores(d)
    truth = s.truth.values; K = int(s.bldg_flag.sum())
    flags = {m: (s.bldg_flag.values.astype(bool) if m.startswith("conformal") else topk(v, K)) for m, v in sc.items()}
    rows, rrows = [], []
    for m, v in sc.items():
        rows.append({"method": m, **flag_skill(flags[m], v.values.astype(float), truth)})
        for reg, idx in s.groupby("region").indices.items():
            rrows.append({"method": m, "region": reg, **flag_skill(flags[m][idx], v.values[idx].astype(float), truth[idx])})
    rng = np.random.default_rng(SEED)
    rp = np.array([truth[rng.choice(len(truth), K, replace=False)].mean() for _ in range(1000)])
    rows.append({"method": "random flags (1,000 draws)", "n": len(truth), "prevalence": truth.mean(), "n_flag": K, "n_true": int(truth.sum()),
                 "precision": rp.mean(), "recall": rp.mean() * K / truth.sum(), "lift": rp.mean() / truth.mean(),
                 "auc": 0.5, "pr_auc": truth.mean(), "precision_lo": np.percentile(rp, 2.5), "precision_hi": np.percentile(rp, 97.5)})
    t = pd.DataFrame(rows); t.to_csv(T / "n3_baselines.csv", index=False)
    pd.DataFrame(rrows).to_csv(T / "n3_by_region.csv", index=False)
    # paired county-cluster bootstrap, same weights for every method
    cl = pd.Categorical(s.county).codes; ncl = cl.max() + 1
    W = _boot_weights(ncl, NB, SEED)
    def met(w, f, v):
        ww = w[cl]; ok = ~np.isnan(v)
        tp = (ww * f * truth).sum()
        return (tp / (ww * f).sum(), tp / (ww * truth).sum(),
                roc_auc_score(truth[ok], v[ok], sample_weight=ww[ok]), average_precision_score(truth[ok], v[ok], sample_weight=ww[ok]))
    names = list(sc); V = {m: sc[m].values.astype(float) for m in names}
    reps = {m: np.empty((NB, 4)) for m in names}
    for b in range(NB):
        for m in names:
            reps[m][b] = met(W[b], flags[m], V[m])
    obs = {m: met(np.ones(ncl), flags[m], V[m]) for m in names}
    MET = ["precision", "recall", "roc_auc", "pr_auc"]
    prow, frows = [], []
    ref = names[0]
    pairs = [(m, ref) for m in names[1:]] + [("XGB model G: E + neighbour density (project)", "XGB model E: structure+rural+region (project)")]
    for a, bb in pairs:
        for j, mt in enumerate(MET):
            dlt = reps[a][:, j] - reps[bb][:, j]
            lo, hi = np.nanpercentile(dlt, [2.5, 97.5])
            r = {"method": a, "minus": bb, "metric": mt, "diff": obs[a][j] - obs[bb][j], "ci_lo": lo, "ci_hi": hi, "p": boot_p(dlt, 0.0)}
            prow.append(r)
            if mt in ("precision", "pr_auc") or bb != ref:
                frows.append({"exp": "N5" if bb != ref else "N3", "test": f"{mt}: {a} - {bb}", "estimate": r["diff"], "ci_lo": lo, "ci_hi": hi, "p": r["p"]})
    p = pd.DataFrame(prow); p.to_csv(T / "n3_paired.csv", index=False)
    beats = p[(p.minus == ref)].assign(sig=lambda x: (x.ci_lo > 0) | (x.ci_hi < 0))
    summ = {m: {mt: ("conformal better" if r.ci_hi < 0 else "baseline better" if r.ci_lo > 0 else "no difference")
                for mt, r in g.set_index("metric").iterrows()} for m, g in beats.groupby("method")}
    jupdate(N3={"budget": K, "prevalence": float(truth.mean()), "comparison_vs_conformal": summ})
    g5 = p[p.minus != ref].set_index("metric")
    jupdate(N5_ranking={"G_minus_E": {mt: [float(r["diff"]), float(r.ci_lo), float(r.ci_hi)] for mt, r in g5.iterrows()},
                        "decision": "second absorption mechanism (G recall lower, CI excludes 0)" if g5.loc["recall", "ci_hi"] < 0 else "one sentence only (no recall loss shown)"})
    fam(frows, "n3")
    print(t.drop(columns=[c for c in t.columns if c in ("f1",)]).round(3).to_string()); print(p.round(4).to_string())


# ---------------------------------------------------------------- N4
def n4(d):
    s = d[d.ref_bldg.notna()].copy()
    s["y"] = s.truth.astype(float); s["log_hu_density"] = np.log1p(s.hu / s.land_km2)
    s = s.replace([np.inf, -np.inf], np.nan).dropna(subset=["y", "class_share", "msft_share", "log_hu_density", "region", "county"])
    m = smf.logit("y ~ class_share + msft_share + log_hu_density + C(region)", data=s).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": pd.Categorical(s.county).codes})
    ci = m.conf_int()
    coef = pd.DataFrame({"coef": m.params, "ci_lo": ci[0], "ci_hi": ci[1], "p": m.pvalues, "odds_ratio": np.exp(m.params)})
    coef.to_csv(T / "n4_logit.csv")
    # class-label poverty as a stand-alone detector (higher score = fewer labels)
    cl = pd.Categorical(s.county).codes; W = _boot_weights(cl.max() + 1, NB, SEED)
    v, tr = -s.class_share.values, s.truth.values
    ok = ~np.isnan(v)
    reps = np.array([[roc_auc_score(tr[ok], v[ok], sample_weight=w[cl][ok]), average_precision_score(tr[ok], v[ok], sample_weight=w[cl][ok])] for w in W])
    det = {"roc_auc": roc_auc_score(tr[ok], v[ok]), "roc_auc_ci": list(np.percentile(reps[:, 0], [2.5, 97.5])),
           "pr_auc": average_precision_score(tr[ok], v[ok]), "pr_auc_ci": list(np.percentile(reps[:, 1], [2.5, 97.5])), "prevalence": float(tr.mean())}
    dom = s.groupby(s.msft_dom.astype(bool)).agg(n=("y", "size"), ref_gap_rate=("y", "mean"), class_share=("class_share", "mean"))
    dom.to_csv(T / "n4_by_msft_dominance.csv")
    # sensitivity (not in the plan): eastern-wa has no reference gaps, so its region effect is not identified
    s2 = s[s.region != "eastern-wa"]
    m2 = smf.logit("y ~ class_share + msft_share + log_hu_density + C(region)", data=s2).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": pd.Categorical(s2.county).codes})
    ci2 = m2.conf_int()
    pd.DataFrame({"coef": m2.params, "ci_lo": ci2[0], "ci_hi": ci2[1], "p": m2.pvalues, "odds_ratio": np.exp(m2.params)}).to_csv(T / "n4_logit_excl_eastern_wa.csv")
    c = coef.loc["class_share"]
    if c.ci_lo <= 0 <= c.ci_hi:
        dec = "separate failures (class share does not predict gaps)"
    elif c.coef > 0:
        dec = ("rule as written not met (CI excludes 0), but the sign is opposite to 'attribute poverty signals gaps': "
               "label-rich tracts have slightly more reference gaps; label poverty is not a gap detector")
    else:
        dec = "attribute poverty is associated with reference gaps"
    jupdate(N4_sensitivity_excl_eastern_wa={"class_share_coef": float(m2.params["class_share"]),
                                            "ci": [float(ci2.loc["class_share", 0]), float(ci2.loc["class_share", 1])], "p": float(m2.pvalues["class_share"]),
                                            "converged": bool(m2.mle_retvals.get("converged", True))})
    jupdate(N4={"class_share_or_per_unit": float(c.odds_ratio), "ci": [float(np.exp(c.ci_lo)), float(np.exp(c.ci_hi))], "p": float(c.p),
                "detector": det, "by_msft_dominance": dom.reset_index().to_dict("records"),
                "converged": bool(m.mle_retvals.get("converged", True)), "decision": dec})
    fam([{"exp": "N4", "test": "class_share coefficient", "estimate": float(c.coef), "ci_lo": float(c.ci_lo), "ci_hi": float(c.ci_hi), "p": float(c.p)}], "n4")
    print(coef.round(4).to_string()); print(json.dumps(det, default=float)); print(dom)


# ---------------------------------------------------------------- N5 absorption
def n5(d):
    s = d[d.ref_bldg.notna() & (d.ref_bldg >= 10)].copy()          # E2 sample rule
    lr = np.log1p(s.ref_bldg)
    s["obs_minus_ref"] = np.log1p(s.prj_y) - lr
    s["E_minus_ref"] = np.log1p(s.prj_mu_E) - lr
    s["G_minus_ref"] = np.log1p(s.prj_mu_G) - lr
    rows, ab = [], {}
    for grp in ["svi", "cvi", "rural", "tribal"]:
        o = {k: continuous_contrast(s, k, grp) for k in ["obs_minus_ref", "E_minus_ref", "G_minus_ref"]}
        for k, r in o.items():
            rows.append({"variable": k, **r})
        ab[grp] = {m: float(o[f"{m}_minus_ref"]["adj_diff"] / o["obs_minus_ref"]["adj_diff"]) for m in "EG"}
    pd.DataFrame(rows).to_csv(T / "n5_absorption.csv", index=False)
    ie = json.load(open(Path("outputs/tables") / "exploratory.json"))
    jupdate(N5_absorption={"absorbed_share": ab, "note": "model E uses rural and region as inputs, so its rural absorption is by construction",
                           "IE_E2_for_reference": {g: ie[f"E2_absorbed_share_{g}"] for g in ["svi", "cvi", "rural", "tribal"]}})
    print(pd.DataFrame(rows)[["variable", "group", "mean_hi", "mean_lo", "adj_diff", "ci_lo", "ci_hi"]].round(4).to_string()); print(ab)


# ---------------------------------------------------------------- FDR over the N-family
def fdr():
    f = pd.concat([pd.read_csv(p) for p in sorted(T.glob("_nfam_*.csv"))], ignore_index=True)
    f["reject_bh_q05"], f["p_bh"] = bh(f.p)
    f.to_csv(T / "n_family_fdr.csv", index=False)
    jupdate(N_family={"tests": len(f), "rejected": int(f.reject_bh_q05.sum())})
    print(f.round(4).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--part", default="all"); a = ap.parse_args()
    d, join = load(); jupdate(join_rate=join, n_tracts=len(d))
    parts = {"n1": n1, "n2": n2, "n3": n3, "n4": n4, "n5": n5}
    for k in (parts if a.part == "all" else [a.part]):
        if k != "fdr":
            parts[k](d)
    if a.part in ("all", "fdr"):
        fdr()
