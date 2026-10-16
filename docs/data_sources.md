# Data sources

Record the exact version and access date for every dataset used.

| Dataset | Use | Access | License | Version used |
|---|---|---|---|---|
| Overture Maps (buildings, places, transportation) | Main map data | Public S3 `s3://overturemaps-us-west-2/release/` or participant extracts on Source Cooperative | Varies by theme (CDLA-Permissive / ODbL) | 2025-09-24.0 |
| Participant strata (SVI, CVI, rurality, tribal, heat, wildfire, drought) | Audit only | Source Cooperative (challenge data) | See source | |
| ACS 5-year (B25001, B01003, B25024, B25002) | Structural covariates | api.census.gov | Public domain | 2023 |
| TIGER/Line cartographic boundary tracts | Tract polygons | via `pygris` | Public domain | 2023 |
| FEMA/ORNL USA Structures | Building reference | source.coop/wherobots/usa-structures (GeoParquet); gis-fema.hub.arcgis.com/pages/usa-structures | U.S. Government Work | |
| Census County Business Patterns / ZIP Business Patterns | POI reference | census.gov/data/developers/data-sets/cbp-zbp.html | Public domain | |
| HUD USPS ZIP–Tract crosswalk | Map ZIP to tract | huduser.gov | Public domain | |
| DOT National Address Database | Optional robustness | catalog.data.gov (NAD text file) | Public domain | |

## Independence check

A reference dataset must not already be a source inside Overture for the same layer and area. Before validating, inspect Overture's `sources[].dataset` values for the study states. Microsoft and Google building footprints are **not** valid references because Overture already includes them.

## Known limitations

- USA Structures only covers structures > 450 sq ft and is satellite-derived, so it may share blind spots (e.g., buildings under tree canopy) with ML footprints in Overture.
- CBP counts only establishments with paid employees and is reported at ZIP/county level.
- NAD coverage depends on which jurisdictions contribute.
