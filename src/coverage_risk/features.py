"""Structural (neutral) tract covariates from the ACS 5-year Table-Based Summary File.

Design rule: only physical / demographic-size facts that determine how many buildings and
places *should* exist enter the expectation model.  Vulnerability, rurality, tribal and hazard
variables are listed in AUDIT_ONLY_PREFIXES and are refused by model.assert_no_leakage().
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests

ACS_DIR = Path("data/raw/acs")

# column prefixes that must never be model inputs (joined only in the audit phase)
AUDIT_ONLY_PREFIXES = (
    "svi_", "cvi_", "ruca", "rucc", "nchs", "ur_", "urban", "rural", "tribal", "aiannh",
    "usdm_", "spi", "pmdi", "drought", "epht_", "heat", "nasa_", "wonder", "cdc_",
    "usfs_", "carbonplan", "cp_", "mtbs_", "nifc_", "fpa_", "usgs_", "fire", "wildfire",
    "ref_", "region", "hwd_", "gehe_", "uhe_", "ghcn_", "fod_", "pop_urban", "pop_rural", "pct_urban",
    "cdcw_", "usdm", "pmdi_", "spi_", "carbonplan_", "fod",
)

TABLES = ["b25001", "b25002", "b25024", "b01003", "b25034", "b11001", "b26001"]


def fetch_acs(year: int = 2024, tables=TABLES, base: str | None = None) -> None:
    base = base or f"https://www2.census.gov/programs-surveys/acs/summary_file/{year}/table-based-SF/data/5YRData"
    ACS_DIR.mkdir(parents=True, exist_ok=True)
    for t in tables:
        out = ACS_DIR / f"acsdt5y{year}-{t}.tracts.parquet"
        if out.exists():
            continue
        raw = ACS_DIR / f"acsdt5y{year}-{t}.dat"
        if not raw.exists():
            with requests.get(f"{base}/acsdt5y{year}-{t}.dat", stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(raw, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        df = pd.read_csv(raw, sep="|", dtype={"GEO_ID": str}, low_memory=False)
        df = df[df.GEO_ID.str.startswith("1400000US")].copy()
        df["GEOID"] = df.GEO_ID.str[-11:]
        keep = ["GEOID"] + [c for c in df.columns if "_E" in c]
        df[keep].to_parquet(out, index=False)
        raw.unlink()


def load_acs(year: int = 2024) -> pd.DataFrame:
    dfs = [pd.read_parquet(ACS_DIR / f"acsdt5y{year}-{t}.tracts.parquet") for t in TABLES]
    df = dfs[0]
    for d in dfs[1:]:
        df = df.merge(d, on="GEOID", how="outer")
    for c in df.columns:
        if c != "GEOID":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def structural_features(acs: pd.DataFrame, land_km2: pd.Series) -> pd.DataFrame:
    """Return GEOID + structural covariates (counts, shares, densities)."""
    a = acs
    f = pd.DataFrame({"GEOID": a.GEOID})
    hu = a["B25001_E001"]
    f["hu"] = hu
    f["pop"] = a["B01003_E001"]
    f["households"] = a["B11001_E001"]
    f["gq_pop"] = a["B26001_E001"]
    f["vacant_share"] = a["B25002_E003"] / hu.replace(0, np.nan)
    # units in structure (B25024): physical housing stock
    names = {2: "u1_det", 3: "u1_att", 4: "u2", 5: "u3_4", 6: "u5_9", 7: "u10_19", 8: "u20_49", 9: "u50p", 10: "u_mobile", 11: "u_boat_rv"}
    for k, n in names.items():
        f[n] = a[f"B25024_E{k:03d}"]
    # rough structure-equivalents implied by the housing stock
    f["struct_equiv"] = (f.u1_det + f.u1_att / 2 + f.u_mobile + f.u_boat_rv + f.u2 / 2 + f.u3_4 / 3.5
                         + f.u5_9 / 7 + f.u10_19 / 14 + f.u20_49 / 30 + f.u50p / 80)
    for n in names.values():
        f[f"sh_{n}"] = f[n] / hu.replace(0, np.nan)
    # year built (B25034): new construction is plausibly under-mapped
    yb = {2: "yb2020p", 3: "yb2010", 4: "yb2000", 5: "yb1990", 6: "yb1980", 7: "yb1970", 8: "yb1960", 9: "yb1950", 10: "yb1940", 11: "yb1939m"}
    for k, n in yb.items():
        f[f"sh_{n}"] = a[f"B25034_E{k:03d}"] / hu.replace(0, np.nan)
    f["land_km2"] = land_km2.values
    f["log_land_km2"] = np.log1p(f.land_km2)
    f["hu_density"] = hu / f.land_km2.replace(0, np.nan)
    f["pop_density"] = f["pop"] / f.land_km2.replace(0, np.nan)
    f["log_hu"] = np.log1p(hu)
    f["log_pop"] = np.log1p(f["pop"])
    f["log_struct_equiv"] = np.log1p(f.struct_equiv)
    f["log_hu_density"] = np.log1p(f.hu_density)
    return f


HOUSING_TYPE_COLS = [c for c in [
    "u1_det", "u1_att", "u2", "u3_4", "u5_9", "u10_19", "u20_49", "u50p", "u_mobile", "u_boat_rv",
    "struct_equiv", "log_struct_equiv"]] + [f"sh_{n}" for n in [
    "u1_det", "u1_att", "u2", "u3_4", "u5_9", "u10_19", "u20_49", "u50p", "u_mobile", "u_boat_rv"]]


LODES_DIR = Path("data/raw/lodes")
# NAICS sector job counts only (no worker race/sex/earnings/education columns)
LODES_SECTORS = {"CNS01": "ag", "CNS07": "retail", "CNS12": "prof", "CNS15": "educ", "CNS16": "health",
                 "CNS17": "arts", "CNS18": "food_accom", "CNS19": "oth_serv", "CNS20": "pubadmin"}


def load_lodes(states=("az", "ca", "nm", "ok", "tx", "wa"), year: int = 2022) -> pd.DataFrame:
    """LODES 8 workplace-area job counts (2020 blocks) aggregated to tracts."""
    parts = []
    for st in states:
        d = pd.read_csv(LODES_DIR / f"{st}_wac_S000_JT00_{year}.csv.gz", dtype={"w_geocode": str},
                        usecols=["w_geocode", "C000", *LODES_SECTORS])
        d["GEOID"] = d.w_geocode.str[:11]
        parts.append(d.drop(columns="w_geocode").groupby("GEOID").sum())
    j = pd.concat(parts).groupby(level=0).sum().reset_index()
    out = pd.DataFrame({"GEOID": j.GEOID, "jobs": j.C000})
    for c, n in LODES_SECTORS.items():
        out[f"jobs_{n}"] = j[c]
        out[f"jsh_{n}"] = j[c] / j.C000.replace(0, np.nan)
    out["log_jobs"] = np.log1p(out.jobs)
    out["log_jobs_retail_food"] = np.log1p(out.jobs_retail + out.jobs_food_accom)
    return out


JOB_COLS = ["jobs", "log_jobs", "log_jobs_retail_food", "job_density"] + [f"jobs_{n}" for n in LODES_SECTORS.values()] + [
    f"jsh_{n}" for n in LODES_SECTORS.values()]
