"""Exploratory journal-revision checks J1-J6 (not pre-registered; added 2026-11-11 in response to an internal review).

J1  One-sided conformal flags: calibrate the lower bound alone, so the flag rate is controlled at alpha_flag (= 5%) in the
    cross-conformal sense, instead of relying on the lower tail of a two-sided 90% interval.
J2  Flag stability: refit the building model with 10 seeds; per-tract flag frequency; skill of stable flags.
J3  Region transfer with local recalibration: leave-one-region-out quantile models, then calibrate with n tracts of the
    held-out region; coverage on the rest of that region.
J4  Reference-based hidden exposure: missing structures measured directly against USA Structures in top-tercile hazard
    tracts, by group (no model involved), next to the model-based H5.
J5  Reference-gap threshold sensitivity (70/80/90%).
J6  Model class: ROC-AUC vs PR-AUC and top-510 precision for flexible and log-linear expectations.

usage: python scripts/15_journal_checks.py --part seeds|rest|all
Writes outputs/tables/journal/*.csv, paper/numbers_journal.tex, paper/tab_journal_*.tex."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from sklearn.metrics import average_precision_score, roc_auc_score

from coverage_risk.model import STRUCTURAL, _fit_q, crossfit_cqr, make_folds

ap = argparse.ArgumentParser(); ap.add_argument("--part", default="all"); a = ap.parse_args()
cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
T = Path("outputs/tables/journal"); T.mkdir(parents=True, exist_ok=True)
P = "data/processed"
df = pd.read_parquet(f"{P}/tracts_all.parquet")
au = pd.read_parquet(f"{P}/audit_frame.parquet")
ex = pd.read_parquet(f"{P}/expectation.parquet")
folds = make_folds(df, "spatial", k=10, seed=mc["seed"], km=mc["spatial_block_km"])
assert (ex.bldg_fold.values == folds).all(), "fold assignment differs from the published model"
ref_ok = (df.ref_bldg >= 10).values
gap = (df.r2026a_bldg450 / df.ref_bldg < 0.8).values
SEEDS = [mc["seed"]] + list(range(1, 10))


def skill(flag, m=ref_ok):
    g, f = gap[m], np.asarray(flag)[m]
    p = g[f].mean() if f.any() else np.nan
    return {"n_flag": int(f.sum()), "precision": p, "recall": (g & f).sum() / g.sum(), "lift": p / g.mean()}


# ------------------------------------------------------------------ J2 seeds (slow part)
if a.part in ("seeds", "all"):
    F = {}
    for s in SEEDS:
        o = crossfit_cqr(df, "r2026a_bldg450", STRUCTURAL, folds, mc["alpha"], mc["lgbm"], s)
        F[f"seed_{s}"] = o.flag.values
        print("seed", s, "flags", int(o.flag.sum()), "coverage", round(o.covered.mean(), 4), flush=True)
    pd.DataFrame({"GEOID": df.GEOID, **F}).to_parquet(T / "seed_flags.parquet", index=False)

# ------------------------------------------------------------------ everything else
if a.part in ("rest", "all"):
    M = {}
    pc = lambda x, n=1: f"{100 * x:.{n}f}\\%"
    f2 = lambda x: f"{x:.2f}"
    alpha = mc["alpha"]

    # J1 one-sided conformal lower bound at alpha_flag = alpha / 2
    af = alpha / 2
    s1 = (ex.bldg_q_lo - ex.bldg_y_log).values
    low1 = np.empty(len(ex))
    for k in np.unique(folds):
        cal = np.sort(s1[folds != k]); m = len(cal)
        low1[folds == k] = ex.bldg_q_lo.values[folds == k] - cal[min(m - 1, int(np.ceil((1 - af) * (m + 1))) - 1)]
    flag1 = ex.bldg_y_log.values < low1
    two = ex.bldg_flag.values
    jac = (flag1 & two).sum() / (flag1 | two).sum()
    j1 = pd.DataFrame([{"rule": "two-sided 90% CQR, below lower bound (primary)", "flag_rate": two.mean(), **skill(two)},
                       {"rule": "one-sided CQR, alpha_flag = 5%", "flag_rate": flag1.mean(), **skill(flag1)}])
    j1["jaccard_with_primary"] = [1.0, jac]
    j1.to_csv(T / "j1_one_sided.csv", index=False); print(j1.round(4).to_string())
    by_reg = pd.DataFrame({"region": df.region, "f": flag1}).groupby("region").f.mean()
    M.update({"JoFlagRate": pc(flag1.mean()), "JoTwoBelow": pc(two.mean()), "JoTwoAbove": pc((ex.bldg_y_log > ex.bldg_upper_log).mean()),
              "JoJaccard": f2(jac), "JoLift": f"{skill(flag1)['lift']:.1f}", "JoPrec": f"{skill(flag1)['precision']:.3f}",
              "JoRegMin": pc(by_reg.min()), "JoRegMax": pc(by_reg.max())})

    # J2 stability
    sf = pd.read_parquet(T / "seed_flags.parquet")
    Fm = sf[[c for c in sf.columns if c.startswith("seed_")]].values
    freq = Fm.mean(axis=1)
    pairs = [((Fm[:, i] & Fm[:, j]).sum() / (Fm[:, i] | Fm[:, j]).sum()) for i in range(Fm.shape[1]) for j in range(i + 1, Fm.shape[1])]
    rows = []
    for lab, f in [("single seed (published)", Fm[:, 0]), ("flagged in >= 1 of 10 seeds", freq >= 0.1),
                   ("majority (>= 6 of 10)", freq >= 0.6), ("stable (>= 9 of 10)", freq >= 0.9)]:
        rows.append({"flag_set": lab, **skill(f)})
    j2 = pd.DataFrame(rows); j2.to_csv(T / "j2_seed_stability.csv", index=False); print(j2.round(4).to_string())
    pd.DataFrame({"GEOID": df.GEOID, "flag_frequency": freq}).to_csv(T / "j2_flag_frequency.csv", index=False)
    loss = (au.set_index("GEOID").loc[df.GEOID, "r2026a_bldg450"].values - au.set_index("GEOID").loc[df.GEOID, "r2026b_bldg450"].values
            if "r2026b_bldg450" in au else None)
    st = j2.set_index("flag_set")
    M.update({"JsPairMin": f2(min(pairs)), "JsPairMax": f2(max(pairs)), "JsPairMean": f2(np.mean(pairs)),
              "JsEver": f"{int((freq > 0).sum()):,}", "JsStable": f"{int((freq >= 0.9).sum()):,}", "JsMajority": f"{int((freq >= 0.6).sum()):,}",
              "JsSingleLift": f"{st.loc['single seed (published)', 'lift']:.1f}", "JsStableLift": f"{st.loc['stable (>= 9 of 10)', 'lift']:.1f}",
              "JsStablePrec": f"{st.loc['stable (>= 9 of 10)', 'precision']:.3f}", "JsStableRecall": f"{st.loc['stable (>= 9 of 10)', 'recall']:.3f}",
              "JsMajLift": f"{st.loc['majority (>= 6 of 10)', 'lift']:.1f}"})

    # J3 leave-one-region-out with local recalibration
    X = df[STRUCTURAL].astype(float).values; y = np.log1p(df.r2026a_bldg450.astype(float).values)
    rng = np.random.default_rng(mc["seed"]); rows = []
    for reg in sorted(df.region.unique()):
        te = (df.region == reg).values; tr = ~te
        ql = _fit_q(X[tr], y[tr], alpha / 2, mc["lgbm"], mc["seed"]).predict(X[te])
        qh = _fit_q(X[tr], y[tr], 1 - alpha / 2, mc["lgbm"], mc["seed"]).predict(X[te])
        qm = _fit_q(X[tr], y[tr], 0.5, mc["lgbm"], mc["seed"]).predict(X[te])
        lo, hi = np.minimum(ql, qm), np.maximum(qh, qm)
        sc_te = np.maximum(lo - y[te], y[te] - hi)
        # global calibration from the training regions' own spatial cross-fitted scores (as in the paper): use published OOF scores
        sc_tr = np.maximum(ex.bldg_q_lo.values[tr] - ex.bldg_y_log.values[tr], ex.bldg_y_log.values[tr] - ex.bldg_q_hi.values[tr])
        qg = np.sort(sc_tr)[int(np.ceil((1 - alpha) * (tr.sum() + 1))) - 1]
        rows.append({"region": reg, "n_cal": 0, "coverage": (sc_te <= qg).mean(), "draws": 1})
        nreg = te.sum()
        for n in [25, 50, 100, 200]:
            if n >= nreg - 20:
                continue
            cov = []
            for _ in range(200):
                idx = rng.permutation(nreg); c, e = idx[:n], idx[n:]
                q = np.sort(sc_te[c])[min(n - 1, int(np.ceil((1 - alpha) * (n + 1))) - 1)]
                cov.append((sc_te[e] <= q).mean())
            rows.append({"region": reg, "n_cal": n, "coverage": np.mean(cov), "cov_p05": np.percentile(cov, 5), "cov_p95": np.percentile(cov, 95), "draws": 200})
    j3 = pd.DataFrame(rows); j3.to_csv(T / "j3_local_recalibration.csv", index=False); print(j3.round(3).to_string())
    g0 = j3[j3.n_cal == 0]; g50 = j3[j3.n_cal == 50]
    M.update({"JtGlobalMin": pc(g0.coverage.min()), "JtGlobalMax": pc(g0.coverage.max()),
              "JtFiftyMin": pc(g50.coverage.min()), "JtFiftyMax": pc(g50.coverage.max()),
              "JtFiftyLo": pc(g50.cov_p05.min()), "JtFiftyHi": pc(g50.cov_p95.max())})

    # J4 reference-based hidden exposure
    d = au.copy()
    d = d[d.ref_bldg.notna() & (d.ref_bldg >= 10)]
    d["miss_ref"] = (d.ref_bldg - d.r2026a_bldg450).clip(lower=0)
    # same group definitions as the pre-registered audit (RUCA >= 4; any tribal-area overlap)
    d["rural_b"] = d.rural.eq("rural"); d["tribal_b"] = d.tribal.eq("tribal")
    cl = d.county.values; uc = np.unique(cl); idx = {c: np.where(cl == c)[0] for c in uc}
    draws = [np.concatenate([idx[c] for c in rng.choice(uc, len(uc))]) for _ in range(1000)]
    rows = []
    for hz, col in [("heat", "epht_heat_days_summer"), ("wildfire", "usfs_BP_mean"), ("drought", "usdm_summer_dsci")]:
        hot = (d[col] >= au[col].quantile(2 / 3)).values
        for grp in ["rural_b", "tribal_b"]:
            gv = d[grp].values
            for lab, mcol in [("reference (USA Structures)", "miss_ref"), ("model (conformal lower bound)", "bldg_shortfall_lower")]:
                mv = d[mcol].values * hot; hu = d.hu.values
                f = lambda i: (mv[i][gv[i]].sum() / hu[i][gv[i]].sum()) / max(mv[i][~gv[i]].sum() / hu[i][~gv[i]].sum(), 1e-12)
                bs = np.array([f(i) for i in draws])
                rows.append({"hazard": hz, "group": grp.replace("_b", ""), "measure": lab,
                             "rate_hi_per1000hu": 1000 * mv[gv].sum() / hu[gv].sum(), "rate_lo_per1000hu": 1000 * mv[~gv].sum() / hu[~gv].sum(),
                             "rate_ratio": f(np.arange(len(d))), "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
    j4 = pd.DataFrame(rows); j4.to_csv(T / "j4_reference_hidden_exposure.csv", index=False); print(j4.round(3).to_string())
    q4 = j4.set_index(["hazard", "group", "measure"])
    for hz in ["wildfire", "drought", "heat"]:
        for grp, G in [("rural", "Rural"), ("tribal", "Tribal")]:
            r = q4.loc[(hz, grp, "reference (USA Structures)")]
            M[f"Jh{hz.capitalize()}{G}"] = f2(r.rate_ratio); M[f"Jh{hz.capitalize()}{G}CI"] = f"[{r.ci_lo:.2f}, {r.ci_hi:.2f}]"
    M["JhMissTotal"] = f"{d.miss_ref.sum():,.0f}"

    # J5 + J6: thresholds and model classes
    dd = df[["GEOID", "lat", "lon", "region", "hu", "pop", "land_km2", "r2026a_bldg450", "ref_bldg"]].copy()
    Xg = np.log1p(pd.DataFrame({"land": dd.land_km2, "hu": dd.hu, "hd": dd.hu / dd.land_km2.clip(lower=1e-3), "pop": dd["pop"],
                                "pd": dd["pop"] / dd.land_km2.clip(lower=1e-3)}))
    Xg = sm.add_constant(((Xg - Xg.mean()) / Xg.std()).values)
    yy = dd.r2026a_bldg450.values.astype(float); mu = np.zeros(len(dd)); al = np.zeros(len(dd))
    for k in np.unique(folds):
        tr, te = folds != k, folds == k
        p = sm.GLM(yy[tr], Xg[tr], family=sm.families.Poisson()).fit(); mt = p.predict(Xg[tr])
        aa = max(((yy[tr] - mt) ** 2 - yy[tr]).sum() / (mt ** 2).sum(), 1e-6)
        mu[te] = sm.GLM(yy[tr], Xg[tr], family=sm.families.NegativeBinomial(alpha=aa)).fit().predict(Xg[te]); al[te] = aa
    me = pd.read_csv("data/external/companion/mapequity_risk.csv", dtype={"GEOID": str}).set_index("GEOID").loc[df.GEOID]
    SC = {"Conformal deficit (published flag score)": ex.bldg_deficit_z.values,
          "LightGBM log residual": (ex.bldg_q_med - ex.bldg_y_log).values,
          "NB GLM, 5 structural features (refit here)": (mu - yy) / np.sqrt(mu + al * mu ** 2),
          "MapEquity frozen building shortfall": me.building_shortfall.values,
          "Raw sparsity": -np.log((yy + 1) / (dd.hu.values + 1))}
    rows = []
    for thr in [0.7, 0.8, 0.9]:
        g = (yy / dd.ref_bldg.values < thr)[ref_ok]
        for name, s in SC.items():
            sv = s[ref_ok]; top = np.argsort(-sv)[:510]
            rows.append({"threshold": thr, "score": name, "prevalence": g.mean(), "roc_auc": roc_auc_score(g, sv),
                         "pr_auc": average_precision_score(g, sv), "precision_top510": g[top].mean()})
        f = two[ref_ok]
        rows.append({"threshold": thr, "score": "Conformal flags (published, 510)", "prevalence": g.mean(), "roc_auc": np.nan,
                     "pr_auc": np.nan, "precision_top510": g[f].mean()})
        rur = au.set_index("GEOID").loc[df.GEOID[ref_ok], "rural"].eq("rural").values
        rows.append({"threshold": thr, "score": "rural/urban gap ratio", "prevalence": g.mean(), "roc_auc": np.nan, "pr_auc": np.nan,
                     "precision_top510": g[rur].mean() / g[~rur].mean()})
    j56 = pd.DataFrame(rows); j56.to_csv(T / "j5_j6_thresholds_model_class.csv", index=False); print(j56.round(3).to_string())
    q = j56[j56.threshold == 0.8].set_index("score")
    M.update({"JmGlmAuc": f2(q.loc["NB GLM, 5 structural features (refit here)", "roc_auc"]), "JmGlmPr": f"{q.loc['NB GLM, 5 structural features (refit here)', 'pr_auc']:.3f}",
              "JmLgbAuc": f2(q.loc["LightGBM log residual", "roc_auc"]), "JmLgbPr": f"{q.loc['LightGBM log residual', 'pr_auc']:.3f}",
              "JmCfPr": f"{q.loc['Conformal deficit (published flag score)', 'pr_auc']:.3f}", "JmMePr": f"{q.loc['MapEquity frozen building shortfall', 'pr_auc']:.3f}",
              "JmGlmTop": f"{q.loc['NB GLM, 5 structural features (refit here)', 'precision_top510']:.3f}",
              "JmLgbTop": f"{q.loc['LightGBM log residual', 'precision_top510']:.3f}"})
    rr = j56[j56.score == "rural/urban gap ratio"].set_index("threshold").precision_top510
    M.update({"JrRuralSeven": f2(rr[0.7]), "JrRuralNine": f2(rr[0.9])})
    lt = j56[j56.score == "LightGBM log residual"].set_index("threshold"); gl = j56[j56.score == "NB GLM, 5 structural features (refit here)"].set_index("threshold")
    M["JrOrderHolds"] = "holds" if all((gl.roc_auc > lt.roc_auc) & (lt.pr_auc > gl.pr_auc)) else "does not hold"

    with open("paper/numbers_journal.tex", "w") as fh:
        fh.write("% generated by scripts/15_journal_checks.py -- do not edit\n")
        for k, v in M.items():
            assert k.isalpha(), k
            fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    # tables
    L = ["\\begin{tabular}{lrrrr}\\toprule", "Score & ROC-AUC & PR-AUC & Precision, top 510 & Prevalence\\\\\\midrule"]
    for name in SC:
        r = q.loc[name]; L.append(f"{name} & {r.roc_auc:.3f} & {r.pr_auc:.3f} & {r.precision_top510:.3f} & {100 * r.prevalence:.2f}\\%\\\\")
    L.append("\\bottomrule\\end{tabular}"); open("paper/tab_journal_modelclass.tex", "w").write("\n".join(L) + "\n")
    L = ["\\begin{tabular}{lrrrr}\\toprule", "Flag set & Flags & Precision & Recall & Lift\\\\\\midrule"]
    for r in j2.itertuples():
        L.append(f"{r.flag_set.replace('>=', '$\\geq$')} & {r.n_flag:,} & {r.precision:.3f} & {r.recall:.3f} & {r.lift:.1f}\\\\")
    for r in j1.itertuples():
        if r.rule.startswith("one-sided"):
            L.append(f"One-sided CQR ($\\alpha_{{\\mathrm{{flag}}}}=5\\%$) & {r.n_flag:,} & {r.precision:.3f} & {r.recall:.3f} & {r.lift:.1f}\\\\")
    L.append("\\bottomrule\\end{tabular}"); open("paper/tab_journal_stability.tex", "w").write("\n".join(L) + "\n")
    L = ["\\begin{tabular}{lrrrrr}\\toprule", "Held-out region & Global & $n=25$ & $n=50$ & $n=100$ & $n=200$\\\\\\midrule"]
    for reg, g in j3.groupby("region"):
        cells = []
        for n in [0, 25, 50, 100, 200]:
            r = g[g.n_cal == n]
            cells.append(f"{100 * r.coverage.iloc[0]:.1f}\\%" if len(r) else "--")
        L.append(f"{reg} & " + " & ".join(cells) + "\\\\")
    L.append("\\bottomrule\\end{tabular}"); open("paper/tab_journal_transfer.tex", "w").write("\n".join(L) + "\n")
    L = ["\\begin{tabular}{llrr}\\toprule", "Hazard & Group & Reference-based RR [95\\% CI] & Model-based RR [95\\% CI]\\\\\\midrule"]
    for (hz, grp), g in j4.groupby(["hazard", "group"], sort=False):
        r = g.set_index("measure")
        c = lambda m: f"{r.loc[m, 'rate_ratio']:.2f} [{r.loc[m, 'ci_lo']:.2f}, {r.loc[m, 'ci_hi']:.2f}]"
        L.append(f"{hz} & {grp} vs.\\ rest & {c('reference (USA Structures)')} & {c('model (conformal lower bound)')}\\\\")
    L.append("\\bottomrule\\end{tabular}"); open("paper/tab_journal_exposure.tex", "w").write("\n".join(L) + "\n")
    print(len(M), "macros")
