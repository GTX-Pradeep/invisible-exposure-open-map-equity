"""Generates notebooks/Invisible_Exposure.ipynb (the course code deliverable)."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))
code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# Invisible Exposure: reference-free conformal auditing of open-map completeness

**Course project notebook (ADA).** This notebook walks through the whole pipeline: data, expectation model with conformal ranges, validation, the pre-registered equity audit, catch-up across Overture releases, and the release regression we found.

* Repository: https://github.com/GTX-Pradeep/invisible-exposure-open-map-equity
* The heavy data ingestion (Phase 1: streaming Overture releases from the cloud) is done by `scripts/01_count_overture.py` and takes about 30 minutes; set `RUN_INGEST = True` below to rerun it. Everything after it runs here in a few minutes.

**Problem statement.** Estimate, without a perfect reference map and with honest uncertainty, where Overture Maps is incomplete at census-tract level; convert the gaps into hidden heat, wildfire and drought exposure; and test, under a pre-registered plan, whether the gaps fall on socially vulnerable, rural and tribal communities and whether they close across releases.

**Design rule.** SVI, CVI, rurality, tribal and hazard variables never enter the model. They are joined only in the audit.""")

code("""import os, sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
os.chdir(ROOT); sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd, yaml
import matplotlib.pyplot as plt
from IPython.display import Image, display
pd.set_option("display.width", 160); pd.set_option("display.max_columns", 30)
cfg = yaml.safe_load(open("config/config.yaml"))
RUN_INGEST = False   # True: re-stream Overture/USA Structures from the cloud (~30 min, needs network)
print("project root:", ROOT); print("regions:", cfg["regions"])""")

md("""## 1. Data ingestion (Phase 1)
Per-tract counts of Overture buildings (all and >= 450 sq ft) and places, with their upstream source, for three releases; USA Structures reference counts; Business Patterns establishments. The commands are below; with `RUN_INGEST = False` the cached outputs in `data/processed/` are used.""")
code("""steps = ["bash scripts/fetch_challenge.sh", "bash scripts/fetch_inputs.sh",
         "python -c 'from coverage_risk.features import fetch_acs; fetch_acs()'",
         "python scripts/00b_usa_structures_counts.py", "python scripts/00c_poi_reference.py",
         "python scripts/01_count_overture.py --release r2026a", "python scripts/01_count_overture.py --release r2026b",
         "python scripts/01_count_overture.py --release r2023 --layer buildings", "python scripts/02_build_tract_table.py"]
if RUN_INGEST:
    for s in steps:
        print(">>", s); assert os.system(f"PYTHONPATH=src {s}") == 0
else:
    print("Using cached outputs. To rebuild, set RUN_INGEST = True. Steps:"); print("\\n".join(steps))""")

md("## 2. The tract table (Phase 2)")
code("""df = pd.read_parquet("data/processed/tracts_all.parquet")
strata = pd.read_parquet("data/processed/strata_audit.parquet")   # kept apart from the model table
print(df.shape, "| strata:", strata.shape)
df.groupby("region").agg(tracts=("GEOID", "size"), housing_units=("hu", "sum"),
    overture_buildings=("r2026a_bldg", "sum"), overture_places=("r2026a_poi", "sum"), usa_structures=("ref_bldg", "sum"))""")

md("### Feasibility gate: how complete is Overture against USA Structures?")
code("""s = df[df.ref_bldg.notna()]
ratio = s.r2026a_bldg450 / s.ref_bldg
print(f"log-scale correlation: {np.corrcoef(np.log1p(s.r2026a_bldg450), np.log1p(s.ref_bldg))[0,1]:.3f}")
print(f"median ratio: {ratio.median():.3f}   share of tracts below 80% of reference: {(ratio < 0.8).mean():.1%}")
fig, ax = plt.subplots(figsize=(5, 5))
ax.scatter(s.ref_bldg + 1, s.r2026a_bldg450 + 1, s=3, alpha=.3, color="#2a78d6")
lim = [1, 2e4]; ax.plot(lim, lim, "k-", lw=.8); ax.plot(lim, [0.8 * x for x in lim], "k--", lw=.8)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("USA Structures per tract (+1)"); ax.set_ylabel("Overture >=450 sq ft (+1)")
plt.show()""")

md("""## 3. Expectation model with conformal ranges (Phase 3)
LightGBM quantile regression on log counts, structural covariates only, cross-fitted on 50 km spatial blocks; conformalized quantile regression (CQR) gives a 90% range per tract. A tract is **flagged** when the map falls below the lower bound. The leakage guard refuses audit columns:""")
code("""from coverage_risk.model import STRUCTURAL, crossfit_cqr, make_folds, assert_no_leakage
try:
    assert_no_leakage(STRUCTURAL + ["svi_overall"])
except ValueError as e:
    print("guard works ->", e)
print(len(STRUCTURAL), "structural features, e.g.", STRUCTURAL[:8])""")
code("""mc = cfg["model"]
folds = make_folds(df, "spatial", k=10, seed=mc["seed"], km=mc["spatial_block_km"])
res = {}
for layer, target in [("bldg", "r2026a_bldg450"), ("poi", "r2026a_poi")]:
    res[layer] = crossfit_cqr(df, target, STRUCTURAL, folds, alpha=mc["alpha"], params=mc["lgbm"], seed=mc["seed"])
    o = res[layer]; r2 = 1 - ((o.y_log - o.q_med)**2).sum() / ((o.y_log - o.y_log.mean())**2).sum()
    print(f"{layer}: coverage {o.covered.mean():.3f} | flag rate {o.flag.mean():.3f} | R2(log) {r2:.3f} | flagged {o.flag.sum()}")""")

md("## 4. Validation (Phase 4)")
code("""from coverage_risk.validation import flag_skill, deletion_test
o = res["bldg"]; truth = (df.r2026a_bldg450 / df.ref_bldg < 0.8).values; ok = df.ref_bldg.notna().values
print("Flags vs USA Structures gaps:", {k: round(v, 3) for k, v in flag_skill(o.flag.values[ok], o.deficit_z.values[ok], truth[ok]).items()})
print(deletion_test(o, seed=mc["seed"]).to_string(index=False))""")
code("""print("CV schemes x calibration (from scripts/04_validation.py):")
pd.read_csv("outputs/tables/cv_schemes.csv")[["layer","scheme","calibration","coverage","flag_rate","r2_log","cov_region_min","cov_region_max"]].round(3)""")
code("display(Image('outputs/figures/fig3_coverage_schemes.png', width=800))")

md("""## 5. Pre-registered equity audit (Phases 5-6)
Hypotheses were frozen in `docs/preregistration.md` before this step. Strata are joined here for the first time.""")
code("""from coverage_risk.audit import define_groups, flag_contrast, exposure_ratio, bh
d = df.merge(define_groups(strata), on="GEOID").merge(strata.drop(columns="region"), on="GEOID")
for layer in ["bldg", "poi"]:
    for c in ["flag", "shortfall_lower", "deficit_z"]:
        d[f"{layer}_{c}"] = res[layer][c].values
rows = []
for layer in ["bldg", "poi"]:
    for g in ["svi", "cvi", "rural", "tribal"]:
        r = flag_contrast(d, f"{layer}_flag", g, n_boot=1000, seed=mc["seed"]); rows.append({"layer": layer, **r})
for hz, col in {"heat": "epht_heat_days_summer", "wildfire": "usfs_BP_mean", "drought": "usdm_summer_dsci"}.items():
    for g in ["svi", "rural", "tribal"]:
        rows.append({"layer": "bldg", "hazard": hz, **exposure_ratio(d, col, g, n_boot=1000, seed=mc["seed"])})
a = pd.DataFrame(rows)
a["reject_bh"], a["p_bh"] = bh(a.p)
a[["layer","hazard","group","contrast","rate_hi","rate_lo","risk_diff","adj_odds_ratio","rate_ratio","ci_lo","ci_hi","p","p_bh","reject_bh"]].round(4)""")
code("""print("Full confirmatory family incl. H3 (scripts/06b_fdr.py):")
pd.read_csv("outputs/tables/confirmatory_fdr.csv")[["hyp","layer","hazard_name","group","risk_diff","adj_odds_ratio","rate_ratio","adj_diff","p","p_bh","reject_bh"]].round(4)""")
code("display(Image('outputs/figures/fig7_hidden_exposure.png', width=650))")

md("## 6. Catch-up across releases (Phase 7, H3) and the release regression")
code("""snap = pd.read_csv("outputs/tables/h3_snapshots.csv")
snap[["snapshot","buildings","buildings450","share_tracts_lt80","lt80_rural_rural","lt80_rural_urban","lt80_tribal_tribal","lt80_svi_Q4"]].round(4)""")
code("""c = pd.read_parquet("data/processed/catchup_frame.parquet")
loss = (c.r2026a_bldg450 - c.r2026b_bldg450) / c.r2026a_bldg450.clip(lower=1)
reg = loss > 0.20
print(f"tracts losing >20% of buildings Aug->Oct 2026: {reg.sum()} (Bexar County: {(reg & (c.county=='48029')).sum()})")
print(f"buildings lost: {(c.r2026a_bldg450 - c.r2026b_bldg450)[reg].sum():,.0f}; residents: {c.loc[reg,'pop'].sum():,.0f}")
print(f"flag rate in those tracts: Aug {c.loc[reg,'flag_r2026a'].mean():.1%} -> Oct {c.loc[reg,'flag_r2026b'].mean():.1%} (no reference used)")""")
code("display(Image('outputs/figures/fig6_catchup.png', width=900)); display(Image('outputs/figures/fig8_bexar_regression.png', width=450))")

md("## 7. Why tract flags miss group-wide gaps (exploratory)")
code("""e = json.load(open("outputs/tables/exploratory.json"))
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items() if k.startswith("E2_absorbed") or k.startswith("E2_resid") or k == "E2_gap_threshold_log"})
display(Image('outputs/figures/fig5_two_lenses.png', width=650))""")

md("""## 8. Conclusions
* Conformal ranges are calibrated (90% coverage) under spatial cross-fitting, but not when transferred to a new region without local calibration.
* Overture buildings are close to complete here; rural and tribal gaps closed faster from 2023 to 2026.
* A silent 2026 release regression removed about 179,000 buildings from San Antonio tracts, mostly high-vulnerability ones, and the reference-free model detected it.
* Hidden wildfire exposure is concentrated in rural tracts.
* Tract-level flags cannot see modest, group-wide gaps; equity audits need reference comparisons aggregated by group.

Full details: `paper/main.pdf`, `deliverables/IEEE_Report.pdf`, `deliverables/Invisible_Exposure_Project_Documentation.docx`.""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "notebooks/Invisible_Exposure.ipynb")
print("written")
