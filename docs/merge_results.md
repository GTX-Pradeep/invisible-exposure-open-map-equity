# Merged project: results of N1-N5 (exploratory)

Run 2026-11-10 with `scripts/11a_import_merged.py` and `scripts/11_merged_exploratory.py` under the pre-specified N1-N5
exploratory rules (summarized below). Nothing has been committed. Join rate 100% (9,794 tracts). Tables in `outputs/tables/merged/n*_*.csv`,
key numbers in `outputs/tables/merged/merged.json`, the N-family BH correction (64 tests) in `outputs/tables/merged/n_family_fdr.csv`.

**Checks that the comparisons are fair:** the re-implemented hazard exposure reproduces IE's `exposure_ratio` exactly;
the conformal, OLS and ratio rows of N3 reproduce `flag_skill.csv` exactly; project's models E and G reproduce
the saved notebook MAE (390.89, 366.56).

## Decisions (rules written before running)

| Exp. | Rule outcome | What the paper says |
|---|---|---|
| N1 | **Two separate failures** (rule as written: county-bootstrap CI includes 0) | see caveat: evidence points to one mechanism, but the pre-specified test cannot show it |
| N2 | Rural wildfire **robust** (4/4 variants; all survive BH). Rural drought **robust by the rule** (2/3, 3/4) but no variant survives BH and within-region terciles give 1.65 (0.74-3.27). Tribal heat (0.08) **indicator-dependent** | 4.8× wildfire stated as robust; drought stated as sensitive to how hazard is cut; tribal heat not interpreted |
| N3 | Conformal model **neither beats nor is beaten** by any baseline on precision, recall or PR-AUC at the 510-tract budget | value of the conformal model = calibrated ranges + shock detection (Bexar), not ranking |
| N4 | Rule not met as written: class-share coefficient CI excludes 0 **but with the opposite sign** (more labels, slightly more gaps; OR 3.3 per unit, 1.18-9.22; not significant after BH, p_BH 0.12). Label poverty is not a gap detector (AUC 0.56, 0.48-0.65) | footprints and attributes are separate failures; a geometric check cannot see the semantic one |
| N5 | No recall loss for G vs E (difference 0.000, CI -0.027 to 0.036) | one sentence; the "spatial lag absorbs gaps" mechanism is not shown |

## N1. San Antonio drop vs Microsoft dominance and labels

186 tracts lost > 20% of buildings ≥ 450 sq ft between 2026-08 and 2026-10 (181 in Bexar County; 179,047 buildings).

| Measure (2026-08) | Regressed | Other S-C Texas | Other Bexar |
|---|---|---|---|
| Microsoft share of buildings (mean) | 0.79 | 0.38 | 0.24 |
| Microsoft-dominant (≥ 90%) | 44% | 19% | 7% |
| Buildings with a class label | 4.1% | 25.4% | 23.4% |

* Pooled, 79.5% of the regressed tracts' buildings were Microsoft-sourced. In **every** regressed tract the loss is no
  larger than its Microsoft count, and loss rises with Microsoft share (Spearman 0.68).
* **Caveat on the rule:** 181 of 186 regressed tracts are in one county, so the pre-specified county-cluster bootstrap
  cannot separate them from the comparison (CI −0.23 to 0.31 for the 25-point difference in Microsoft dominance). A
  tract bootstrap gives 0.18 to 0.32. The "other Bexar" comparison CIs are degenerate (one cluster) and are not evidence,
  even though they pass BH.
* Suggested wording: *"The tracts that lost buildings were the ones built from Microsoft footprints (79.5% of their
  buildings; every loss ≤ the Microsoft count) and they carried almost no class labels (4%). Because almost all are in
  one county, we cannot test this as a general mechanism."*

## N2. Hidden hazard exposure under other indicators

| Hazard × group | H5 primary | Alt 1 | Alt 2 | Within-region terciles | Mantel-Haenszel | Verdict |
|---|---|---|---|---|---|---|
| wildfire × rural | 4.79 (2.38-9.41) | WHP 3.80 (1.80-8.31) | MTBS 6.25 (1.79-27.1) | 4.47 (2.23-8.73) | 4.93 (1.97-9.31) | robust |
| drought × rural | 2.92 (1.23-7.13) | PMDI 2.51 (1.00-6.27) | SPI 3.09 (1.27-8.28) | 1.65 (0.74-3.27) | 3.30 (1.07-7.12) | robust (rule), weak |
| heat × tribal | 0.08 (0.00-0.36) | WBGT 0.00 | HWD 1.65 (0.51-5.46) | 0.72 (0.19-2.42) | 6.37 (0.00-23.2) | indicator-dependent |

All other hazard × group cells: primary not significant, and no variant changes that. MTBS burned share is
zero-inflated, so its "top tercile" is the 9.6% of tracts with any burn. The tribal heat Mantel-Haenszel value passes BH
only because of the zero-replicate issue already noted in Deviation 4; it is not evidence.

## N3. Flag skill against USA Structures (budget = 510 flags, prevalence 1.86%)

| Method | Precision | Recall | Lift | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|
| Conformal model (IE) | 0.094 | 0.264 | 5.06 | 0.685 | 0.099 |
| Isolation Forest (experiments) | 0.098 | 0.275 | 5.28 | 0.766 | 0.095 |
| NB shortfall (experiments) | 0.094 | 0.264 | 5.06 | 0.736 | 0.069 |
| Map/housing ratio (IE) | 0.090 | 0.253 | 4.85 | 0.463 | 0.081 |
| XGB shortfall (experiments) | 0.086 | 0.242 | 4.64 | 0.730 | 0.071 |
| OLS log-HU (IE) | 0.075 | 0.209 | 4.01 | 0.729 | 0.063 |
| XGB model E (project) | 0.075 | 0.209 | 4.01 | 0.686 | 0.064 |
| XGB model G (project) | 0.075 | 0.209 | 4.01 | 0.670 | 0.066 |
| Random flags | 0.019 | 0.053 | 1.01 | 0.50 | 0.019 |

Paired county-bootstrap differences vs the conformal model: no difference for any method on precision, recall or PR-AUC.
On ROC-AUC the ratio baseline is worse (−0.22, −0.33 to −0.14) and XGB shortfall is better (+0.04, 0.005 to 0.085);
neither survives as a ranking claim after BH. Per region (`n3_by_region.csv`): every method finds nothing in Eastern WA
(no gaps) and the conformal model finds none of Northern CA's 8 gaps.

## N4. Do missing labels predict real gaps?

* Logit (region FE, county-cluster SE): class share OR 3.3 per unit (1.18-9.22), Microsoft share OR 1.8 (0.90-3.67),
  housing density OR 0.70 (0.61-0.79). Eastern WA has no gaps, so its region effect is not identified (non-convergence);
  refitting without it gives the same class-share coefficient.
* Microsoft-dominant tracts have 1.1% labelled buildings and a reference-gap rate of 2.9%; other tracts 29.5% and 1.6%.

## N5. Does a spatial lag of the outcome hide gaps?

Model G vs E: precision and recall identical at 510 flags; ROC-AUC −0.016 (−0.043 to 0.024). Absorption shares from the
project models are unstable because the observed rural and SVI reference gaps are themselves near zero in this sample
(`n5_absorption.csv`); they are not interpreted. Model E uses rurality and region as inputs (by construction it absorbs
rural differences), which is one more reason the project models are comparison methods only.

## Changes made in this repository (uncommitted)

* `config/config.yaml`: `merge:` block. `data/external/merged_inputs.csv`: imported per-tract fields.
* `scripts/11a_import_merged.py`, `scripts/11_merged_exploratory.py` (new); `scripts/run_all.sh`: two lines after `09`.
* `scripts/11b_import_companion.py` (added 2026-11-11): copies the companion pipeline's summary tables (relative RMSE by layer,
  highway-length transfer totals by region, provenance-beyond-counts) into `data/external/companion/`, with SHA-256 hashes of the
  sources in `SOURCES.json`. Before this, `12_merged_numbers.py` read them from `../MapEquityChallenge`, so the paper's
  `MgRrmse*`, `MgHwyLoro*` and `MgProvMae*` numbers could not be checked from a clone of this repository. All 86 generated
  numbers were unchanged after the switch; `tests/test_self_contained.py` keeps steps 11 and 12 free of sibling-project paths.
* `src/coverage_risk/model.py`: `assert_no_leakage` also refuses the imported prefixes (`mec_`, `alt_`, `if_`, `exp_`, `prj_`).
* `tests/test_core.py`: two tests (11 pass). `docs/preregistration.md`: Deviation 5.
* Not yet changed: `paper/`, `deliverables/`, `scripts/10_paper_numbers.py` (plan step 5).

## Independent review and additions (2026-11-11)

Every imported number was checked against the companion sources before the merged work was kept.

| Check | Result |
|---|---|
| SHA-256 of all six imported source files | match `outputs/tables/merged/merged_sources.json` |
| Building / Microsoft counts vs this pipeline's own extraction | agree in 98.5% / 99.3% of tracts |
| Use-class share in Microsoft-dominant tracts, from `base_table.parquet` | 1.05% vs 24.9% elsewhere (as reported) |
| N3 comparison inputs rebuilt from the raw OOF cache | identical (max difference 0.0); lifts NB 5.06, XGB 4.64 |
| N1-N5 rerun from committed inputs | identical to floating-point noise (1e-12) |

Changes made in review:
- **Self-contained.** `scripts/11b_import_companion.py` writes `data/external/companion/` (layer predictability, highway transfer,
  provenance-beyond-counts, MapEquity risk scores; SHA-256 in `sources.json`). `scripts/12_merged_numbers.py` and
  `scripts/14_reference_validation.py` read only these copies; `tests/test_self_contained.py` enforces it. Road/fire/EMS relative RMSE
  now comes from the verified research cache (spatial folds): buildings 0.49, highways 0.52, fire 0.92, EMS 0.99.
- **Wording.** "consistent with H4" now refers to the descriptive source comparison (H4's test was null); "reproduces exactly" is
  "to floating-point precision"; the boundary-assignment limitation (3 buildings, 62 places) was dropped.
- **Restored** the deliverable build scripts (`deliverables/build_*.js`, `notebooks/make_notebook.py`).
- **New exploratory R1-R2** (`scripts/14_reference_validation.py`): both teams' scores against USA Structures for all tracts. This answers
  the companion experiment plan's E1/E4/E9 without hand labelling and corrects the companion manuscript's claim that rural disparities are
  model artefacts: real gaps are 3.72x (rural, RUCA >= 4 as pre-registered; 2.64x with the Census urban/rural class) and 2.71x (tribal) more common, and both scores under-state this.

## Relative RMSE re-estimated in this repository (2026-11-11, evening)

`scripts/16_relative_rmse.py` refits Poisson and Tweedie GLMs, LightGBM and XGBoost on the five structural inputs, with the
conformal model's spatial folds and leave-one-region-out, using only `data/external/merged_inputs.csv`. The paper quotes these:
buildings 0.48, highways 0.53, fire 0.92, EMS 1.00; highway transfer 1.49x (Maricopa) and 0.70x (Texas). The research cache in
`data/external/companion/layer_predictability.csv` gives 0.49 / 0.52 / 0.92 / 0.99 and 1.42x / 0.70x; the conclusions are the same.
`MgProvMae*` still comes from `data/external/companion/provenance_beyond_counts.csv`. `scripts/17_review_checks.py` collects the
review numbers in `outputs/tables/review/review_checks.csv`.
