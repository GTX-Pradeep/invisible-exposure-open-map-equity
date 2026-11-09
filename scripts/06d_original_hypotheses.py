"""Tests of the ORIGINAL pre-registration (repository commit 807831b, 2026-10-16), exactly as worded there:
Mann-Whitney U on tract-level outcomes, medians and effect sizes, BH across these contrasts.
Blanks in that template were completed in docs/preregistration.md before any model output was seen:
quartiles of heat/drought/wildfire are cut on the study tracts; SVI quartiles use the national percentile;
rural = participant urban/rural class (ur_class == 'Rural'); tribal = any tribal-area overlap."""
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from coverage_risk.audit import bh

d = pd.read_parquet("data/processed/catchup_frame.parquet")
d["he_per1000"] = 1000 * d.bldg_shortfall_lower / d.hu.clip(lower=1)
q = lambda c, p: d[c].quantile(p)
HEAT, DRT, WF = "epht_heat_days_summer", "usdm_summer_dsci", "usfs_BP_mean"
hi = lambda c: d[c] >= q(c, 0.75); lo = lambda c: d[c] <= q(c, 0.25)
svi_hi, svi_lo = d.svi_overall >= 0.75, (d.svi_overall < 0.25) & (d.svi_overall >= 0)
rural, tribal = d.ur_class == "Rural", d.tribal_any.fillna(False).astype(bool)
ok = d.ref_bldg.notna() & (d.ref_bldg >= 10)


def mw(name, outcome, a, b, alt="greater"):
    xa, xb = d.loc[a, outcome].dropna(), d.loc[b, outcome].dropna()
    u, p = mannwhitneyu(xa, xb, alternative="two-sided")
    return {"hyp": name, "outcome": outcome, "n_a": len(xa), "n_b": len(xb), "median_a": xa.median(), "median_b": xb.median(),
            "mean_a": xa.mean(), "mean_b": xb.mean(), "rank_biserial": 2 * u / (len(xa) * len(xb)) - 1, "p": p}


rows = [
    mw("H1 orig: high-SVI x high-heat vs low-SVI x low-heat", "he_per1000", svi_hi & hi(HEAT), svi_lo & lo(HEAT)),
    mw("H2 orig: rural/tribal x high-drought vs non-rural non-tribal (source max share)", "b_src_max_share",
       (rural | tribal) & hi(DRT), ~rural & ~tribal),
    mw("H2 orig: rural/tribal x high-drought vs non-rural non-tribal (single-source flag)", "b_single_source",
       (rural | tribal) & hi(DRT), ~rural & ~tribal),
    mw("H3 orig: shortfall change 2023->2026-10, high- vs low-SVI (log completeness change)", "d_lc", svi_hi & ok, svi_lo & ok),
    mw("H5 orig: high- vs low-wildfire hazard", "he_per1000", hi(WF), lo(WF)),
]
r = pd.DataFrame(rows)
r["reject_bh"], r["p_bh"] = bh(r.p, 0.05)
r.to_csv("outputs/tables/original_prereg_tests.csv", index=False)
print(r.round(4).to_string())
