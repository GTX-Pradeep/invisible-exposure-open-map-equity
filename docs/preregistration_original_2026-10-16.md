# Pre-registration

Fill this in and commit it **before** looking at any audit results. The git commit timestamp serves as the registration date. For a stronger record, also deposit it on OSF (osf.io).

## 1. Research questions

1. Can we estimate where open maps are incomplete, with honest uncertainty, without a perfect reference map?
2. How much wildfire, heat and drought exposure is missing from the map, and does it fall disproportionately on socially vulnerable, rural and tribal communities?
3. As Overture improves across releases, do vulnerable communities catch up?
4. Does dependence on a single data source predict where gaps are?

## 2. Hypotheses

- **H1.** Hidden exposure (missing exposed structures per 1,000 housing units) is higher in high-SVI × high-heat tracts than in low-SVI × low-heat tracts.
- **H2.** Rural and tribal tracts in high-drought areas have higher single-source dependence than non-rural, non-tribal tracts.
- **H3.** Between Overture releases, the shortfall shrinks more slowly in high-SVI tracts than in low-SVI tracts.
- **H4.** Adding provenance features improves detection of reference-validated gaps beyond count-only features, under spatial-block validation.
- **H5 (wildfire).** Hidden exposure is higher in high-wildfire-hazard tracts. Primary outcome uses buildings only (no POI-based score) to avoid circularity.

## 3. Data

- Overture Maps release: `2025-09-24.0` (plus earlier releases for H3)
- States: AZ, CA, OK, TX, GA
- Unit of analysis: 2020 census tracts
- Structural covariates: see `config/config.yaml` (ACS 5-year)
- Audit variables: SVI, CVI, rurality class, tribal overlap, heat, wildfire, drought (participant strata)
- External reference: FEMA/ORNL USA Structures (buildings); Census County Business Patterns (POIs)

## 4. Expectation model

- Inputs: structural variables only (`STRUCTURAL_COLUMNS` in `src/coverage_risk/features.py`)
- Excluded by design: all audit variables
- Model: LightGBM on log1p(count); split-conformal 90% intervals
- Flag rule: observed count below the conformal lower bound

## 5. Group definitions (fix thresholds now)

| Variable | High | Low |
|---|---|---|
| SVI | top quartile | bottom quartile |
| Heat | top quartile | bottom quartile |
| Drought | top quartile | bottom quartile |
| Wildfire | top quartile | bottom quartile |
| Rural | (define using participant rurality class) | |
| Tribal | tract overlaps tribal land by ≥ __% | no overlap |

## 6. Analysis plan

- Tests: Mann–Whitney U for group contrasts; report medians and effect sizes
- Multiple comparisons: Benjamini–Hochberg FDR at q = 0.05 across all pre-registered contrasts
- Validation: random vs. spatial-block (50 km) vs. leave-one-state-out CV
- Robustness: (a) without units-in-structure covariates, (b) alternative models (negative binomial GLM), (c) alternative conformal level (80%, 95%)

## 7. What would count as a negative result

Report all hypotheses regardless of outcome. A null result for H1–H5 is still reported as a finding.

## 8. Deviations

Record any change made after registration here, with date and reason.
