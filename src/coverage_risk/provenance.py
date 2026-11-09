"""Provenance (source-mix) features: which upstream datasets supply a tract's map features."""
import numpy as np
import pandas as pd

BLDG_SRC = ["osm", "msft", "google", "esri", "other"]
POI_SRC = ["meta", "msft", "fsq"]


def _entropy(shares: np.ndarray) -> np.ndarray:
    s = np.where(shares > 0, shares, 1)
    return -(np.where(shares > 0, shares * np.log2(s), 0)).sum(axis=1)


def provenance_features(df: pd.DataFrame, rel: str) -> pd.DataFrame:
    out = pd.DataFrame({"GEOID": df.GEOID})
    tot = df[f"{rel}_bldg"].replace(0, np.nan)
    sh = np.column_stack([df[f"{rel}_src_{s}"] / tot for s in BLDG_SRC])
    for i, s in enumerate(BLDG_SRC):
        out[f"bsh_{s}"] = sh[:, i]
    shz = np.nan_to_num(sh)
    out["b_src_entropy"] = np.where(tot.isna(), np.nan, _entropy(shz))
    out["b_src_max_share"] = np.where(tot.isna(), np.nan, shz.max(axis=1))
    out["b_single_source"] = (out.b_src_max_share >= 0.9).astype(float)
    out["b_ml_share"] = out.bsh_msft + out.bsh_google  # machine-learned footprints
    if f"{rel}_poi" in df:
        ptot = df[f"{rel}_poi"].replace(0, np.nan)
        psh = np.column_stack([df[f"{rel}_psrc_{s}"] / ptot for s in POI_SRC])
        for i, s in enumerate(POI_SRC):
            out[f"psh_{s}"] = psh[:, i]
        pz = np.nan_to_num(psh)
        out["p_src_entropy"] = np.where(ptot.isna(), np.nan, _entropy(pz))
        out["p_src_max_share"] = np.where(ptot.isna(), np.nan, pz.max(axis=1))
        out["p_single_source"] = (out.p_src_max_share >= 0.9).astype(float)
        out["p_conf50_share"] = df[f"{rel}_poi_conf50"] / ptot
    return out
