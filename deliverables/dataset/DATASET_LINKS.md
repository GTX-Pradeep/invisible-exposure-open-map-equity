# Dataset: Invisible Exposure

Two parts: (A) our processed tract-level tables, in this folder; (B) the public raw sources, with links. Everything in (A) is regenerated from (B) by `scripts/run_all.sh`.

## A. Processed data (this folder)

| File | Rows | Description |
|---|---|---|
| `invisible_exposure_tract_results.csv` | 9,794 | One row per census tract: counts per release, reference counts, expected range, flags, shortfall, audit strata. Main results file. |
| `tracts_model_table.csv` | 9,794 | The full model table: structural covariates, Overture counts and provenance, references. Contains no audit strata. |

### Data dictionary (`invisible_exposure_tract_results.csv`)

| Column | Meaning |
|---|---|
| `GEOID` | 2020 census tract ID (11 characters; keep as text) |
| `region` | Study region (maricopa-az, northern-ca, eastern-ok, south-central-tx, eastern-wa) |
| `county` | 5-digit county FIPS |
| `hu`, `pop`, `land_km2`, `jobs` | Housing units, population (ACS 2020-2024), land area, workplace jobs (LODES 2022) |
| `r2023_bldg`, `r2026a_bldg`, `r2026b_bldg` | Overture buildings per tract: 2023-07-26-alpha.0, 2026-08-19.0, 2026-10-21.0 |
| `*_bldg450` | Same, footprints of at least 450 sq ft (comparable to USA Structures) |
| `r2026a_poi` | Overture places per tract (2026-08-19.0) |
| `r2026a_src_*` | Buildings by primary upstream source (OpenStreetMap, Microsoft, Google, Esri) |
| `ref_bldg` | FEMA/ORNL USA Structures count (validation reference) |
| `ref_est_zbp` | ZIP Business Patterns 2023 establishments allocated to the tract (POI reference) |
| `bldg_expected`, `bldg_lower`, `bldg_upper` | Model's expected building count and 90% conformal range (2026-08) |
| `bldg_flag` | True if observed buildings fall below the lower bound |
| `bldg_shortfall_lower` | Conservative missing buildings (lower bound minus observed, if positive) |
| `bldg_deficit_z` | Standardized deficit; above 1 means below the lower bound |
| `poi_*` | Same for POIs |
| `flag_r2023`, `flag_r2026b` | Building flag when the model is rerun on the 2023 and 2026-10 releases |
| `svi_overall`, `cvi_overall` | CDC SVI 2022 percentile; Climate Vulnerability Index (audit only) |
| `ruca_primary`, `ur_class`, `tribal_any` | Rurality code, Census urban/rural class, any tribal-area overlap (audit only) |
| `epht_heat_days_summer`, `usfs_BP_mean`, `usdm_summer_dsci` | Heat days, wildfire burn probability, drought severity (audit only) |
| `svi`, `rural`, `tribal`, `cvi` | Pre-registered audit groups (Q4/Q1, rural/urban, tribal/non-tribal, top/bottom) |

## B. Public raw sources

| Dataset | Version | Link |
|---|---|---|
| Bias Bounty challenge extracts (Overture 2026-08-19.0 buildings/places, ACS housing, strata, boundaries) | 2026 | https://source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge |
| Overture Maps (current releases) | 2026-10-21.0 | `s3://overturemaps-us-west-2/release/2026-10-21.0/` (https://docs.overturemaps.org) |
| Overture Maps 2023 (archived GeoParquet copy) | 2023-07-26-alpha.0 | https://source.coop/cholmes/overture |
| FEMA/ORNL USA Structures | v1 | https://source.coop/wherobots/usa-structures |
| ACS 5-year Table-Based Summary File | 2020-2024 | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/ |
| LEHD LODES 8 workplace area characteristics | 2022 | https://lehd.ces.census.gov/data/lodes/LODES8/ |
| ZIP and County Business Patterns | 2023 | https://www2.census.gov/programs-surveys/cbp/datasets/2023/ |
| ZCTA-to-tract relationship file | 2020 | https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/ |

Licences: Overture buildings ODbL, places CDLA-Permissive-2.0; Census, LODES, USA Structures public domain; challenge package CC BY-SA 4.0. Derived tables inherit these licences.
