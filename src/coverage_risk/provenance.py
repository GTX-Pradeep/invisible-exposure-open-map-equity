"""Source-provenance features per tract.

Input: long table with columns GEOID, src, n (count of features from each
source in each tract). Output: one row per tract with
  - n_total             total features
  - n_sources           number of distinct sources
  - source_entropy      Shannon entropy of the source mix (bits)
  - source_hhi          Herfindahl concentration (1 = single source)
  - top_source_share    share of the dominant source
  - single_source       True if top_source_share >= threshold
  - share_<src>         share of each source
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def provenance_features(
    long_counts: pd.DataFrame, single_source_threshold: float = 0.95, prefix: str = ""
) -> pd.DataFrame:
    df = long_counts.copy()
    df["src"] = df["src"].fillna("unknown")
    wide = df.pivot_table(index="GEOID", columns="src", values="n", aggfunc="sum", fill_value=0)
    total = wide.sum(axis=1)
    shares = wide.div(total.replace(0, np.nan), axis=0).fillna(0)

    with np.errstate(divide="ignore", invalid="ignore"):
        ent = -(shares * np.log2(shares.where(shares > 0))).sum(axis=1)

    out = pd.DataFrame(
        {
            "n_total": total,
            "n_sources": (wide > 0).sum(axis=1),
            "source_entropy": ent.fillna(0).abs(),
            "source_hhi": (shares**2).sum(axis=1),
            "top_source_share": shares.max(axis=1),
        }
    )
    out["single_source"] = out["top_source_share"] >= single_source_threshold
    share_cols = shares.add_prefix("share_")
    out = out.join(share_cols)
    if prefix:
        out = out.add_prefix(prefix)
    return out.reset_index()
