"""Write docs/DATA_DICTIONARY.md: every column of the tract model table (data/processed/tracts_all.parquet, released as
deliverables/dataset/tracts_model_table.csv) with its role, source, meaning, unit, missing count and range."""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from coverage_risk.model import STRUCTURAL

src = Path("data/processed/tracts_all.parquet")
d = pd.read_parquet(src) if src.exists() else pd.read_csv("deliverables/dataset/tracts_model_table.csv", dtype={"GEOID": str, "county": str})
UNITS = {"u1_det": "1-unit detached", "u1_att": "1-unit attached", "u2": "2 units", "u3_4": "3-4 units", "u5_9": "5-9 units",
         "u10_19": "10-19 units", "u20_49": "20-49 units", "u50p": "50+ units", "u_mobile": "mobile home", "u_boat_rv": "boat, RV, van"}
YB = {"yb2020p": "2020 or later", "yb2010": "2010-2019", "yb2000": "2000-2009", "yb1990": "1990-1999", "yb1980": "1980-1989",
      "yb1970": "1970-1979", "yb1960": "1960-1969", "yb1950": "1950-1959", "yb1940": "1940-1949", "yb1939m": "1939 or earlier"}
SECT = {"ag": "agriculture, forestry, fishing (NAICS 11)", "retail": "retail trade (44-45)", "prof": "professional, scientific, technical (54)",
        "educ": "educational services (61)", "health": "health care and social assistance (62)", "arts": "arts, entertainment, recreation (71)",
        "food_accom": "accommodation and food services (72)", "oth_serv": "other services (81)", "pubadmin": "public administration (92)"}
BSRC = {"osm": "OpenStreetMap", "msft": "Microsoft ML Buildings", "google": "Google Open Buildings", "esri": "Esri Community Maps", "other": "any other source"}
PSRC = {"meta": "Meta", "msft": "Microsoft", "fsq": "Foursquare", "osm": "OpenStreetMap"}
EXACT = {
    "GEOID": ("identifier", "Census 2020", "census tract ID; keep as 11-character text (leading zero)", "-"),
    "region": ("identifier", "challenge", "study region", "-"),
    "county": ("identifier", "derived", "5-digit county FIPS (first 5 characters of GEOID); cluster for bootstrap", "-"),
    "lat": ("geometry", "Census spine INTPTLAT", "internal point latitude; used for spatial blocks only", "degrees"),
    "lon": ("geometry", "Census spine INTPTLON", "internal point longitude; used for spatial blocks only", "degrees"),
    "ALAND": ("structural", "Census spine", "land area", "m²"),
    "land_km2": ("structural", "Census spine", "land area (ALAND / 10⁶)", "km²"),
    "log_land_km2": ("structural", "derived", "log(1 + land_km2)", "-"),
    "hu": ("structural", "ACS B25001", "housing units", "count"),
    "pop": ("structural", "ACS B01003", "total population", "people"),
    "households": ("structural", "ACS B11001", "households (occupied housing units)", "count"),
    "gq_pop": ("structural", "ACS B26001", "population in group quarters (prisons, dormitories, bases, care homes)", "people"),
    "vacant_share": ("structural", "ACS B25002", "vacant / all housing units", "share"),
    "struct_equiv": ("structural", "derived from B25024", "rough number of residential structures implied by the housing stock (units per structure assumed by type)", "count"),
    "log_struct_equiv": ("structural", "derived", "log(1 + struct_equiv)", "-"),
    "hu_density": ("structural", "derived", "housing units per km² of land", "per km²"),
    "pop_density": ("structural", "derived", "residents per km² of land", "per km²"),
    "log_hu": ("structural", "derived", "log(1 + hu)", "-"), "log_pop": ("structural", "derived", "log(1 + pop)", "-"),
    "log_hu_density": ("structural", "derived", "log(1 + hu_density)", "-"),
    "jobs": ("structural", "LODES 2022 WAC C000", "jobs located in the tract (all jobs, all workers)", "jobs"),
    "log_jobs": ("structural", "derived", "log(1 + jobs)", "-"),
    "log_jobs_retail_food": ("structural", "derived", "log(1 + retail + accommodation/food jobs)", "-"),
    "job_density": ("structural", "derived", "jobs per km² of land", "per km²"),
    "r2026a_bldg": ("outcome (buildings)", "Overture 2026-08-19.0", "buildings whose bounding-box centre lies in the tract (all sizes)", "count"),
    "r2026a_bldg450": ("outcome (buildings)", "Overture 2026-08-19.0", "same, footprint ≥ 41.8 m² (450 sq ft, the USA Structures threshold); the modelled building count", "count"),
    "r2026a_area_m2": ("descriptive", "Overture 2026-08-19.0", "total footprint area of the tract's buildings", "m²"),
    "r2026a_area_med": ("descriptive", "Overture 2026-08-19.0", "median footprint area (missing if no building)", "m²"),
    "r2026a_poi": ("outcome (places)", "Overture 2026-08-19.0", "places (POIs) in the tract; the modelled place count", "count"),
    "r2026a_poi_conf50": ("descriptive", "Overture 2026-08-19.0", "places with confidence ≥ 0.5", "count"),
    "r2026a_poi_multisrc": ("descriptive", "Overture 2026-08-19.0", "places backed by at least 2 source records", "count"),
    "b_src_entropy": ("provenance", "derived", "Shannon entropy (bits) of the building source shares; 0 = one source", "bits"),
    "b_src_max_share": ("provenance", "derived", "share of buildings from the largest source", "share"),
    "b_single_source": ("provenance", "derived", "1 if one source supplies ≥ 90% of buildings (not strictly a single source)", "0/1"),
    "b_ml_share": ("provenance", "derived", "share of machine-learned footprints (Microsoft + Google)", "share"),
    "p_src_entropy": ("provenance", "derived", "Shannon entropy (bits) of the place source shares (Meta, Microsoft, Foursquare)", "bits"),
    "p_src_max_share": ("provenance", "derived", "share of places from the largest of those sources", "share"),
    "p_single_source": ("provenance", "derived", "1 if one source supplies ≥ 90% of places", "0/1"),
    "p_conf50_share": ("provenance", "derived", "share of places with confidence ≥ 0.5", "share"),
    "ref_bldg": ("reference (validation only)", "FEMA/ORNL USA Structures v1", "structures ≥ 450 sq ft in the tract", "count"),
    "ref_res": ("reference (validation only)", "USA Structures OCC_CLS", "residential structures", "count"),
    "ref_nonres": ("reference (validation only)", "USA Structures OCC_CLS", "commercial, industrial, assembly, education and government structures", "count"),
    "ref_outbldg": ("reference (validation only)", "USA Structures OUTBLDG", "structures flagged as outbuildings", "count"),
    "ref_area_m2": ("reference (validation only)", "USA Structures SQMETERS", "total structure footprint area", "m²"),
    "ref_img_min": ("reference (validation only)", "USA Structures IMAGE_DATE", "earliest imagery date of the tract's structures", "date"),
    "ref_img_max": ("reference (validation only)", "USA Structures IMAGE_DATE", "latest imagery date", "date"),
    "ref_est_zbp": ("reference (validation only)", "ZIP Business Patterns 2023 + ZCTA-tract file", "establishments allocated to the tract by ZCTA land share (approximate)", "establishments"),
}


def describe(c):
    if c in EXACT:
        return EXACT[c]
    m = re.fullmatch(r"(sh_)?(u\w+)", c)
    if m and m.group(2) in UNITS:
        return ("structural", "ACS B25024", f"housing units in structures of type: {UNITS[m.group(2)]}" + (" / all housing units" if m.group(1) else ""), "share" if m.group(1) else "count")
    if c.startswith("sh_yb") and c[3:] in YB:
        return ("structural", "ACS B25034", f"housing units built {YB[c[3:]]} / all housing units", "share")
    if c.startswith(("jobs_", "jsh_")) and c.split("_", 1)[1] in SECT:
        k = c.split("_", 1)[1]
        return ("structural", "LODES 2022 WAC", f"jobs in {SECT[k]}" + (" / all jobs" if c.startswith("jsh_") else ""), "share" if c.startswith("jsh_") else "jobs")
    if c.startswith("r2026a_src_"):
        return ("provenance", "Overture 2026-08-19.0", f"buildings whose first source record is {BSRC[c[11:]]}", "count")
    if c.startswith("r2026a_psrc_"):
        return ("provenance", "Overture 2026-08-19.0", f"places whose first source record is {PSRC[c[12:]]}", "count")
    if c.startswith("bsh_"):
        return ("provenance", "derived", f"share of buildings from {BSRC[c[4:]]}", "share")
    if c.startswith("psh_"):
        return ("provenance", "derived", f"share of places from {PSRC[c[4:]]}", "share")
    return ("?", "?", "?", "?")


rows = []
for c in d.columns:
    role, source, meaning, unit = describe(c)
    if c in STRUCTURAL:
        role = "model input"
    x = d[c]
    num = pd.api.types.is_numeric_dtype(x) and not pd.api.types.is_bool_dtype(x)
    rng = f"{np.nanmin(x):,.3g} / {np.nanmedian(x):,.3g} / {np.nanmax(x):,.3g}" if num and x.notna().any() else (f"{x.dropna().astype(str).min()} to {x.dropna().astype(str).max()}" if c.startswith("ref_img") else "")
    rows.append({"column": f"`{c}`", "role": role, "source": source, "meaning": meaning, "unit": unit, "missing": int(x.isna().sum()), "min / median / max": rng})
t = pd.DataFrame(rows)
unknown = t[t.role == "?"]
assert unknown.empty, f"undocumented columns: {unknown.column.tolist()}"
roles = t.role.value_counts()
lines = ["# Data dictionary: tract model table", "",
         f"`data/processed/tracts_all.parquet` (built by `scripts/02_build_tract_table.py`; released as `deliverables/dataset/tracts_model_table.csv`): "
         f"{len(d):,} rows (one per study tract), {d.shape[1]} columns. Generated by `scripts/13_data_dictionary.py` from the table itself, so the "
         "missing counts and ranges are exact.", "",
         "**Roles.** *model input*: in `coverage_risk.model.STRUCTURAL`, the only columns the expectation model may use. *structural*: built "
         "from the same sources but not a model input. *outcome*: the counts the model predicts. *provenance*: where the map's features "
         "come from (used in H4 and descriptives, never as model inputs). *reference*: independent counts used only to validate. "
         "Audit strata (SVI, CVI, rurality, tribal, hazards) are deliberately **not** in this table; they are in `data/processed/strata_audit.parquet`.", "",
         "Counts by role: " + ", ".join(f"{k} {v}" for k, v in roles.items()) + ".", "",
         "Conventions: ratios use a zero-safe denominator, so a tract with no housing units has missing (not infinite) shares; "
         "`log` means natural log of (1 + x). The 2023 and 2026-10 counts (`r2023_*`, `r2026b_*`) are added later in `scripts/07_catchup.py`.", ""]
lines.append("| " + " | ".join(t.columns) + " |"); lines.append("|" + "---|" * len(t.columns))
for r in t.itertuples(index=False):
    lines.append("| " + " | ".join(str(v).replace("|", "/") for v in r) + " |")
Path("docs/DATA_DICTIONARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote docs/DATA_DICTIONARY.md:", len(t), "columns;", roles.to_dict())
