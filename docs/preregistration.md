# Pre-registration: Invisible Exposure (frozen before Phase 5)

**Frozen:** 2026-11-09, before the provenance (Phase 5), equity-audit (Phase 6), or catch-up (Phase 7)
analyses were run. The Git commit that adds this file is the registration record. Any change after
that commit is listed under *Deviations* with a date and a reason.

## Disclosure of what was seen before freezing

* Phase 1 feasibility: the share of tracts where Overture buildings ≥ 450 sq ft fall below 80% of
  the USA Structures count, overall and tabulated by `ur_class`, SVI quartile, and `tribal_any`
  (1.9% overall; 3.7% rural vs 1.3% urban; 4.3% tribal vs 1.6% non-tribal; no monotone SVI pattern).
  These are reference-based descriptives, not model outputs, and are reported as such.
* Phases 3–4: model fit, conformal coverage, flag skill against the references, and the deletion test.
  No model output (flag, shortfall, deficit) was cross-tabulated with any audit stratum.

## Study units and data

* 9,794 2020 census tracts in the five *Bias Bounty: Mapping Equity* study regions (maricopa-az,
  northern-ca, eastern-ok, south-central-tx, eastern-wa). This replaces the five whole states in the
  original plan, because the audit strata are distributed for these regions.
* Map under audit: Overture Maps `2026-08-19.0` (primary). Snapshots for H3: `2023-07-26-alpha.0`
  (archived GeoParquet copy) and `2026-10-21.0`.
* Independent references (validation only): FEMA/ORNL USA Structures (buildings); Census ZIP / County
  Business Patterns 2023 (establishments).

## Outcomes (per layer L ∈ {buildings ≥ 450 sq ft, POIs})

* `flag_L`: observed count below the 90% conformal lower bound (spatial-block cross-fitting,
  global CQR calibration). **Primary outcome.**
* `deficit_z_L`: (median − observed) / (median − lower), on the log scale. Secondary.
* `shortfall_lower_L`: max(lower bound − observed, 0), in features. Conservative missing count.
* **Hidden exposure** for hazard h: Σ `shortfall_lower_bldg` over tracts in the top tercile of hazard h,
  per 1,000 housing units of the group. Hazards: heat (`epht_heat_days_summer`), wildfire
  (`usfs_BP_mean`, burn probability), drought (`usdm_summer_dsci`). Terciles are cut on all 9,794
  study tracts.

## Audit groups (never model inputs)

* **SVI:** `svi_overall` national percentile, Q4 (≥ 0.75) vs Q1 (< 0.25).
* **Rural:** RUCA primary code ≥ 4 vs 1–3.
* **Tribal:** `tribal_any` = True vs False.
* **CVI:** `cvi_overall` top vs bottom quartile within the study tracts.

## Hypotheses and tests

| ID | Hypothesis | Test |
|---|---|---|
| H1 | Flag rates are higher in high-SVI (Q4) than low-SVI (Q1) tracts, for buildings and POIs; also high vs low CVI. | Logistic regression `flag ~ group + region FE`. Log-odds with county-cluster-robust SE; risk difference with county-cluster bootstrap 95% CI (2,000 reps). |
| H2 | Flag rates are higher in rural than urban tracts, and in tribal than non-tribal tracts. | Same as H1. |
| H3 | From 2023 to 2026, mapping catches up in disadvantaged tracts: building completeness relative to USA Structures improves more in SVI-Q4, rural, and tribal tracts. | Outcome Δ = log(r2026b/ref) − log(r2023/ref) per tract; OLS `Δ ~ group + region FE`, county-cluster SE. Also the change in flag rate (2023 vs 2026-10 model reruns), by group. |
| H4 | Provenance features (source-mix entropy, single-source flag, ML-footprint share, POI source shares) improve detection of reference-defined gaps. | Gradient-boosted classifier for the reference gap: structural + model deficit vs. + provenance. Spatial-block CV PR-AUC and ROC-AUC; difference with block-bootstrap 95% CI. |
| H5 | Hidden heat, wildfire and drought exposure per 1,000 housing units is higher in SVI-Q4, rural and tribal tracts. | Ratio of group rates; county-cluster bootstrap 95% CI and two-sided p. |

**Multiplicity:** Benjamini–Hochberg across all H1, H2, H3 and H5 contrasts (both layers where
applicable), q = 0.05. H4 is reported with its CI and is not in the FDR family.

**Direction:** all tests are two-sided. A null or reversed result is reported as such.

## Robustness (reported, not FDR-controlled)

1. Expectation model without housing-type covariates (units in structure).
2. Negative-binomial GLM expectation model in place of LightGBM.
3. 80% and 95% conformal ranges.
4. Mondrian (within-region) calibration.
5. For buildings: the USA Structures gap (ratio < 0.8) as the outcome, in place of the model flag.
6. Excluding tracts with fewer than 50 housing units.

## Deviations

Recorded after the freeze, with date and reason. None changes a pre-registered estimand, threshold or test.

1. **2026-11-09: bootstrap implementation.** The county-cluster bootstrap was re-implemented with
   multinomial cluster weights on per-county sums, which is algebraically the same resampling scheme
   but much faster. Reported CIs come from this implementation. Point estimates are unchanged.
2. **2026-11-09: original template tested as worded.** The original template (commit `807831b`,
   2026-10-16; preserved in `docs/preregistration_original_2026-10-16.md`) is tested exactly as
   worded (Mann–Whitney U, BH within that family) in `scripts/06d_original_hypotheses.py`, with its
   blanks filled as in this document (rural = participant `ur_class`; tribal = any overlap).
3. **2026-11-09: exploratory analyses (not pre-registered).** These are labelled *exploratory*
   wherever reported:
   * E1: a release regression found while running H3 (Overture `2026-09-23.0` and later dropped
     Microsoft footprints in Bexar County, TX), and whether the reference-free model detects it.
   * E2: normalization/absorption, comparing the map-trained expectation with a reference-anchored
     expectation.
   * E3: H3 re-estimated with the `2026-08-19.0` endpoint, and excluding Bexar County, because of E1.
4. **2026-11-09: H5 inference.** For one contrast (heat, tribal vs. non-tribal) some bootstrap
   replicates have zero hidden exposure in the tribal group. Its bootstrap p-value is computed on
   the replicates with a positive ratio. The 95% CI excludes 1 either way.
