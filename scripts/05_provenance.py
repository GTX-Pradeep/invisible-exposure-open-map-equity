"""Phase 5 (H4): do provenance / source-mix features improve detection of reference-defined gaps?
Spatial-block CV; out-of-fold probabilities; block-bootstrap CI for the PR-AUC / ROC-AUC difference."""
import json
import lightgbm as lgb
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import average_precision_score, roc_auc_score
from coverage_risk.model import STRUCTURAL, make_folds, spatial_blocks

cfg = yaml.safe_load(open("config/config.yaml")); mc = cfg["model"]
d = pd.read_parquet("data/processed/validation_frame.parquet")
PROV_B = ["bsh_osm", "bsh_msft", "bsh_google", "bsh_esri", "b_src_entropy", "b_src_max_share", "b_single_source", "b_ml_share"]
PROV_P = ["psh_meta", "psh_msft", "psh_fsq", "p_src_entropy", "p_src_max_share", "p_single_source", "p_conf50_share"]
params = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=30, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.8, verbose=-1)
rows, store = [], {}
for layer, truth, prov in [("bldg", "ref_gap_b", PROV_B + PROV_P), ("poi", "ref_gap_p", PROV_P + PROV_B)]:
    s = d[d[truth].notna() & (d.ref_bldg.notna() if layer == "bldg" else d.ref_ratio_p.notna())].reset_index(drop=True)
    y = s[truth].astype(int).values
    base = STRUCTURAL + [f"{layer}_deficit_z", f"{layer}_q_med", f"{layer}_y_log"]
    folds = make_folds(s, "spatial", k=10, seed=mc["seed"], km=mc["spatial_block_km"])
    probs = {}
    for name, feats in [("structural+deficit", base), ("+provenance", base + prov)]:
        p = np.zeros(len(s))
        for f in np.unique(folds):
            tr, te = folds != f, folds == f
            m = lgb.LGBMClassifier(random_state=mc["seed"], **params).fit(s.loc[tr, feats].astype(float), y[tr])
            p[te] = m.predict_proba(s.loc[te, feats].astype(float))[:, 1]
        probs[name] = p
    blocks = spatial_blocks(s.lat, s.lon, mc["spatial_block_km"])
    ub = np.unique(blocks); idx = {b: np.where(blocks == b)[0] for b in ub}
    rng = np.random.default_rng(mc["seed"])
    dpr, dauc = [], []
    for _ in range(1000):
        ii = np.concatenate([idx[b] for b in rng.choice(ub, len(ub))])
        if y[ii].sum() == 0:
            continue
        dpr.append(average_precision_score(y[ii], probs["+provenance"][ii]) - average_precision_score(y[ii], probs["structural+deficit"][ii]))
        dauc.append(roc_auc_score(y[ii], probs["+provenance"][ii]) - roc_auc_score(y[ii], probs["structural+deficit"][ii]))
    r = {"layer": layer, "n": len(s), "prevalence": y.mean()}
    for name, p in probs.items():
        r[f"pr_auc[{name}]"] = average_precision_score(y, p); r[f"roc_auc[{name}]"] = roc_auc_score(y, p)
    r["d_pr_auc"] = r["pr_auc[+provenance]"] - r["pr_auc[structural+deficit]"]
    r["d_pr_auc_ci"] = list(np.percentile(dpr, [2.5, 97.5]))
    r["d_roc_auc"] = r["roc_auc[+provenance]"] - r["roc_auc[structural+deficit]"]
    r["d_roc_auc_ci"] = list(np.percentile(dauc, [2.5, 97.5]))
    # importance of provenance features in full model
    m = lgb.LGBMClassifier(random_state=mc["seed"], **params).fit(s[base + prov].astype(float), y)
    imp = pd.Series(m.booster_.feature_importance("gain"), index=base + prov)
    r["provenance_gain_share"] = float(imp[prov].sum() / imp.sum())
    r["top_features"] = imp.sort_values(ascending=False).head(8).round(0).to_dict()
    rows.append(r)
    # descriptive: gap rate by building single-source status / dominant source
    if layer == "bldg":
        s["dominant"] = s[["bsh_osm", "bsh_msft", "bsh_google", "bsh_esri"]].fillna(0).assign(bsh_none=1e-9).idxmax(axis=1).str.replace("bsh_", "")
        tab = s.groupby("dominant").agg(n=(truth, "size"), gap_rate=(truth, "mean"), flag_rate=("bldg_flag", "mean"))
        tab.to_csv("outputs/tables/h4_gap_by_dominant_source.csv"); print(tab)
json.dump(rows, open("outputs/tables/h4_provenance.json", "w"), indent=2, default=float)
print(json.dumps(rows, indent=2, default=float))
