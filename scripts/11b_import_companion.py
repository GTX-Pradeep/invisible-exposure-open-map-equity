"""Merged project, step 3: copy the few companion-pipeline summaries the paper quotes into data/external/companion/,
so the repository reproduces its own numbers without ../MapEquityChallenge.

Sources (MapEquityChallenge/academic_research, SHA-256 logged in data/external/companion/sources.json):
  ablation_benchmarks/cache/oof_predictions.parquet      out-of-fold expectations for six map layers (spatial / LORO folds)
  ablation_benchmarks/tables/table_A_models.csv          model-family comparison under spatial folds (notebook 03)
  shared_inputs/risk/frozen_spatial_oof_risk.parquet     MapEquity's frozen peer-normalised risk scores
Writes:
  layer_predictability.csv   best relative RMSE (RMSE / SD of the count) per layer and design
  highway_transfer.csv       predicted / observed highway length per held-out region (Tweedie, leave-one-region-out)
  provenance_beyond_counts.csv  change in error when peer-theme provenance is added (spatial_and_novelty notebook 07 output)
  mapequity_risk.csv         GEOID + MapEquity building shortfall, combined risk and non-POI risk (for scripts/14)
Nothing here is ever an input to the expectation model (tests/test_core.py checks the prefixes)."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

MEC = Path(yaml.safe_load(open("config/config.yaml"))["merge"]["mapequity_root"]).resolve()
AR = MEC / "academic_research"
OUT = Path("data/external/companion"); OUT.mkdir(parents=True, exist_ok=True)
src = {}


def use(p: Path) -> Path:
    src[str(p.relative_to(MEC))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


c = pd.read_parquet(use(AR / "ablation_benchmarks/cache/oof_predictions.parquet"),
                    columns=["design", "region", "component", "model", "feature_set", "y", "mu"])
c = c[(c.feature_set == "B0") & ~c.model.isin(["region_mean", "region_median"])]
rows = []
for (des, comp, mod), g in c[c.design.isin(["random", "spatial", "loro"])].groupby(["design", "component", "model"], observed=True):
    rows.append({"design": des, "component": comp, "model": mod,
                 "rrmse": float(np.sqrt(((g.y - g.mu) ** 2).mean()) / g.y.std(ddof=0))})
r = pd.DataFrame(rows)
best = r.loc[r.groupby(["design", "component"]).rrmse.idxmin()].sort_values(["component", "design"])
best.round(4).to_csv(OUT / "layer_predictability.csv", index=False)

h = c[(c.design == "loro") & (c.component == "highways") & (c.model == "tweedie")]
(h.groupby("region", observed=True).mu.sum() / h.groupby("region", observed=True).y.sum()).rename("predicted_over_observed") \
    .round(4).reset_index().to_csv(OUT / "highway_transfer.csv", index=False)

# notebook spatial_and_novelty/07 (provenance beyond count-based peer signals, region held out); summary as printed there
pd.DataFrame({"target_theme": ["building", "poi", "road"],
              "delta_mae_plus_minus_base": [0.0025, 0.0056, 0.0015],
              "ci_low": [-0.0002, 0.0034, -0.0006], "ci_high": [0.0052, 0.0076, 0.0031]}) \
    .to_csv(OUT / "provenance_beyond_counts.csv", index=False)

k = pd.read_parquet(use(AR / "shared_inputs/risk/frozen_spatial_oof_risk.parquet"))
k[["GEOID", "building_shortfall", "risk_score", "non_poi_risk_score"]].to_csv(OUT / "mapequity_risk.csv", index=False)

json.dump({"sources_sha256": src, "note": "provenance_beyond_counts.csv transcribes the saved output of "
           "academic_research/spatial_and_novelty/notebooks/07 (4 decimals)."}, open(OUT / "sources.json", "w"), indent=2)
print(best.to_string(index=False)); print("written to", OUT)
