"""Phase 1/2: count Overture buildings + POIs (with provenance) per tract for one snapshot.

usage: python scripts/01_count_overture.py --release r2026a|r2026b|r2023 [--layer buildings|places|both]
"""
import argparse
import time
from pathlib import Path

import yaml

from coverage_risk import aggregate as ag
from coverage_risk.db import connect, source_coop_files

cfg = yaml.safe_load(open("config/config.yaml"))
ap = argparse.ArgumentParser()
ap.add_argument("--release", default="r2026a")
ap.add_argument("--layer", default="both")
a = ap.parse_args()

tracts = ag.load_tracts(cfg["regions"])
print(f"{len(tracts)} tracts")
con = connect()
out_dir = Path("data/processed"); out_dir.mkdir(parents=True, exist_ok=True)
rel = cfg["overture"]["releases"][a.release]

import pandas as pd

def run(kind, sql_fn):
    """sql_fn(tracts_subset) -> SQL. Remote sources run region by region with checkpoints."""
    t = time.time()
    path = out_dir / f"overture_{a.release}_{kind}.parquet"
    parts = []
    for reg, sub in tracts.groupby("region"):
        ck = out_dir / f"_ck_{a.release}_{kind}_{reg}.parquet"
        if not ck.exists():
            part = ag.count_points(sql_fn(sub), sub, a.release, "building" if kind == "buildings" else "poi", con=con)
            part.to_parquet(ck, index=False)
            print("  region", reg, f"{time.time()-t:.0f}s", flush=True)
        parts.append(pd.read_parquet(ck))
    df = pd.concat(parts, ignore_index=True)
    df.to_parquet(path, index=False)
    print(kind, path, f"{time.time()-t:.0f}s", df.drop(columns="GEOID").sum(numeric_only=True).round().to_dict())

if a.layer in ("buildings", "both"):
    if rel["source"] == "challenge":
        run("buildings", lambda sub: ag.challenge_buildings_sql([sub.region.iloc[0]]))
    elif rel["source"] == "s3":
        run("buildings", lambda sub: ag.s3_buildings_sql(rel["path"], sub))
    else:
        urls = source_coop_files("cholmes", "overture/geoparquet-country-quad-hive/country_iso=US/")
        run("buildings", lambda sub: ag.legacy2023_buildings_sql(urls, sub))
if a.layer in ("places", "both"):
    if rel["source"] == "challenge":
        run("places", lambda sub: ag.challenge_pois_sql([sub.region.iloc[0]]))
    elif rel["source"] == "s3":
        run("places", lambda sub: ag.s3_places_sql(cfg["overture"]["places_r2026b"], sub))
