"""POI reference: Census ZIP Business Patterns 2023 establishments allocated to 2020 tracts by
ZCTA land-area share (approximate), plus exact county-level CBP 2023 establishment totals.
Validation-only."""
import pandas as pd

raw = "data/raw/cbp"
z = pd.read_csv(f"{raw}/zbp23totals.txt", dtype={"zip": str})[["zip", "est"]]
rel = pd.read_csv(f"{raw}/tab20_zcta520_tract20_natl.txt", sep="|", dtype=str)
rel = rel[rel.GEOID_ZCTA5_20.notna() & (rel.GEOID_ZCTA5_20 != "")]
for c in ["AREALAND_ZCTA5_20", "AREALAND_PART"]:
    rel[c] = pd.to_numeric(rel[c])
rel["w"] = rel.AREALAND_PART / rel.AREALAND_ZCTA5_20.where(rel.AREALAND_ZCTA5_20 > 0)
m = rel.merge(z, left_on="GEOID_ZCTA5_20", right_on="zip", how="inner")
m["est_alloc"] = m.est * m.w.fillna(0)
t = m.groupby("GEOID_TRACT_20").est_alloc.sum().rename("ref_est_zbp").reset_index().rename(columns={"GEOID_TRACT_20": "GEOID"})
t.to_parquet("data/processed/zbp_tract.parquet", index=False)
c = pd.read_csv(f"{raw}/cbp23co.txt", dtype={"fipstate": str, "fipscty": str, "naics": str})
c = c[c.naics.str.startswith("------")]
c["county"] = c.fipstate + c.fipscty
c[["county", "est"]].rename(columns={"est": "ref_est_cbp"}).to_parquet("data/processed/cbp_county.parquet", index=False)
print(len(t), t.ref_est_zbp.sum(), len(c))
