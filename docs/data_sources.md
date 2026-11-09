# Data sources, versions, licences, and independence

| Dataset | Version / vintage | Role | Access | Licence |
|---|---|---|---|---|
| Overture Maps buildings + places | `2026-08-19.0` (primary; challenge extracts) | Map under audit | `data.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/reference/` | ODbL (buildings), CDLA-Permissive-2.0 (places) |
| Overture Maps buildings + places | `2026-10-21.0` | Later snapshot (H3) | `s3://overturemaps-us-west-2/release/2026-10-21.0/` | as above |
| Overture Maps buildings | `2023-07-26-alpha.0` (archived GeoParquet copy; files dated Aug–Oct 2023) | Earlier snapshot (H3) | `data.source.coop/cholmes/overture/geoparquet-country-quad-hive/country_iso=US/` | ODbL |
| Census tract polygons + spine | 2020 tracts, TIGER 2025 | Unit of analysis, land area | challenge `strata/` | Public domain |
| ACS 5-year Table-Based Summary File | 2020–2024 (B25001, B25002, B25024, B01003, B25034, B11001, B26001) | Structural covariates | `www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/` | Public domain |
| LEHD LODES 8 WAC | 2022, all jobs (S000/JT00), NAICS sector counts only | Structural covariates (POIs) | `lehd.ces.census.gov/data/lodes/LODES8/` | Public domain |
| FEMA/ORNL USA Structures | v1 (geoparquet mirror) | Building reference, validation only | `data.source.coop/wherobots/usa-structures/` | Public domain |
| Census ZIP Business Patterns | 2023 totals | Establishment reference (allocated to tracts by ZCTA land share), validation only | `www2.census.gov/programs-surveys/cbp/datasets/2023/` | Public domain |
| Census County Business Patterns | 2023 | County establishment reference, validation only | as above | Public domain |
| ZCTA–tract relationship file | 2020 | Allocation weights | `www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/` | Public domain |
| Audit strata (SVI 2022, CVI, RUCA 2020, tribal overlap, EPHT heat, USFS Wildfire Risk 2024, USDM) | see challenge README | Audit only | challenge `strata/national/` | per source; challenge package CC BY-SA 4.0 |

## Independence check

* **Model inputs** are Census/ACS/LODES counts only. None is derived from Overture, USA Structures,
  or Business Patterns. `model.assert_no_leakage()` refuses audit-stratum, reference, outcome and
  provenance columns.
* **USA Structures and Overture.** USA Structures is ORNL's own imagery extraction. Overture buildings
  merge OpenStreetMap, Microsoft ML footprints, Google Open Buildings and Esri Community Maps. Both
  are imagery-derived, so their errors may be correlated (e.g., under tree canopy). This would
  *understate* true gaps, not create spurious ones. It is discussed as a limitation.
* **Business Patterns** counts establishments with paid employees at their tax address; Overture places
  includes non-employer and non-business POIs. The two measure related but different universes, so we
  use within-region relative ratios, not absolute ones.
* **Audit strata** enter only in `scripts/06_audit.py` and later.
