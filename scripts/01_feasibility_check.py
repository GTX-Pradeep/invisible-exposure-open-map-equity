"""Feasibility check for one state.

Counts Overture buildings (with source mix) and USA Structures buildings per
census tract, joins ACS housing units, and plots Overture vs. reference.

If most tracts sit near the 1:1 line but a meaningful share falls clearly
below it, there is real coverage-gap signal and the project is viable for
buildings. If they agree almost perfectly everywhere, shift focus to POIs.

Usage:
    python scripts/01_feasibility_check.py --state AZ
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from coverage_risk import PROJECT_ROOT, load_config
from coverage_risk.aggregate import (
    connect,
    overture_buildings_by_tract,
    reference_buildings_by_tract,
    register_tracts,
)
from coverage_risk.features import fetch_acs, load_tracts
from coverage_risk.provenance import provenance_features

STATE_FIPS = {"AZ": "04", "CA": "06", "GA": "13", "OK": "40", "TX": "48",
              "OR": "41", "MT": "30", "NM": "35"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=None)
    ap.add_argument("--skip-reference", action="store_true",
                    help="Skip USA Structures (e.g., before its path is confirmed)")
    args = ap.parse_args()

    cfg = load_config()
    state = args.state or cfg["pilot_state"]
    fips = STATE_FIPS[state]
    processed = PROJECT_ROOT / cfg["paths"]["processed"]
    figures = PROJECT_ROOT / cfg["paths"]["figures"]
    processed.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Loading tracts for {state}")
    tracts = load_tracts(state, year=cfg["acs"]["year"], equal_area_crs=cfg["crs"]["equal_area"])

    print("[2/5] Fetching ACS")
    acs = fetch_acs(fips, cfg["acs"]["variables"], cfg["acs"]["year"], os.getenv("CENSUS_API_KEY"))

    con = connect(cfg["overture"]["s3_region"])
    bbox = register_tracts(con, tracts)

    print("[3/5] Counting Overture buildings per tract (this can take a while)")
    bpath = cfg["overture"]["buildings_path"].format(release=cfg["overture"]["release"])
    b_long = overture_buildings_by_tract(con, bpath, bbox)
    b_prov = provenance_features(b_long, prefix="bld_")

    df = tracts.drop(columns="geometry").merge(acs, on="GEOID", how="left")
    df = df.merge(b_prov, on="GEOID", how="left")
    df["bld_n_total"] = df["bld_n_total"].fillna(0)

    if not args.skip_reference:
        print("[4/5] Counting USA Structures per tract")
        ref = reference_buildings_by_tract(con, cfg["reference"]["usa_structures_path"], bbox)
        df = df.merge(ref, on="GEOID", how="left")
        df["n_ref_buildings"] = df["n_ref_buildings"].fillna(0)

    out = processed / f"feasibility_{state}.parquet"
    df.to_parquet(out, index=False)
    print(f"Saved {out}")

    print("[5/5] Summary and plot")
    print(df[["bld_n_total", "total_housing_units", "bld_n_sources", "bld_source_entropy"]].describe())
    print(f"Single-source tracts: {df['bld_single_source'].mean():.1%}")

    if "n_ref_buildings" in df:
        d = df[(df.n_ref_buildings > 0)]
        ratio = d.bld_n_total / d.n_ref_buildings
        print(f"Overture/reference ratio: median {ratio.median():.2f}; "
              f"tracts below 0.8: {(ratio < 0.8).mean():.1%}")
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(np.log1p(d.n_ref_buildings), np.log1p(d.bld_n_total), s=4, alpha=0.4)
        lim = [0, max(np.log1p(d.n_ref_buildings).max(), np.log1p(d.bld_n_total).max())]
        ax.plot(lim, lim, "k--", lw=1)
        ax.set_xlabel("log(1 + USA Structures buildings)")
        ax.set_ylabel("log(1 + Overture buildings)")
        ax.set_title(f"{state}: Overture vs. reference buildings per tract")
        fig.tight_layout()
        fig.savefig(figures / f"feasibility_{state}_buildings.png", dpi=150)
        print(f"Saved plot to {figures}")


if __name__ == "__main__":
    main()
