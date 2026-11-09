"""Apply Benjamini-Hochberg across the pre-registered FDR family (H1, H2, H3, H5)."""
import pandas as pd
from coverage_risk.audit import bh
a = pd.read_csv("outputs/tables/h125_raw.csv")
parts = [a]
try:
    h3 = pd.read_csv("outputs/tables/h3_raw.csv"); parts.append(h3)
except FileNotFoundError:
    print("H3 not yet available")
f = pd.concat(parts, ignore_index=True)
f["reject_bh"], f["p_bh"] = bh(f.p, 0.05)
f.to_csv("outputs/tables/confirmatory_fdr.csv", index=False)
cols = [c for c in ["hyp", "layer", "hazard_name", "group", "contrast", "rate_hi", "rate_lo", "risk_diff", "adj_odds_ratio",
        "rate_ratio", "adj_diff", "p", "p_bh", "reject_bh"] if c in f]
print(f[cols].round(4).to_string())
