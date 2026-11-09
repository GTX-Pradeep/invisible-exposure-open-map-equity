"""Equity audit: pre-registered group contrasts, cluster bootstrap, Benjamini-Hochberg."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


def define_groups(st: pd.DataFrame) -> pd.DataFrame:
    g = pd.DataFrame({"GEOID": st.GEOID})
    svi = st.svi_overall.where(st.svi_overall >= 0)
    g["svi"] = np.select([svi >= 0.75, svi < 0.25], ["Q4", "Q1"], default=None)
    g.loc[svi.isna(), "svi"] = None
    ruca = pd.to_numeric(st.ruca_primary, errors="coerce")
    g["rural"] = np.where(ruca.isna(), None, np.where(ruca >= 4, "rural", "urban"))
    g["tribal"] = np.where(st.tribal_any.fillna(False).astype(bool), "tribal", "non-tribal")
    cvi = st.cvi_overall
    q1, q3 = cvi.quantile([0.25, 0.75])
    g["cvi"] = np.select([cvi >= q3, cvi < q1], ["top", "bottom"], default=None)
    g.loc[cvi.isna(), "cvi"] = None
    return g


CONTRASTS = {"svi": ("Q4", "Q1"), "cvi": ("top", "bottom"), "rural": ("rural", "urban"), "tribal": ("tribal", "non-tribal")}


def cluster_bootstrap(df, stat_fn, cluster="county", n=2000, seed=0):
    rng = np.random.default_rng(seed)
    cl = df[cluster].values
    uc = np.unique(cl)
    idx_by = {c: np.where(cl == c)[0] for c in uc}
    est = stat_fn(df)
    reps = np.empty(n)
    for b in range(n):
        pick = rng.choice(uc, size=len(uc), replace=True)
        ii = np.concatenate([idx_by[c] for c in pick])
        reps[b] = stat_fn(df.iloc[ii])
    lo, hi = np.nanpercentile(reps, [2.5, 97.5])
    # two-sided bootstrap p for H0: stat = null (0 for differences, 1 for ratios handled by caller)
    return est, lo, hi, reps




def _boot_weights(n_clusters, n_boot, seed):
    rng = np.random.default_rng(seed)
    return rng.multinomial(n_clusters, np.full(n_clusters, 1 / n_clusters), size=n_boot).astype(float)


def cluster_sums(df, cols, cluster="county"):
    """Per-cluster sums of the given columns (fast cluster bootstrap via multinomial weights)."""
    return df.groupby(cluster)[cols].sum()


def fast_boot(agg: pd.DataFrame, stat, n_boot=2000, seed=0):
    """stat(sums: dict[str, ndarray]) -> ndarray; called once with observed sums and once with weighted sums."""
    W = _boot_weights(len(agg), n_boot, seed)
    est = stat({c: np.array([agg[c].sum()]) for c in agg.columns})[0]
    reps = stat({c: W @ agg[c].values for c in agg.columns})
    lo, hi = np.nanpercentile(reps, [2.5, 97.5])
    return est, lo, hi, reps


def boot_p(reps, null=0.0):
    reps = reps[~np.isnan(reps)]
    p = 2 * min((reps <= null).mean(), (reps >= null).mean())
    return max(p, 1 / len(reps))


def flag_contrast(d: pd.DataFrame, outcome: str, group: str, n_boot=2000, seed=0) -> dict:
    hi, lo = CONTRASTS[group]
    s = d[d[group].isin([hi, lo])].copy()
    s["g"] = (s[group] == hi).astype(int)
    s["y"] = s[outcome].astype(float)
    rate_hi, rate_lo = s.loc[s.g == 1, "y"].mean(), s.loc[s.g == 0, "y"].mean()
    # adjusted log-odds, region fixed effects, county-cluster SE
    try:
        m = smf.logit("y ~ g + C(region)", data=s).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.Categorical(s.county).codes})
        b, se, p = m.params["g"], m.bse["g"], m.pvalues["g"]
    except Exception:  # separation etc.
        b, se, p = np.nan, np.nan, np.nan
    s["n1"], s["y1"] = s.g, s.g * s.y
    s["n0"], s["y0"] = 1 - s.g, (1 - s.g) * s.y
    agg = cluster_sums(s, ["n1", "y1", "n0", "y0"])
    est, ci_lo, ci_hi, reps = fast_boot(agg, lambda z: z["y1"] / z["n1"] - z["y0"] / z["n0"], n_boot, seed)
    return {"outcome": outcome, "group": group, "contrast": f"{hi} vs {lo}", "n_hi": int(s.g.sum()), "n_lo": int((1 - s.g).sum()),
            "rate_hi": rate_hi, "rate_lo": rate_lo, "risk_diff": est, "rd_ci_lo": ci_lo, "rd_ci_hi": ci_hi,
            "adj_odds_ratio": float(np.exp(b)), "aor_ci_lo": float(np.exp(b - 1.96 * se)), "aor_ci_hi": float(np.exp(b + 1.96 * se)),
            "p": float(p)}


def continuous_contrast(d: pd.DataFrame, outcome: str, group: str) -> dict:
    hi, lo = CONTRASTS[group]
    s = d[d[group].isin([hi, lo])].dropna(subset=[outcome]).copy()
    s["g"] = (s[group] == hi).astype(int)
    m = smf.ols(f"{outcome} ~ g + C(region)", data=s).fit(cov_type="cluster", cov_kwds={"groups": pd.Categorical(s.county).codes})
    return {"outcome": outcome, "group": group, "contrast": f"{hi} vs {lo}", "n_hi": int(s.g.sum()), "n_lo": int((1 - s.g).sum()),
            "mean_hi": s.loc[s.g == 1, outcome].mean(), "mean_lo": s.loc[s.g == 0, outcome].mean(),
            "adj_diff": m.params["g"], "ci_lo": m.conf_int().loc["g", 0], "ci_hi": m.conf_int().loc["g", 1], "p": float(m.pvalues["g"])}


def exposure_ratio(d: pd.DataFrame, hazard_col: str, group: str, n_boot=2000, seed=0) -> dict:
    """Hidden exposure = missing structures (below lower bound) in top-tercile-hazard tracts per 1,000 HU."""
    hi, lo = CONTRASTS[group]
    s = d[d[group].isin([hi, lo])].copy()
    cut = d[hazard_col].quantile(2 / 3)
    s["he"] = s.bldg_shortfall_lower * (s[hazard_col] >= cut)
    s["g"] = (s[group] == hi).astype(int)

    def rate(x, gv):
        xx = x[x.g == gv]
        return 1000 * xx.he.sum() / max(xx.hu.sum(), 1)

    s["he1"], s["hu1"] = s.he * s.g, s.hu * s.g
    s["he0"], s["hu0"] = s.he * (1 - s.g), s.hu * (1 - s.g)
    agg = cluster_sums(s, ["he1", "hu1", "he0", "hu0"])
    with np.errstate(divide="ignore", invalid="ignore"):
        est, ci_lo, ci_hi, reps = fast_boot(agg, lambda z: np.where(z["he0"] > 0, (z["he1"] / z["hu1"]) / (z["he0"] / z["hu0"]), np.nan), n_boot, seed)
    return {"hazard": hazard_col, "group": group, "contrast": f"{hi} vs {lo}", "rate_hi_per1000hu": rate(s, 1),
            "rate_lo_per1000hu": rate(s, 0), "missing_hi": float(s.loc[s.g == 1, "he"].sum()),
            "missing_lo": float(s.loc[s.g == 0, "he"].sum()), "rate_ratio": est, "ci_lo": ci_lo, "ci_hi": ci_hi,
            "p": boot_p(np.log(reps[reps > 0]), 0.0) if np.isfinite(est) else np.nan}


def bh(p: pd.Series, q=0.05):
    ok = p.notna()
    rej = pd.Series(False, index=p.index); padj = pd.Series(np.nan, index=p.index)
    if ok.any():
        r, pa, _, _ = multipletests(p[ok], alpha=q, method="fdr_bh")
        rej[ok], padj[ok] = r, pa
    return rej, padj
