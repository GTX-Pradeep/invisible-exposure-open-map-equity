"""Phase 2: one row per tract — structural covariates, Overture counts + provenance, references.
Audit strata are written to a SEPARATE file and never merged here."""
import numpy as np
import pandas as pd
import yaml

from coverage_risk import aggregate as ag
from coverage_risk.features import load_acs, load_lodes, structural_features
from coverage_risk.provenance import provenance_features

cfg = yaml.safe_load(open("config/config.yaml"))
P = "data/processed"
tracts = ag.load_tracts(cfg["regions"])
spine = pd.read_parquet("data/raw/challenge/strata/national/national-census-tract-table.parquet")
spine = tracts[["GEOID", "region"]].merge(spine[["GEOID", "ALAND", "INTPTLAT", "INTPTLON"]], on="GEOID", how="left")

acs = load_acs(cfg["acs"]["year"])
acs = spine[["GEOID"]].merge(acs, on="GEOID", how="left")
feat = structural_features(acs, spine.ALAND / 1e6)
feat = feat.merge(load_lodes(), on="GEOID", how="left")
jc = [c for c in feat.columns if c.startswith(("jobs", "log_jobs"))]
feat[jc] = feat[jc].fillna(0)
feat["job_density"] = feat.jobs / feat.land_km2.replace(0, np.nan)

b = pd.read_parquet(f"{P}/overture_r2026a_buildings.parquet")
p = pd.read_parquet(f"{P}/overture_r2026a_places.parquet")
ov = b.merge(p, on="GEOID")
prov = provenance_features(ov, "r2026a")

ref = pd.read_parquet(f"{P}/usa_structures_tract.parquet")
zbp = pd.read_parquet(f"{P}/zbp_tract.parquet")

df = (spine.merge(feat, on="GEOID").merge(ov, on="GEOID").merge(prov, on="GEOID")
      .merge(ref, on="GEOID", how="left").merge(zbp, on="GEOID", how="left"))
df["county"] = df.GEOID.str[:5]
df["lat"] = pd.to_numeric(df.INTPTLAT); df["lon"] = pd.to_numeric(df.INTPTLON)
df = df.drop(columns=["INTPTLAT", "INTPTLON"])
# exit checks
miss = df[["hu", "pop", "land_km2"]].isna().sum()
print("missing structural:", miss.to_dict())
print(df.shape, df.region.value_counts().to_dict())
df.to_parquet(f"{P}/tracts_all.parquet", index=False)

# audit strata (kept apart from the model table)
cols = ["GEOID", "pop_total", "pct_urban", "ur_class", "svi_overall", "svi_socioeconomic", "svi_household",
        "svi_minority", "svi_housing_transport", "cvi_overall", "cvi_climate", "cvi_baseline", "ruca_primary", "rucc_2023",
        "rucc_metro", "nchs_2013", "tribal_any", "tribal_pct", "tribal_legal", "usdm_summer_dsci", "usdm_summer_pct_d2plus",
        "epht_heat_days_summer", "hwd_heatindex_mean", "gehe_wbgt30_days_mean", "usfs_WHP_mean", "usfs_BP_mean",
        "usfs_RPS_mean", "usfs_Exposure_mean", "usfs_BuildingCount_sum", "usfs_HUCount_sum", "carbonplan_bp_2011_mean",
        "carbonplan_rps_2011_mean", "carbonplan_buildings", "mtbs_wildfire_burned_pct_land", "mtbs_wildfire_ever",
        "fod_ignition_density", "pmdi_pct_months_severe", "spi12_pct_months_d2"]
st = pd.read_parquet("data/raw/challenge/strata/national/national-strata-tract-table.parquet", columns=cols)
st = tracts[["GEOID", "region"]].merge(st, on="GEOID", how="left")
st.to_parquet(f"{P}/strata_audit.parquet", index=False)
print("strata", st.shape, st.isna().mean().round(3)[st.isna().mean() > 0].to_dict())
