"""Random vs. spatial-block vs. leave-one-region-out cross-validation.

The gap between random CV and spatial CV quantifies how much ordinary
validation overstates performance on spatially autocorrelated data.
"""

from __future__ import annotations

import geopandas as gpd
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, KFold


def spatial_blocks(gdf: gpd.GeoDataFrame, block_km: float, crs: str = "EPSG:5070") -> pd.Series:
    """Assign each tract to a square grid block by its centroid."""
    c = gdf.to_crs(crs).geometry.centroid
    size = block_km * 1000
    return (np.floor(c.x / size).astype(int).astype(str) + "_" +
            np.floor(c.y / size).astype(int).astype(str))


def _cv(X, y, splitter, groups=None, seed=42):
    preds = np.zeros(len(y))
    for tr, te in splitter.split(X, y, groups):
        m = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, random_state=seed, verbose=-1)
        m.fit(X.iloc[tr], y.iloc[tr])
        preds[te] = m.predict(X.iloc[te])
    return {"r2": r2_score(y, preds), "mae": mean_absolute_error(y, preds)}


def compare_cv(df: pd.DataFrame, features, target, block_ids, region_ids, n_folds=5, seed=42):
    """Return a table of R2/MAE (log scale) under three CV schemes."""
    X, y = df[features], np.log1p(df[target])
    rows = {
        "random": _cv(X, y, KFold(n_folds, shuffle=True, random_state=seed), seed=seed),
        "spatial_block": _cv(X, y, GroupKFold(n_folds), groups=block_ids, seed=seed),
    }
    n_regions = pd.Series(region_ids).nunique()
    if n_regions >= 2:
        rows["leave_one_region_out"] = _cv(X, y, GroupKFold(n_regions), groups=region_ids, seed=seed)
    return pd.DataFrame(rows).T
