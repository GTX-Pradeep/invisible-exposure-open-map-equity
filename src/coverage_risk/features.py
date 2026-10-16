"""Tract geometry and ACS structural covariates.

Only *structural* variables belong in the expectation model. Vulnerability
and hazard variables (SVI, CVI, rurality, tribal, heat, wildfire, drought)
must be kept out and joined later for the audit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import requests

ACS_URL = "https://api.census.gov/data/{year}/acs/acs5"


def load_tracts(state: str, year: int = 2023, equal_area_crs: str = "EPSG:5070"):
    """Download tract polygons for a state via pygris; add land area (km^2)."""
    from pygris import tracts

    gdf = tracts(state=state, year=year, cb=True, cache=True)
    gdf = gdf[["GEOID", "ALAND", "geometry"]].copy()
    gdf["area_km2"] = gdf.to_crs(equal_area_crs).area / 1e6
    gdf["land_km2"] = gdf["ALAND"] / 1e6
    return gdf


def fetch_acs(state_fips: str, variables: dict, year: int = 2023, api_key: str | None = None):
    """Fetch ACS 5-year tract variables for a state. Returns renamed columns."""
    codes = list(variables.values())
    params = {"get": ",".join(codes), "for": "tract:*", "in": f"state:{state_fips}"}
    if api_key:
        params["key"] = api_key
    r = requests.get(ACS_URL.format(year=year), params=params, timeout=120)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["GEOID"] = df["state"] + df["county"] + df["tract"]
    df = df.rename(columns={v: k for k, v in variables.items()})
    num = list(variables.keys())
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    df[num] = df[num].where(df[num] >= 0)  # Census uses negative codes for missing
    return df[["GEOID", *num]]


def structural_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive model-ready structural features from ACS + geometry columns."""
    out = df.copy()
    hu = out["total_housing_units"].replace(0, np.nan)
    out["log_area_km2"] = np.log1p(out["land_km2"])
    out["log_housing_units"] = np.log1p(out["total_housing_units"])
    out["log_population"] = np.log1p(out["total_population"])
    out["log_hu_density"] = np.log1p(out["total_housing_units"] / out["land_km2"].clip(lower=0.01))
    out["share_single_family"] = (out["units_1_detached"] + out["units_1_attached"]) / hu
    out["share_small_multi"] = (out["units_2"] + out["units_3_4"] + out["units_5_9"]) / hu
    out["share_large_multi"] = (out["units_10_19"] + out["units_20_49"] + out["units_50_plus"]) / hu
    out["share_mobile_home"] = out["mobile_home"] / hu
    out["vacancy_rate"] = out["vacant_units"] / hu
    return out


STRUCTURAL_COLUMNS = [
    "log_area_km2",
    "log_housing_units",
    "log_population",
    "log_hu_density",
    "share_single_family",
    "share_small_multi",
    "share_large_multi",
    "share_mobile_home",
    "vacancy_rate",
]

# Never pass these to the expectation model.
AUDIT_ONLY_COLUMNS = ["svi", "cvi", "rurality", "tribal", "heat", "wildfire", "drought"]
